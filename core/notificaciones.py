import json
import logging
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.core.mail import send_mail
from django.forms.models import model_to_dict
from pywebpush import WebPushException, webpush

from webpush.models import Group
from .models import CustomUser


logger = logging.getLogger(__name__)


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


def _dispatch_webpush(recipient, payload_json, vapid_data, ttl=0):
    """
    Lógica central de envío y manejo de suscripciones inválidas.
    """
    subscription_data = _process_subscription_info(recipient.subscription)
    try:
        webpush(
            subscription_info=subscription_data,
            data=payload_json,
            ttl=ttl,
            **vapid_data,
        )
        logger.info("[WebPush OK] %s", recipient)
        return "sent"
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            logger.warning("[WebPush 410] Borrando suscripción muerta: %s", recipient)
            recipient.subscription.delete()
            return "deleted"
        else:
            status = e.response.status_code if e.response else "No response"
            logger.error("[WebPush ERROR] Usuario: %s, Status: %s", recipient, status)
            logger.exception("Error al enviar la notificación")
            return "failed"
    except Exception as e:
        logger.exception("[WebPush Error] Error inesperado")
        return "failed"


def _build_report_recipients(report_email=None):
    recipients = []
    if report_email:
        recipients.append(report_email)

    configured_recipients = getattr(settings, "WEBPUSH_REPORT_EMAILS", [])
    if isinstance(configured_recipients, str):
        configured_recipients = [email.strip() for email in configured_recipients.split(",") if email.strip()]
    recipients.extend(configured_recipients)

    if not recipients:
        superusers = (
            CustomUser.objects
            .filter(is_superuser=True)
            .exclude(email__isnull=True)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        recipients.extend(list(superusers))

    if not recipients and getattr(settings, "EMAIL_HOST_USER", None):
        recipients.append(settings.EMAIL_HOST_USER)

    # Deduplicar conservando orden.
    return list(dict.fromkeys(recipients))


def _send_massive_report(report, report_context, report_email=None):
    recipients = _build_report_recipients(report_email=report_email)
    if not recipients:
        logger.warning("[WebPush WARN] No hay destinatarios para el reporte de envio masivo")
        return

    group_name = report_context.get("group_name", "N/A")
    notification_head = report_context.get("head", "N/A")
    notification_url = report_context.get("url", "N/A")
    total = report.get("total", 1) or 1
    exito_pct = (report.get("sent", 0) / total) * 100

    subject = f"[WebPush] Reporte envio masivo - Grupo {group_name}"
    body = (
        "Se ha completado el envio masivo de notificaciones push.\n\n"
        f"Grupo: {group_name}\n"
        f"Titulo notificacion: {notification_head}\n"
        f"URL destino: {notification_url}\n\n"
        f"Total procesadas: {report.get('total', 0)}\n"
        f"Enviadas OK: {report.get('sent', 0)}\n"
        f"Suscripciones eliminadas (410): {report.get('deleted', 0)}\n"
        f"Fallidas: {report.get('failed', 0)}\n"
        f"Porcentaje de éxito: {exito_pct:.2f}%\n"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    try:
        send_mail(subject, body, from_email, recipients, fail_silently=False)
        logger.info("[WebPush REPORT] Reporte enviado a: %s", ", ".join(recipients))
    except Exception as e:
        logger.exception("[WebPush ERROR] No se pudo enviar el reporte")


class NotificationThread(Thread):
    """
    Clase base para enviar notificaciones en un hilo.
    """
    def __init__(self, recipients, payload, ttl=0, report_enabled=False, report_context=None, report_email=None):
        self.recipients = recipients
        self.payload_json = json.dumps(payload)
        self.vapid_data = _get_vapid_data()
        self.ttl = ttl
        self.report_enabled = report_enabled
        self.report_context = report_context or {}
        self.report_email = report_email
        super().__init__()

    def run(self):
        """
        Enviar notificaciones a todos los destinatarios.
        """
        report = {
            "total": len(self.recipients),
            "sent": 0,
            "deleted": 0,
            "failed": 0,
        }

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for recipient in self.recipients:
                future = executor.submit(
                    _dispatch_webpush,
                    recipient,
                    self.payload_json,
                    self.vapid_data,
                    self.ttl,
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    status = future.result()
                except Exception:
                    report["failed"] += 1
                    continue

                if status == "sent":
                    report["sent"] += 1
                elif status == "deleted":
                    report["deleted"] += 1
                else:
                    report["failed"] += 1

        if self.report_enabled:
            _send_massive_report(
                report=report,
                report_context=self.report_context,
                report_email=self.report_email,
            )

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
    recipients = user.webpush_info.select_related("subscription").order_by("-id")
    NotificationThread(recipients, payload, ttl).start()


# *********************************************************************************
# Envia una notificación Webpush a todo un Grupo
# *********************************************************************************
def send_notification_to_group(group_name, payload, ttl=0, report_email=None):
    """
    Envía una notificación a un grupo.
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        logger.warning("[WebPush WARN] No existe el grupo '%s'", group_name)
        return False
    except Group.MultipleObjectsReturned:
        group = Group.objects.filter(name=group_name).order_by("id").first()
        if not group:
            logger.warning("[WebPush WARN] No se pudo resolver el grupo '%s'", group_name)
            return False

    recipients = list(
        group.webpush_info
        .select_related("subscription")
        .filter(subscription__isnull=False)
        .order_by("-id")
    )
    if not recipients:
        logger.warning("[WebPush WARN] El grupo '%s' no tiene suscripciones activas", group_name)
        return False

    NotificationThread(
        recipients,
        payload,
        ttl,
        report_enabled=True,
        report_context={
            "group_name": group_name,
            "head": payload.get("head", ""),
            "url": payload.get("url", ""),
        },
        report_email=report_email,
    ).start()
    return True


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
        logger.exception("Error al enviar notificación push app")
        return
    
