from .models import Alerta
from .models import AplicacionWeb, Alerta
from .models import NotificacionUsuario, NotificacionUsuarioCount
from django.conf import settings

from .avisos_masivos import avisos_masivos_pendientes_para_usuario, contar_pendientes_avisos_masivos


def main_context(request):
    context = {}
    context['alertas'] = Alerta.objects.filter(activo=True)
    context['application'] = AplicacionWeb.objects.first()

    if settings.WEBPUSH_HABILITADO:
        context['webpush_habilitado'] = True

    if request.user.is_authenticated:
        notificaciones = NotificacionUsuario.objects.filter(
            usuario_notificado=request.user
        ).order_by('-id')[:5]
        noti_count = NotificacionUsuarioCount.objects.filter(
            usuario=request.user
        ).first()
        num_individuales = noti_count.numero if noti_count else 0
        num_masivos = contar_pendientes_avisos_masivos(request.user)
        context['num_notificaciones'] = num_individuales
        context['num_avisos_masivos_pendientes'] = num_masivos
        context['num_notificaciones_badge'] = num_individuales + num_masivos
        context['notificaciones'] = notificaciones
        context['avisos_masivos_pendientes'] = list(
            avisos_masivos_pendientes_para_usuario(request.user)[:5]
        )
    return context
