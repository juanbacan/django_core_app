"""
Cliente Graph API para Pages de Facebook (contenido + engagement).

Cubre feed, fotos, videos, drafts, programación, comentarios, likes y
diagnóstico de página/credenciales. No incluye Messenger ni Marketing/Ads.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import requests
from django.apps import apps
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

AUTH_ERROR_CODES = {102, 190}


def _api_version() -> str:
    return getattr(settings, 'FACEBOOK_API_VERSION', 'v23.0')


def _timeout() -> int:
    return int(getattr(settings, 'FACEBOOK_TIMEOUT', 30) or 30)


def _rate_limit() -> int:
    return int(getattr(settings, 'FACEBOOK_RATE_LIMIT', 200) or 200)


class FacebookAPIError(Exception):
    """Error de la API de Facebook o del cliente."""

    def __init__(self, message: str, *, code: Any = None, error_type: Any = None):
        super().__init__(message)
        self.code = code
        self.error_type = error_type


def _bool_param(value: bool) -> str:
    """Graph API form-data espera 'true'/'false' en minúsculas."""
    return 'true' if value else 'false'


class FacebookClient:
    """Singleton thread-safe para operar sobre una Page de Facebook."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_credentials()
        return cls._instance

    def _initialize_credentials(self):
        try:
            CredencialesAPI = apps.get_model('core', 'CredencialesAPI')
            credenciales, created = CredencialesAPI.objects.get_or_create(
                defaults={
                    'facebook_page_id': '',
                    'facebook_token': '',
                }
            )
            self.page_id = (credenciales.facebook_page_id or '').strip() or None
            self.token = (credenciales.facebook_token or '').strip() or None
            self._credenciales_id = credenciales.id
            if created:
                logger.info('Se creó un nuevo registro de CredencialesAPI')
        except Exception as e:
            logger.error('Error al inicializar credenciales de Facebook: %s', e)
            self.page_id = None
            self.token = None
            self._credenciales_id = None

    def refresh_credentials(self):
        """Recargar page_id/token desde la base de datos."""
        self._initialize_credentials()

    def _validate_credentials(self):
        if not self.page_id or not self.token:
            raise ValueError(
                'Las credenciales de Facebook no están configuradas. '
                'Actualiza CredencialesAPI (facebook_page_id y facebook_token).'
            )

    def _check_rate_limit(self):
        """Solo verifica el cupo; el incremento ocurre tras un 2xx."""
        key = f'fb_rate_limit_{self.page_id}'
        count = cache.get(key, 0)
        limit = _rate_limit()
        if count >= limit:
            raise FacebookAPIError(
                f'Rate limit excedido: {count}/{limit} requests por hora'
            )

    def _increment_rate_limit(self):
        key = f'fb_rate_limit_{self.page_id}'
        count = cache.get(key, 0)
        cache.set(key, count + 1, 3600)

    def _graph_url(self, endpoint: str, use_page_id: bool) -> str:
        endpoint = str(endpoint).lstrip('/')
        version = _api_version()
        if use_page_id:
            return f'https://graph.facebook.com/{version}/{self.page_id}/{endpoint}'
        return f'https://graph.facebook.com/{version}/{endpoint}'

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict | None = None,
        params: dict | None = None,
        use_page_id: bool = True,
        *,
        _retried_auth: bool = False,
    ):
        """
        Petición genérica a Graph API.

        Returns:
            tuple: (success: bool, response_data: dict)
        """
        try:
            self.refresh_credentials()
            self._validate_credentials()
            self._check_rate_limit()

            url = self._graph_url(endpoint, use_page_id)
            method = method.upper()

            if method == 'POST':
                data = dict(payload or {})
                data['access_token'] = self.token
                response = requests.post(url, data=data, timeout=_timeout())
            elif method == 'GET':
                query = dict(params or {})
                query['access_token'] = self.token
                response = requests.get(url, params=query, timeout=_timeout())
            elif method == 'DELETE':
                query = dict(params or {})
                query['access_token'] = self.token
                response = requests.delete(url, params=query, timeout=_timeout())
            else:
                raise ValueError(f'Método HTTP no soportado: {method}')

            try:
                response_data = response.json()
            except ValueError:
                logger.error(
                    'Respuesta no-JSON de Facebook (%s %s): status=%s body=%r',
                    method,
                    endpoint,
                    response.status_code,
                    response.text[:500],
                )
                return False, {
                    'error': f'Respuesta no-JSON de Facebook (HTTP {response.status_code})',
                    'status_code': response.status_code,
                    'raw': response.text[:500],
                }

            if isinstance(response_data, dict) and 'error' in response_data:
                error_info = response_data['error'] or {}
                error_code = error_info.get('code')
                error_type = error_info.get('type')
                error_message = error_info.get('message', 'Error desconocido')

                if error_code in AUTH_ERROR_CODES and not _retried_auth:
                    logger.warning(
                        'Auth Facebook falló (code=%s); refrescando credenciales y reintentando',
                        error_code,
                    )
                    self.refresh_credentials()
                    return self._request(
                        method,
                        endpoint,
                        payload=payload,
                        params=params,
                        use_page_id=use_page_id,
                        _retried_auth=True,
                    )

                logger.error(
                    'Facebook API Error: %s - Código: %s, Tipo: %s',
                    error_message,
                    error_code,
                    error_type,
                )
                raise FacebookAPIError(
                    f'Facebook API Error: {error_message} (Código: {error_code})',
                    code=error_code,
                    error_type=error_type,
                )

            if response.status_code not in (200, 201):
                logger.error('Error HTTP %s: %s', response.status_code, response_data)
                raise FacebookAPIError(
                    f'Error HTTP {response.status_code}: {response_data}',
                    code=response.status_code,
                )

            self._increment_rate_limit()
            logger.info('%s exitoso en Facebook - Endpoint: %s', method, endpoint)
            return True, response_data

        except requests.exceptions.Timeout:
            error_msg = 'Timeout al conectar con Facebook API'
            logger.error(error_msg)
            return False, {'error': error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = 'Error de conexión con Facebook API'
            logger.error(error_msg)
            return False, {'error': error_msg}
        except FacebookAPIError as e:
            return False, {
                'error': str(e),
                'code': getattr(e, 'code', None),
                'type': getattr(e, 'error_type', None),
            }
        except ValueError as e:
            logger.error('Error de validación: %s', e)
            return False, {'error': str(e)}
        except Exception as e:
            error_msg = f'Error inesperado: {e}'
            logger.error(error_msg)
            return False, {'error': error_msg}

    def _post(self, endpoint, payload):
        return self._request('POST', endpoint, payload=payload, use_page_id=True)

    def _post_direct(self, endpoint, payload):
        return self._request('POST', endpoint, payload=payload, use_page_id=False)

    def _get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params or {}, use_page_id=False)

    def _get_page(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params or {}, use_page_id=True)

    def _delete_direct(self, endpoint, params=None):
        return self._request('DELETE', endpoint, params=params or {}, use_page_id=False)

    # ------------------------------------------------------------------
    # Feed / contenido
    # ------------------------------------------------------------------

    def create_feed_post(
        self,
        message: str = '',
        *,
        link: str | None = None,
        published: bool = True,
        unpublished_content_type: str | None = None,
        scheduled_publish_time: int | None = None,
        attached_media: list[str] | None = None,
        extra: dict | None = None,
    ):
        """
        Crear un post en el feed de la Page.

        attached_media: lista de media_fbid (photo ids unpublished).
        """
        if not (message or '').strip() and not link and not attached_media:
            return False, {'error': 'Se requiere message, link o attached_media'}

        payload: dict[str, Any] = {
            'published': _bool_param(published),
        }
        if message is not None:
            payload['message'] = message
        if link:
            payload['link'] = link
        if unpublished_content_type:
            payload['unpublished_content_type'] = unpublished_content_type
        if scheduled_publish_time is not None:
            payload['scheduled_publish_time'] = int(scheduled_publish_time)
            payload['published'] = _bool_param(False)
        if attached_media:
            for idx, media_fbid in enumerate(attached_media):
                payload[f'attached_media[{idx}]'] = json.dumps({'media_fbid': str(media_fbid)})
        if extra:
            payload.update(extra)

        return self._post('feed', payload)

    def create_draft_post(
        self,
        message: str = '',
        *,
        link: str | None = None,
        attached_media: list[str] | None = None,
        extra: dict | None = None,
    ):
        """Borrador visible en Business Suite (unpublished_content_type=DRAFT)."""
        return self.create_feed_post(
            message,
            link=link,
            published=False,
            unpublished_content_type='DRAFT',
            attached_media=attached_media,
            extra=extra,
        )

    def schedule_feed_post(
        self,
        message: str,
        publish_at_ts: int,
        *,
        link: str | None = None,
        attached_media: list[str] | None = None,
    ):
        """Programar un post (mínimo ~10 minutos en el futuro según Graph)."""
        if not message or not str(message).strip():
            return False, {'error': 'El mensaje no puede estar vacío'}
        now = int(time.time())
        if int(publish_at_ts) < now + 600:
            return False, {'error': 'scheduled_publish_time debe ser al menos 10 minutos en el futuro'}
        return self.create_feed_post(
            message,
            link=link,
            published=False,
            unpublished_content_type='SCHEDULED',
            scheduled_publish_time=int(publish_at_ts),
            attached_media=attached_media,
        )

    def schedule_post(self, message, delay_seconds):
        """Compat: programar con delay en segundos desde ahora."""
        if delay_seconds < 600:
            return False, {'error': 'El delay debe ser al menos 600 segundos (10 minutos)'}
        return self.schedule_feed_post(message, int(time.time()) + int(delay_seconds))

    def publish_post(self, post_id: str):
        """Pasar un draft/unpublished a público."""
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        return self._post_direct(str(post_id), {'is_published': _bool_param(True)})

    def update_post(self, post_id: str, message: str):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        if message is None:
            return False, {'error': 'El mensaje es requerido'}
        return self._post_direct(str(post_id), {'message': message})

    def delete_post(self, post_id: str):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        return self._delete_direct(str(post_id))

    def get_post(self, post_id: str, fields: str = 'id,message,created_time,permalink_url,is_published,status_type'):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        return self._get(str(post_id), {'fields': fields})

    def get_permalink(self, post_id: str):
        """
        Obtener permalink.

        Returns:
            (True, {'permalink_url': url, ...}) o (False, {'error': ...})
        """
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        success, data = self._get(str(post_id), {'fields': 'permalink_url'})
        if success and not data.get('permalink_url'):
            # Fallback razonable si Graph no devuelve permalink
            pid = str(post_id)
            if '_' in pid:
                page_part, post_part = pid.split('_', 1)
                data = {
                    **data,
                    'permalink_url': f'https://www.facebook.com/{page_part}/posts/{post_part}',
                }
            else:
                data = {**data, 'permalink_url': f'https://www.facebook.com/{pid}'}
        return success, data

    def list_feed(self, limit: int = 25, fields: str = 'id,message,created_time,permalink_url,is_published'):
        return self._get_page('feed', {'fields': fields, 'limit': max(1, min(int(limit), 100))})

    # ------------------------------------------------------------------
    # Fotos / media
    # ------------------------------------------------------------------

    def upload_unpublished_photo(self, image_url: str):
        """Subir foto unpublished (para attached_media en un feed post)."""
        if not image_url or not str(image_url).strip():
            return False, {'error': 'La URL de la imagen no puede estar vacía'}
        return self._post(
            'photos',
            {
                'url': image_url,
                'published': _bool_param(False),
            },
        )

    def post_photo(self, image_url: str, caption: str = ''):
        if not image_url or not str(image_url).strip():
            return False, {'error': 'La URL de la imagen no puede estar vacía'}
        return self._post(
            'photos',
            {
                'url': image_url,
                'caption': caption or '',
                'published': _bool_param(True),
            },
        )

    def create_photo_post(
        self,
        image_url: str,
        message: str = '',
        *,
        modo: str = 'public',
        link: str | None = None,
    ):
        """
        Flujo de 2 pasos: foto unpublished + feed con attached_media.

        modo: 'draft' | 'public'
        """
        if not image_url or not str(image_url).strip():
            return False, {'error': 'La URL de la imagen no puede estar vacía'}

        ok, photo_data = self.upload_unpublished_photo(image_url)
        if not ok:
            return False, photo_data

        photo_id = photo_data.get('id')
        if not photo_id:
            return False, {'error': 'Facebook no devolvió id de foto', 'response': photo_data}

        if modo == 'draft':
            ok_feed, feed_data = self.create_draft_post(
                message,
                link=link,
                attached_media=[photo_id],
            )
        else:
            ok_feed, feed_data = self.create_feed_post(
                message,
                link=link,
                published=True,
                attached_media=[photo_id],
            )

        if ok_feed:
            feed_data = {**feed_data, 'photo_id': photo_id}
        return ok_feed, feed_data

    def post_video(
        self,
        video_url: str,
        description: str = '',
        *,
        published: bool = True,
        unpublished_content_type: str | None = None,
        scheduled_publish_time: int | None = None,
    ):
        if not video_url or not str(video_url).strip():
            return False, {'error': 'La URL del video no puede estar vacía'}
        payload: dict[str, Any] = {
            'file_url': video_url,
            'description': description or '',
            'published': _bool_param(published),
        }
        if unpublished_content_type:
            payload['unpublished_content_type'] = unpublished_content_type
        if scheduled_publish_time is not None:
            payload['scheduled_publish_time'] = int(scheduled_publish_time)
            payload['published'] = _bool_param(False)
        return self._post('videos', payload)

    def create_draft_video(self, video_url: str, description: str = ''):
        return self.post_video(
            video_url,
            description,
            published=False,
            unpublished_content_type='DRAFT',
        )

    # ------------------------------------------------------------------
    # Wrappers de compatibilidad
    # ------------------------------------------------------------------

    def post_message(self, message: str):
        if not message or not str(message).strip():
            return False, {'error': 'El mensaje no puede estar vacío'}
        return self.create_feed_post(message, published=True)

    def post_link(self, message: str, link: str):
        if not link or not str(link).strip():
            return False, {'error': 'El enlace no puede estar vacío'}
        return self.create_feed_post(message or '', link=link, published=True)

    # ------------------------------------------------------------------
    # Engagement
    # ------------------------------------------------------------------

    def post_comment(self, post_id: str, message: str):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        if not message or not str(message).strip():
            return False, {'error': 'El mensaje del comentario no puede estar vacío'}
        return self._post_direct(f'{post_id}/comments', {'message': message})

    def reply_to_comment(self, comment_id: str, message: str):
        if not comment_id or not str(comment_id).strip():
            return False, {'error': 'El comment_id no puede estar vacío'}
        if not message or not str(message).strip():
            return False, {'error': 'El mensaje de respuesta no puede estar vacío'}
        return self._post_direct(f'{comment_id}/comments', {'message': message})

    def delete_comment(self, comment_id: str):
        if not comment_id or not str(comment_id).strip():
            return False, {'error': 'El comment_id no puede estar vacío'}
        return self._delete_direct(str(comment_id))

    def get_post_comments(self, post_id: str, limit: int = 25, get_all: bool = False):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}

        params = {
            'fields': 'id,message,created_time,from{name,id},like_count,comment_count',
            'limit': limit,
            'order': 'reverse_chronological',
        }

        if not get_all:
            return self._get(f'{post_id}/comments', params)

        all_comments = []
        while True:
            success, data = self._get(f'{post_id}/comments', params)
            if not success:
                return False, data
            all_comments.extend(data.get('data', []))
            paging = data.get('paging') or {}
            cursors = paging.get('cursors') or {}
            if 'next' not in paging or 'after' not in cursors:
                break
            params['after'] = cursors['after']

        return True, {'data': all_comments, 'total': len(all_comments)}

    def like_post(self, post_id: str):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        return self._post_direct(f'{post_id}/likes', {})

    def unlike_post(self, post_id: str):
        if not post_id or not str(post_id).strip():
            return False, {'error': 'El post_id no puede estar vacío'}
        return self._delete_direct(f'{post_id}/likes')

    # ------------------------------------------------------------------
    # Página / diagnóstico
    # ------------------------------------------------------------------

    def get_page(self, fields: str = 'id,name,link,fan_count,category'):
        self.refresh_credentials()
        if not self.page_id:
            return False, {'error': 'page_id no configurado'}
        return self._get(str(self.page_id), {'fields': fields})

    def validate_credentials(self):
        """Comprobar que page_id + token pueden leer la Page."""
        self.refresh_credentials()
        try:
            self._validate_credentials()
        except ValueError as e:
            return False, {'error': str(e)}
        return self.get_page(fields='id,name')

    def debug_token(self, input_token: str | None = None):
        """
        Inspeccionar un token con /debug_token.

        Requiere que el token actual pueda inspeccionar (app/page token).
        """
        self.refresh_credentials()
        token_to_check = (input_token or self.token or '').strip()
        if not token_to_check:
            return False, {'error': 'No hay token para inspeccionar'}
        return self._get(
            'debug_token',
            {
                'input_token': token_to_check,
                # access_token del request ya se agrega en _request
            },
        )


def get_facebook_client() -> FacebookClient:
    """Instancia singleton del cliente de Facebook."""
    return FacebookClient()
