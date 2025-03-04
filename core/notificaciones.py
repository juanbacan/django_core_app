import json
from django.conf import settings
from django.forms.models import model_to_dict
from pywebpush import WebPushException, webpush
from webpush.models import Group
from threading import Thread
from .models import CustomUser


def _process_subscription_info(subscription):
    """
    Convierte un objeto de suscripción a un formato adecuado para Web Push.
    """
    subscription_data = model_to_dict(subscription, exclude=["browser", "id"])
    return {
        "endpoint": subscription_data.pop("endpoint"),
        "keys": {
            "p256dh": subscription_data.pop("p256dh"),
            "auth": subscription_data.pop("auth")
        }
    }


def _get_vapid_data():
    """
    Obtiene la configuración de VAPID de los settings.
    """
    webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
    vapid_private_key = webpush_settings.get('VAPID_PRIVATE_KEY')
    vapid_admin_email = webpush_settings.get('VAPID_ADMIN_EMAIL')
    
    if vapid_private_key:
        return {
            'vapid_private_key': vapid_private_key,
            'vapid_claims': {"sub": f"mailto:{vapid_admin_email}"}
        }
    return {}


def _send_push_notification(recipient, payload, ttl=0):
    """
    Envía una notificación Web Push a una suscripción.
    """
    vapid_data = _get_vapid_data()
    payload = json.dumps(payload)

    subscription_data = _process_subscription_info(recipient.subscription)
    try:
        webpush(subscription_info=subscription_data, data=payload, ttl=ttl, **vapid_data)
        print("Notificación enviada correctamente ************************************************** ")
    except WebPushException as e:
        print("Error WebPush No encontrado ************************************************** ")
        if e.response.status_code == 410:
            recipient.subscription.delete()
        else:
            print(f"Error al enviar la notificación: {e}")
    except Exception as e:
        print(f"Error al enviar la notificación *******************************")


class NotificationThread(Thread):
    """
    Clase base para enviar notificaciones en un hilo.
    """
    def __init__(self, recipients, payload, ttl=0):
        self.recipients = recipients
        self.payload = payload
        self.ttl = ttl
        super().__init__()

    def run(self):
        """
        Enviar notificaciones a todos los destinatarios.
        """
        for recipient in self.recipients:
            _send_push_notification(recipient, self.payload, self.ttl)



# ************************************************************************************************
# Funciones
# ************************************************************************************************


# *********************************************************************************
# Envia una notificación Webpush a un Usuario
# *********************************************************************************
def send_notification_to_user(user, payload, ttl=0):
    """
    Envía una notificación a un usuario.
    """
    recipients = user.webpush_info.select_related("subscription")
    NotificationThread(recipients, payload, ttl).start()


# *********************************************************************************
# Envia una notificación Webpush a todo un Grupo
# *********************************************************************************
def send_notification_to_group(group_name, payload, ttl=0):
    """
    Envía una notificación a un grupo.
    """
    recipients = Group.objects.get(name=group_name).webpush_info.select_related("subscription")
    NotificationThread(recipients, payload, ttl).start()


# *********************************************************************************
# Envia una notificación a través de la Aplicacion Web
# *********************************************************************************
def notify_user(usuario_notificado, usuario_notifica, url, mensaje = "", tipo='agradecimiento_solucion'):
    """
    Crea una notificación para un usuario en la aplicación.
    """

    from .models import NotificacionUsuario, NotificacionUsuarioCount, TipoNotificacion
    tipo_notificacion = TipoNotificacion.objects.get(tipo=tipo)
    if not tipo_notificacion:
        return
    try:
        notificacion = NotificacionUsuario.objects.create(
            usuario_notificado=usuario_notificado,
            usuario_notifica=usuario_notifica,
            tipo=tipo_notificacion,
            url=url,
            mensaje=mensaje,
        )

        numero_noti, _ = NotificacionUsuarioCount.objects.get_or_create(usuario=usuario_notificado)
        numero_noti.numero = numero_noti.numero + 1
        numero_noti.save()
        return notificacion
    
    except Exception as e:
        return

# *********************************************************************************
# Notifica a un usuario en la Aplicación y mediante Webpush notification
# *********************************************************************************
def notify_push_app_user(usuario_notificado: CustomUser, usuario_notifica: CustomUser, url: str, mensaje: str = "", tipo: str = 'agradecimiento_solucion'):
    from .models import TipoNotificacion, AplicacionWeb
    try:
        logo_url = AplicacionWeb.objects.first().logo.url
        URL_BASE = settings.URL_BASE
        tipo_notificacion = TipoNotificacion.objects.get(tipo=tipo)
        notificacion = notify_user(
            usuario_notificado=usuario_notificado,
            usuario_notifica=usuario_notifica,
            tipo=tipo_notificacion,
            url=url,
            mensaje=mensaje,
        )

        payload = {
            "head": notificacion.titulo(),
            "body": notificacion.mensaje_final(),
            'icon': f"{URL_BASE}{logo_url}",
            'url': url,
        }

        send_notification_to_user(usuario_notificado, payload)
        
    except Exception as e:
        print(e)
        return
    
