from .models import Alerta
from .models import AplicacionWeb, Alerta
from .models import NotificacionUsuario, NotificacionUsuarioCount
from django.conf import settings


def main_context(request):
    context = {}
    context['alertas'] = Alerta.objects.filter(activo=True)
    context['application'] = AplicacionWeb.objects.first()

    if settings.WEBPUSH_HABILITADO:
        context['webpush_habilitado'] = True

    if request.user.is_authenticated:
        notificaciones = NotificacionUsuario.objects.filter(usuario_notificado=request.user).order_by('-id')[:5]        
        noti_count = NotificacionUsuarioCount.objects.filter(usuario=request.user).first()        
        context['num_notificaciones'] = noti_count.numero if noti_count else 0
        context['notificaciones'] = notificaciones
    return context
