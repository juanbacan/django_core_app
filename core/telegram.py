import os
import json
import logging
import requests
import threading
from typing import Optional, Dict, Any, Union
from django.apps import apps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuración de API
TELEGRAM_TIMEOUT = getattr(settings, 'TELEGRAM_TIMEOUT', 30)
TELEGRAM_RATE_LIMIT = getattr(settings, 'TELEGRAM_RATE_LIMIT', 30)  # Requests por segundo


class TelegramAPIError(Exception):
    """Excepción personalizada para errores de la API de Telegram."""
    pass


class TelegramClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern para thread-safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_credentials()
        return cls._instance

    # -------------------------
    # Credenciales / setup
    # -------------------------
    def _initialize_credentials(self):
        try:
            CredencialesAPI = apps.get_model('core', 'CredencialesAPI')
            # Sugerencia de nuevos campos en tu modelo:
            # telegram_bot_token = models.CharField(max_length=255, blank=True, default="")
            # telegram_default_chat_id = models.CharField(max_length=64, blank=True, default="")
            cred, _ = CredencialesAPI.objects.get_or_create(
                defaults={
                    'telegram_bot_token': '',
                    'telegram_default_chat_id': ''
                }
            )
            self._credenciales_id = cred.id
            self.token = getattr(cred, 'telegram_bot_token', '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
            self.default_chat_id = getattr(cred, 'telegram_default_chat_id', '') or os.getenv('TELEGRAM_DEFAULT_CHAT_ID', '')

            if not self.token:
                logger.warning("Telegram: token vacío; configura 'telegram_bot_token' en CredencialesAPI.")

            self.base_url = f"https://api.telegram.org/bot{self.token}/"
            self.timeout = TELEGRAM_TIMEOUT
        except Exception as e:
            logger.error(f"Error inicializando credenciales de Telegram: {e}")
            self._credenciales_id = None
            self.token = ''
            self.default_chat_id = ''
            self.base_url = ''

    def _validate_credentials(self):
        if not self.token:
            raise ValueError("Credenciales de Telegram no configuradas. Actualiza 'telegram_bot_token' en CredencialesAPI.")
        if not self.base_url:
            raise ValueError("URL base de Telegram no inicializada.")
    
    def _check_rate_limit(self):
        """Verificar límite de requests para evitar bloqueos de Telegram"""
        key = f'telegram_rate_limit_{self.token[:10]}'
        count = cache.get(key, 0)
        if count >= TELEGRAM_RATE_LIMIT:
            raise TelegramAPIError(f"Rate limit excedido: {count}/{TELEGRAM_RATE_LIMIT} requests por segundo")
        cache.set(key, count + 1, 1)  # Expira en 1 segundo

    def refresh_credentials(self):
        """Refrescar credenciales desde la base de datos."""
        self._initialize_credentials()

    # -------------------------
    # Núcleo HTTP
    # -------------------------
    def _request(self, method: str, payload: Dict[str, Any], files: Optional[Dict[str, Any]] = None):
        """
        Llamada genérica a Telegram API.
        - method: nombre del método (p. ej. 'sendMessage')
        - payload: parámetros del método
        - files: para multipart (p. ej. {'photo': open('path', 'rb')})
        """
        try:
            self._validate_credentials()
            self._check_rate_limit()
            url = self.base_url + method

            # Telegram acepta application/x-www-form-urlencoded o multipart/form-data para la mayoría.
            # Si hay reply_markup como dict, serializarlo a JSON.
            if 'reply_markup' in payload and isinstance(payload['reply_markup'], (dict, list)):
                payload = dict(payload)  # copiar para no mutar
                payload['reply_markup'] = json.dumps(payload['reply_markup'])

            if files:
                r = requests.post(url, data=payload, files=files, timeout=self.timeout)
            else:
                r = requests.post(url, data=payload, timeout=self.timeout)

            resp = r.json()
            if not resp.get('ok'):
                desc = (resp.get('description') or 'Error desconocido')
                err_code = resp.get('error_code')
                logger.error(f"Telegram API Error {err_code}: {desc}")
                raise TelegramAPIError(f"Telegram API Error {err_code}: {desc}")

            return True, resp['result']

        except requests.exceptions.Timeout:
            msg = "Timeout al conectar con Telegram API"
            logger.error(msg)
            return False, {"error": msg}
        except requests.exceptions.ConnectionError:
            msg = "Error de conexión con Telegram API"
            logger.error(msg)
            return False, {"error": msg}
        except TelegramAPIError as e:
            return False, {"error": str(e)}
        except Exception as e:
            msg = f"Error inesperado en TelegramClient: {e}"
            logger.error(msg)
            return False, {"error": msg}

    # -------------------------
    # Helpers
    # -------------------------
    def _resolve_chat(self, chat_id: Optional[Union[str, int]]) -> Union[str, int]:
        cid = chat_id or self.default_chat_id
        if not cid:
            raise ValueError("Falta chat_id. Configura 'telegram_default_chat_id' o pásalo al método.")
        return cid
    
    def _safe_open_file(self, file_path: str, mode: str = 'rb'):
        """Abrir archivo de manera segura con validaciones"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        if not os.path.isfile(file_path):
            raise ValueError(f"La ruta no es un archivo: {file_path}")
        return open(file_path, mode)

    # -------------------------
    # Métodos públicos
    # -------------------------
    def send_message(
        self,
        text: str,
        chat_id: Optional[Union[str, int]] = None,
        thread_id: Optional[int] = None,
        parse_mode: Optional[str] = "HTML",
        disable_web_page_preview: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        link_preview_options: Optional[Dict[str, Any]] = None,  # Telegram nuevo
    ):
        """
        Envía un mensaje de texto.
        Para supergrupos con foros (topics), usa 'thread_id' = message_thread_id.
        """
        if not text or not text.strip():
            return False, {"error": "El texto del mensaje no puede estar vacío"}
        if len(text) > 4096:
            return False, {"error": "El texto excede el límite de 4096 caracteres de Telegram"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "text": text
        }
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if protect_content is not None:
            payload["protect_content"] = protect_content
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if link_preview_options is not None:
            payload["link_preview_options"] = json.dumps(link_preview_options)

        return self._request("sendMessage", payload)

    def send_photo(
        self,
        photo: str,
        caption: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        thread_id: Optional[int] = None,
        parse_mode: Optional[str] = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ):
        """
        photo: URL, file_id, o ruta local (p. ej. '/tmp/img.jpg').
        """
        if not photo or not photo.strip():
            return False, {"error": "El parámetro 'photo' no puede estar vacío"}
        if caption and len(caption) > 1024:
            return False, {"error": "El caption excede el límite de 1024 caracteres"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
        }
        if caption:
            payload["caption"] = caption
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        files = None
        if photo.startswith("http://") or photo.startswith("https://") or photo.startswith("attach://") or photo.startswith("BQAC"):  # file_id heurístico
            payload["photo"] = photo
        else:
            try:
                files = {"photo": self._safe_open_file(photo)}
            except (FileNotFoundError, ValueError) as e:
                return False, {"error": str(e)}

        try:
            return self._request("sendPhoto", payload, files=files)
        finally:
            if files and files.get("photo") and not files["photo"].closed:
                files["photo"].close()

    def send_document(
        self,
        document: str,
        caption: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        thread_id: Optional[int] = None,
        parse_mode: Optional[str] = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ):
        if not document or not document.strip():
            return False, {"error": "El parámetro 'document' no puede estar vacío"}
        if caption and len(caption) > 1024:
            return False, {"error": "El caption excede el límite de 1024 caracteres"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
        }
        if caption:
            payload["caption"] = caption
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        files = None
        if document.startswith("http://") or document.startswith("https://") or document.startswith("attach://"):
            payload["document"] = document
        else:
            try:
                files = {"document": self._safe_open_file(document)}
            except (FileNotFoundError, ValueError) as e:
                return False, {"error": str(e)}

        try:
            return self._request("sendDocument", payload, files=files)
        finally:
            if files and files.get("document") and not files["document"].closed:
                files["document"].close()

    def send_video(
        self,
        video: str,
        caption: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        thread_id: Optional[int] = None,
        parse_mode: Optional[str] = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
        supports_streaming: bool = True
    ):
        if not video or not video.strip():
            return False, {"error": "El parámetro 'video' no puede estar vacío"}
        if caption and len(caption) > 1024:
            return False, {"error": "El caption excede el límite de 1024 caracteres"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "supports_streaming": supports_streaming,
        }
        if caption:
            payload["caption"] = caption
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        files = None
        if video.startswith("http://") or video.startswith("https://") or video.startswith("attach://"):
            payload["video"] = video
        else:
            try:
                files = {"video": self._safe_open_file(video)}
            except (FileNotFoundError, ValueError) as e:
                return False, {"error": str(e)}

        try:
            return self._request("sendVideo", payload, files=files)
        finally:
            if files and files.get("video") and not files["video"].closed:
                files["video"].close()

    def delete_message(self, message_id: int, chat_id: Optional[Union[str, int]] = None):
        if not message_id or message_id <= 0:
            return False, {"error": "message_id inválido"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "message_id": message_id
        }
        return self._request("deleteMessage", payload)

    def pin_message(self, message_id: int, chat_id: Optional[Union[str, int]] = None, disable_notification: bool = True):
        if not message_id or message_id <= 0:
            return False, {"error": "message_id inválido"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "message_id": message_id,
            "disable_notification": disable_notification
        }
        return self._request("pinChatMessage", payload)

    def unpin_message(self, message_id: int, chat_id: Optional[Union[str, int]] = None):
        if not message_id or message_id <= 0:
            return False, {"error": "message_id inválido"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "message_id": message_id
        }
        return self._request("unpinChatMessage", payload)

    def send_chat_action(self, action: str = "typing", chat_id: Optional[Union[str, int]] = None, thread_id: Optional[int] = None):
        """
        action: 'typing', 'upload_photo', 'record_video', 'upload_video', 'record_voice', 'upload_voice',
                'upload_document', 'choose_sticker', 'find_location', 'record_video_note', 'upload_video_note'
        """
        valid_actions = {
            'typing', 'upload_photo', 'record_video', 'upload_video', 'record_voice', 'upload_voice',
            'upload_document', 'choose_sticker', 'find_location', 'record_video_note', 'upload_video_note'
        }
        if action not in valid_actions:
            return False, {"error": f"Acción inválida. Debe ser una de: {', '.join(valid_actions)}"}
        
        payload = {
            "chat_id": self._resolve_chat(chat_id),
            "action": action
        }
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        return self._request("sendChatAction", payload)

    def get_me(self):
        return self._request("getMe", {})

    def get_chat(self, chat_id: Optional[Union[str, int]] = None):
        payload = {"chat_id": self._resolve_chat(chat_id)}
        return self._request("getChat", payload)


def get_telegram_client() -> TelegramClient:
    return TelegramClient()
