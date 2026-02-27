import requests
import time
import logging
import threading
from django.apps import apps
from django.core.cache import cache
from django.conf import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración de API
FACEBOOK_API_VERSION = getattr(settings, 'FACEBOOK_API_VERSION', 'v23.0')
FACEBOOK_TIMEOUT = getattr(settings, 'FACEBOOK_TIMEOUT', 30)
FACEBOOK_RATE_LIMIT = getattr(settings, 'FACEBOOK_RATE_LIMIT', 200)  # Requests por hora

class FacebookAPIError(Exception):
    """Excepción personalizada para errores de la API de Facebook"""
    pass

class FacebookClient:
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
    
    def _initialize_credentials(self):
        try:
            # Obtener el modelo CredencialesAPI dinámicamente
            CredencialesAPI = apps.get_model('core', 'CredencialesAPI')
            
            # Obtener o crear las credenciales
            credenciales, created = CredencialesAPI.objects.get_or_create(
                defaults={
                    'facebook_page_id': '',
                    'facebook_token': ''
                }
            )
            
            self.page_id = credenciales.facebook_page_id
            self.token = credenciales.facebook_token
            self._credenciales_id = credenciales.id
            
            if created:
                logger.info("Se creó un nuevo registro de credenciales de Facebook")
            
        except Exception as e:
            logger.error(f"Error al inicializar credenciales de Facebook: {e}")
            self.page_id = None
            self.token = None
            self._credenciales_id = None
    
    def _validate_credentials(self):
        """Validar que las credenciales estén configuradas"""
        if not self.page_id or not self.token:
            raise ValueError("Las credenciales de Facebook no están configuradas. Actualiza el modelo CredencialesAPI.")
    
    def _check_rate_limit(self):
        """Verificar límite de requests para evitar bloqueos de Facebook"""
        key = f'fb_rate_limit_{self.page_id}'
        count = cache.get(key, 0)
        if count >= FACEBOOK_RATE_LIMIT:
            raise FacebookAPIError(f"Rate limit excedido: {count}/{FACEBOOK_RATE_LIMIT} requests por hora")
        cache.set(key, count + 1, 3600)  # Expira en 1 hora
    
    def _request(self, method, endpoint, payload=None, params=None, use_page_id=True):
        """Método genérico para realizar peticiones a Facebook API
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            payload: Data para POST (dict)
            params: Query parameters para GET/DELETE (dict)
            use_page_id: Si debe incluir page_id en la URL
        
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        try:
            self._validate_credentials()
            self._check_rate_limit()
            
            # Construir URL
            if use_page_id:
                url = f"https://graph.facebook.com/{FACEBOOK_API_VERSION}/{self.page_id}/{endpoint}"
            else:
                url = f"https://graph.facebook.com/{FACEBOOK_API_VERSION}/{endpoint}"
            
            # Preparar datos
            if method in ['POST']:
                if payload is None:
                    payload = {}
                payload['access_token'] = self.token
                r = requests.post(url, data=payload, timeout=FACEBOOK_TIMEOUT)
            elif method in ['GET']:
                if params is None:
                    params = {}
                params['access_token'] = self.token
                r = requests.get(url, params=params, timeout=FACEBOOK_TIMEOUT)
            elif method in ['DELETE']:
                if params is None:
                    params = {}
                params['access_token'] = self.token
                r = requests.delete(url, params=params, timeout=FACEBOOK_TIMEOUT)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            # Parsear respuesta
            try:
                response_data = r.json()
            except ValueError:
                # Si no hay JSON válido, asumir éxito
                response_data = {"success": True}
            
            # Verificar errores en la respuesta
            if 'error' in response_data:
                error_info = response_data['error']
                error_message = f"Facebook API Error: {error_info.get('message', 'Error desconocido')}"
                error_code = error_info.get('code', 'N/A')
                error_type = error_info.get('type', 'N/A')
                
                logger.error(f"{error_message} - Código: {error_code}, Tipo: {error_type}")
                raise FacebookAPIError(f"{error_message} (Código: {error_code})")
            
            # Verificar status code
            if r.status_code not in [200, 201]:
                logger.error(f"Error HTTP {r.status_code}: {response_data}")
                raise FacebookAPIError(f"Error HTTP {r.status_code}: {response_data}")
            
            logger.info(f"{method} exitoso en Facebook - Endpoint: {endpoint}")
            return True, response_data
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout al conectar con Facebook API"
            logger.error(error_msg)
            return False, {"error": error_msg}
            
        except requests.exceptions.ConnectionError:
            error_msg = "Error de conexión con Facebook API"
            logger.error(error_msg)
            return False, {"error": error_msg}
            
        except FacebookAPIError as e:
            return False, {"error": str(e)}
            
        except ValueError as e:
            logger.error(f"Error de validación: {e}")
            return False, {"error": str(e)}
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}
    
    def _post(self, endpoint, payload):
        """Método privado para realizar peticiones POST a Facebook API"""
        return self._request('POST', endpoint, payload=payload, use_page_id=True)

    def _post_direct(self, endpoint, payload):
        """Método privado para POST directo sin agregar page_id (para comentarios)"""
        return self._request('POST', endpoint, payload=payload, use_page_id=False)

    def _get(self, endpoint, params):
        """Método privado para realizar peticiones GET a Facebook API"""
        return self._request('GET', endpoint, params=params, use_page_id=False)

    def post_message(self, message):
        """Publicar un mensaje simple en Facebook
        
        Args:
            message: Texto del mensaje a publicar
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not message or not message.strip():
            return False, {"error": "El mensaje no puede estar vacío"}
        return self._post('feed', {"message": message})

    def post_link(self, message, link):
        """Publicar un mensaje con enlace en Facebook
        
        Args:
            message: Texto del mensaje
            link: URL del enlace a compartir
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not link or not link.strip():
            return False, {"error": "El enlace no puede estar vacío"}
        if not message:
            message = ""
        return self._post('feed', {"message": message, "link": link})

    def post_photo(self, image_url, caption=""):
        """Publicar una foto en Facebook desde una URL pública
        
        Args:
            image_url: URL pública de la imagen
            caption: Texto descriptivo de la foto (opcional)
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not image_url or not image_url.strip():
            return False, {"error": "La URL de la imagen no puede estar vacía"}
        return self._post('photos', {"url": image_url, "caption": caption})

    def post_video(self, video_url, description=""):
        """Publicar un video en Facebook desde una URL pública
        
        Args:
            video_url: URL pública del video
            description: Texto descriptivo del video (opcional)
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not video_url or not video_url.strip():
            return False, {"error": "La URL del video no puede estar vacía"}
        return self._post('videos', {"file_url": video_url, "description": description})

    def schedule_post(self, message, delay_seconds):
        """Programar un post para publicarse en el futuro
        
        Args:
            message: Texto del mensaje
            delay_seconds: Segundos desde ahora para la publicación
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not message or not message.strip():
            return False, {"error": "El mensaje no puede estar vacío"}
        if delay_seconds < 600:  # Mínimo 10 minutos
            return False, {"error": "El delay debe ser al menos 600 segundos (10 minutos)"}
        
        future = int(time.time()) + delay_seconds
        payload = {
            "message": message,
            "published": "false",
            "scheduled_publish_time": future
        }
        return self._post('feed', payload)

    def get_permalink(self, post_id):
        """Obtener el enlace permanente de un post"""
        return self._get(post_id, {"fields": "permalink_url"})
    
    def post_comment(self, post_id, message):
        """Publicar un comentario en un post específico
        
        Args:
            post_id: ID del post donde comentar
            message: Texto del comentario
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not post_id or not str(post_id).strip():
            return False, {"error": "El post_id no puede estar vacío"}
        if not message or not message.strip():
            return False, {"error": "El mensaje del comentario no puede estar vacío"}
        return self._post_direct(f"{post_id}/comments", {"message": message})
    
    def reply_to_comment(self, comment_id, message):
        """Responder a un comentario específico
        
        Args:
            comment_id: ID del comentario a responder
            message: Texto de la respuesta
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not comment_id or not str(comment_id).strip():
            return False, {"error": "El comment_id no puede estar vacío"}
        if not message or not message.strip():
            return False, {"error": "El mensaje de respuesta no puede estar vacío"}
        return self._post_direct(f"{comment_id}/comments", {"message": message})
    
    def get_post_comments(self, post_id, limit=25, get_all=False):
        """Obtener comentarios de un post
        
        Args:
            post_id: ID del post
            limit: Número máximo de comentarios por página (default: 25)
            get_all: Si es True, obtiene todos los comentarios usando paginación
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not post_id or not str(post_id).strip():
            return False, {"error": "El post_id no puede estar vacío"}
        
        params = {
            "fields": "id,message,created_time,from{name,id},like_count,comment_count",
            "limit": limit,
            "order": "reverse_chronological"
        }
        
        if not get_all:
            return self._get(f"{post_id}/comments", params)
        
        # Obtener todos los comentarios con paginación
        all_comments = []
        while True:
            success, data = self._get(f"{post_id}/comments", params)
            if not success:
                return False, data
            
            all_comments.extend(data.get('data', []))
            
            # Verificar si hay más páginas
            if 'paging' not in data or 'next' not in data['paging']:
                break
            
            # Obtener cursor para siguiente página
            if 'cursors' in data['paging'] and 'after' in data['paging']['cursors']:
                params['after'] = data['paging']['cursors']['after']
            else:
                break
        
        return True, {'data': all_comments, 'total': len(all_comments)}
    
    def like_post(self, post_id):
        """Dar me gusta a un post
        
        Args:
            post_id: ID del post
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not post_id or not str(post_id).strip():
            return False, {"error": "El post_id no puede estar vacío"}
        return self._post(f"{post_id}/likes", {})
    
    def unlike_post(self, post_id):
        """Quitar me gusta de un post
        
        Args:
            post_id: ID del post
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not post_id or not str(post_id).strip():
            return False, {"error": "El post_id no puede estar vacío"}
        return self._request('DELETE', f"{post_id}/likes", params={}, use_page_id=False)
    
    def delete_post(self, post_id):
        """Eliminar un post
        
        Args:
            post_id: ID del post a eliminar
            
        Returns:
            tuple: (success: bool, response_data: dict)
        """
        if not post_id or not str(post_id).strip():
            return False, {"error": "El post_id no puede estar vacío"}
        return self._request('DELETE', post_id, params={}, use_page_id=False)
    
    def refresh_credentials(self):
        """Refrescar las credenciales desde la base de datos"""
        self._initialize_credentials()

# Función helper para obtener el cliente de Facebook
def get_facebook_client():
    """Función de conveniencia para obtener la instancia del cliente de Facebook"""
    return FacebookClient()

# Ejemplo de uso con manejo de errores:
# fb = get_facebook_client()
# 
# # Publicar post y comentarlo
# success, response = fb.post_message("Hola, Precavidos: inscripciones abiertas.")
# if success:
#     post_id = response['id']
#     print(f"Post publicado exitosamente: {post_id}")
#     
#     # Comentar el post recién creado
#     success_comment, comment_response = fb.post_comment(post_id, "¡No olvides revisar todos los requisitos!")
#     if success_comment:
#         comment_id = comment_response['id']
#         print(f"Comentario agregado: {comment_id}")
#         
#         # Responder al comentario
#         fb.reply_to_comment(comment_id, "Cualquier duda, escríbenos.")
#     
#     # Dar me gusta al post
#     fb.like_post(post_id)
#     
#     # Obtener comentarios del post
#     success_comments, comments_data = fb.get_post_comments(post_id)
#     if success_comments:
#         print(f"El post tiene {len(comments_data.get('data', []))} comentarios")
# else:
#     print(f"Error al publicar: {response['error']}")
# 
# # Otros ejemplos
# success, response = fb.post_link("Guía completa de inscripciones 2025", "https://tu-dominio.com/guia-inscripciones")
# success, response = fb.post_photo("https://tu-dominio.com/imagen.jpg", "Fechas de inscripción ➜ https://tu-dominio.com/fechas")
# success, response = fb.post_video("https://tu-dominio.com/video.mp4", "Consejos para rendir el examen")
# success, response = fb.schedule_post("Recordatorio: simulador actualizado hoy.", 2*60*60)
# success, response = fb.get_permalink("102993938392964_123456789012345")