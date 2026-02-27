import re
import logging
import requests
from typing import Optional
from threading import Thread, Lock
from functools import wraps
    
from evolutionapi.client import EvolutionClient
from evolutionapi.models.message import TextMessage, ButtonMessage, Button

from django.conf import settings
from core.models import CredencialesAPI

logger = logging.getLogger(__name__)


EC_CC = "593"

def normalize_ec_mobile(raw: str, *, return_plus: bool = False, raise_on_fail: bool = False) -> Optional[str]:
    """Normaliza celulares de Ecuador al formato 5939XXXXXXXX (sin '+')."""
    if raw is None:
        if raise_on_fail:
            raise ValueError("Número vacío o None.")
        return None

    s = re.sub(r"\D+", "", raw)  # deja solo dígitos
    if not s:
        if raise_on_fail:
            raise ValueError("No se encontraron dígitos en la entrada.")
        return None

    # quitar prefijo internacional '00'
    if s.startswith("00"):
        s = s[2:]

    res = None

    # casos con código de país
    if s.startswith(EC_CC):
        rest = s[len(EC_CC):]
        if rest.startswith("0"):   # corrige '5930...' -> '593...'
            rest = rest[1:]
        if len(rest) == 9 and rest.startswith("9"):
            res = EC_CC + rest

    # formatos nacionales
    if res is None:
        if s.startswith("0") and len(s) == 10 and s[1] == "9":  # 09XXXXXXXXX
            res = EC_CC + s[1:]
        elif len(s) == 9 and s.startswith("9"):                 # 9XXXXXXXX
            res = EC_CC + s
        else:
            if raise_on_fail:
                raise ValueError(f"Número no parece celular ecuatoriano válido: {raw!r}")
            return None

    # filtro simple: descarta 999999999, etc.
    subscriber = res[len(EC_CC):]
    if len(set(subscriber)) == 1:
        if raise_on_fail:
            raise ValueError("Número inválido (dígitos repetidos).")
        return None

    return ("+" + res) if return_plus else res

def async_thread(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        Thread(target=func, args=args, kwargs=kwargs).start()
    return wrapper


class EvolutionClientManager:
    """Gestiona la configuración y instancia de EvolutionClient sin variables globales."""
    
    def __init__(self):
        self._client = None
        self._last_config = None
        self._lock = Lock()

    def _load_evolution_config(self):
        """Devuelve un dict con la configuración, priorizando la primera fila de CredencialesAPI.
        Fallback a variables en settings si no hay registro en BD.
        """
        cfg = {}
        try:
            info = CredencialesAPI.objects.first()
        except Exception:
            info = None

        if info:
            cfg['base_url'] = getattr(info, 'evolution_api_url', None) or getattr(settings, 'EVOLUTION_API_URL', '')
            cfg['api_token'] = getattr(info, 'evolution_api_key', None) or getattr(settings, 'EVOLUTION_API_KEY', '')
            cfg['instance_id'] = getattr(info, 'evolution_instance_id', None) or getattr(settings, 'EVOLUTION_INSTANCE_ID', '')
            cfg['instance_token'] = getattr(info, 'evolution_instance_token', None) or getattr(settings, 'EVOLUTION_INSTANCE_TOKEN', '')
        else:
            cfg['base_url'] = getattr(settings, 'EVOLUTION_API_URL', '')
            cfg['api_token'] = getattr(settings, 'EVOLUTION_API_KEY', '')
            cfg['instance_id'] = getattr(settings, 'EVOLUTION_INSTANCE_ID', '')
            cfg['instance_token'] = getattr(settings, 'EVOLUTION_INSTANCE_TOKEN', '')

        return cfg



    def get_client(self, force_refresh: bool = False):
        """Devuelve una instancia de EvolutionClient, recreándola si la configuración cambió.
        
        Thread-safe: usa lock para evitar race conditions.
        """
        with self._lock:
            cfg = self._load_evolution_config()
            
            # Recrear cliente si es forzado o si la configuración cambió
            if force_refresh or self._client is None or self._last_config != cfg:
                self._client = EvolutionClient(base_url=cfg['base_url'], api_token=cfg['api_token'])
                self._last_config = cfg.copy()
                logger.info("EvolutionClient recreado")
            
            return self._client, cfg


# Instancia singleton del manager
_evolution_manager = EvolutionClientManager()


def get_evolution_client(force_refresh: bool = False):
    """Interfaz pública para obtener el cliente Evolution y su configuración."""
    return _evolution_manager.get_client(force_refresh)

@async_thread
def send_whatsapp_text(number: str, text: str, delay: int = 0):
    """
    Enviar un mensaje de texto a través de WhatsApp (asíncrono).
    number: número del receptor (incluyendo código de país) o ID de grupo (formato @g.us)
    text: texto del mensaje
    delay: retraso opcional en milisegundos
    """
    try:
        # Verificar si es un grupo de WhatsApp (termina en @g.us) o un número normal
        if number.endswith('@g.us'):
            final_number = number
        else:
            final_number = normalize_ec_mobile(number, raise_on_fail=True)
            
        msg = TextMessage(
            number=f"{final_number}",
            text=text,
            delay=delay,
        )

        client, cfg = get_evolution_client()
        result = client.messages.send_text(cfg['instance_id'], msg, cfg['instance_token'])
        logger.info(f"Mensaje enviado a {final_number}")
        return result
    except Exception as e:
        logger.error(f"Error al enviar mensaje de WhatsApp a {number}: {e}")


@async_thread
def send_whatsapp_buttons(number: str, title: str, description: str, footer: str, buttons: list, delay: int = 0):
    """
    Enviar botones a través de WhatsApp (asíncrono).
    number: número del receptor (incluyendo código de país) o ID de grupo (formato @g.us)
    title: título del mensaje
    description: texto principal del mensaje
    footer: texto en la parte inferior
    buttons: lista de dicts con estructura {"type": "reply"|"url"|"phoneNumber"|"copyCode", ...}
    delay: retraso opcional en milisegundos
    """
    try:
        # Verificar si es un grupo de WhatsApp (termina en @g.us) o un número normal
        if number.endswith('@g.us'):
            normalized = number
        else:
            normalized = normalize_ec_mobile(number, raise_on_fail=True)
        
        button_objects = []
        for b in buttons:
            button_objects.append(Button(**b))

        msg = ButtonMessage(
            number=normalized,
            title=title,
            description=description,
            footer=footer,
            buttons=button_objects,
            delay=delay
        )

        client, cfg = get_evolution_client()
        result = client.messages.send_buttons(
            cfg['instance_id'],
            msg,
            cfg['instance_token']
        )
        logger.info(f"Botones enviados a {normalized}")
        return result
    except Exception as e:
        logger.error(f"Error al enviar botones de WhatsApp a {number}: {e}")


def send_whatsapp_text_sync(number: str, text: str, delay: int = 0):
    """
    Enviar un mensaje de texto a través de WhatsApp de forma síncrona.
    Para usar en funciones que necesitan el resultado inmediatamente.
    
    Args:
        number: número del receptor (incluyendo código de país), ID de grupo (@g.us) o URL de grupo
        text: texto del mensaje
        delay: retraso opcional en milisegundos
    
    Returns:
        dict: Respuesta de la API con status, resultado o error
    """
    try:
        # Procesar el número/canal de destino
        final_number = number
        
        if number.startswith('https://chat.whatsapp.com/'):
            logger.info(f"Detectada URL de grupo: {number}")
            final_number = number
        elif number.endswith('@g.us'):
            logger.debug(f"Enviando a grupo con ID: {number}")
            final_number = number
        else:
            final_number = normalize_ec_mobile(number, raise_on_fail=True)
            logger.debug(f"Enviando a número normalizado: {final_number}")
        
        # Obtener configuración desde el manager (evita duplicación de código)
        client, cfg = get_evolution_client()
        
        if not all([cfg['base_url'], cfg['instance_id'], cfg['api_token']]):
            logger.error('Faltan credenciales de Evolution API')
            return {'error': 'Faltan credenciales de Evolution API'}
        
        url = f"{cfg['base_url']}/message/sendText/{cfg['instance_id']}"
        headers = {
            'Content-Type': 'application/json',
            'apikey': cfg['api_token'],
        }
        
        data = {
            'number': final_number,
            'text': text
        }
        
        if delay > 0:
            data['delay'] = delay
        
        logger.debug(f"Enviando a Evolution API: {url}")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        logger.debug(f"Status de respuesta: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"Mensaje enviado exitosamente a {final_number}")
            return result
        else:
            error_detail = response.text
            logger.warning(f"Fallo al enviar mensaje: {response.status_code} - {error_detail}")
            return {
                'status': response.status_code,
                'error': error_detail,
                'response': response.json() if response.content else None
            }
            
    except Exception as e:
        logger.exception(f"Excepción al enviar mensaje de WhatsApp síncrono: {e}")
        return {'error': str(e)}