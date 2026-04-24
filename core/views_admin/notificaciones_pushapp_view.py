from django.shortcuts import render
from django.contrib import messages

from django.conf import settings
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from core.models import CustomUser, AplicacionWeb, AvisoMasivo
from core.views import ViewAdministracionBase
from core.administracion_forms import NotificacionPushUsuarioForm, NotificacionAppUsuarioForm, \
    NotificacionPushAppUsuarioForm, NotificacionPushMasivaForm, AvisoMasivoEnviarForm, \
    NotificacionAndroidMasivaForm

from core.utils import success_json, error_json
from core.notificaciones import send_notification_to_group, send_notification_to_user
from core.notificaciones  import notify_user, notify_push_app_user


def _success_recarga(request, mensaje):
    """
    - messages.success: flash de Django para al recargar (plantilla con {% if messages %}).
    - success_json: para el JSON del modal (redirected + url).
    """
    messages.success(request, mensaje, fail_silently=True)
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        url = referer
    else:
        url = request.build_absolute_uri(request.get_full_path())
    return success_json(mensaje=mensaje, url=url)


class NotificacionesPushAppView(ViewAdministracionBase):

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        
        return error_json(mensaje="Acción no permitida")
    
    def post_notificaciones_push_usuario(self, request, context, *args, **kwargs):
        logo_url = AplicacionWeb.objects.first().logo.url

        form = NotificacionPushUsuarioForm(request.POST)
        if form.is_valid():
            URL_BASE = settings.URL_BASE
            user = form.cleaned_data['usuario']
            payload = {
                "head": form.cleaned_data['head'], 
                "body": form.cleaned_data['body'],
                'icon': f"{URL_BASE}{logo_url}",
                'url': form.cleaned_data['url'],
            }
            send_notification_to_user(user=user, payload=payload)
            return _success_recarga(request, "Notificación enviada correctamente")
        else:
            return error_json(mensaje=str(form.errors))
        
    def post_notificaciones_app_usuario(self, request, context, *args, **kwargs):
        form = NotificacionAppUsuarioForm(request.POST)
        if form.is_valid():
            usuario_notificado = form.cleaned_data['usuario_notificado']
            tipo = form.cleaned_data['tipo_notificacion']
            mensaje = form.cleaned_data['mensaje']
            url = form.cleaned_data['url']
            notify_user(
                usuario_notifica=CustomUser.objects.get(username="juanbacan"),
                usuario_notificado=usuario_notificado,
                tipo=tipo.tipo, 
                mensaje=mensaje, 
                url=url
            )
            return _success_recarga(request, "Notificación enviada correctamente")
        else:
            return error_json(mensaje=str(form.errors))
        
    def post_notificaciones_pushapp_usuario(self, request, context, *args, **kwargs):
        form = NotificacionPushAppUsuarioForm(request.POST)
        if form.is_valid():
            usuario_notificado = form.cleaned_data['usuario_notificado']
            body = form.cleaned_data['body']
            url = form.cleaned_data['url']
            tipo = form.cleaned_data['tipo_notificacion']
            notify_push_app_user(
                usuario_notifica=CustomUser.objects.get(username="juanbacan"),
                usuario_notificado=usuario_notificado,
                tipo=tipo.tipo,
                url=url,
                mensaje=body,
            )
            return _success_recarga(request, "Notificación enviada correctamente")

    def post_notificaciones_push_masiva(self, request, context, *args, **kwargs):
        application = AplicacionWeb.objects.first()
        logo_url = application.logo.url if application and application.logo else ''
        group_name = application.group_name_webpush if application and application.group_name_webpush else 'Main'
        form = NotificacionPushMasivaForm(request.POST)
        if form.is_valid():
            URL_BASE = settings.URL_BASE
            payload = {
                "head": form.cleaned_data['head'], 
                "body": form.cleaned_data['body'],
                'icon': f"{URL_BASE}{logo_url}",
                'url': form.cleaned_data['url'],
            }
            sent = send_notification_to_group(
                group_name=group_name,
                payload=payload,
                report_email=getattr(request.user, "email", None),
            )
            if not sent:
                m = (
                    "No se pudo enviar la notificación masiva. "
                    "Revisa el grupo o las suscripciones Web Push."
                )
                messages.error(request, m, fail_silently=True)
                return error_json(mensaje=m)
            return _success_recarga(
                request,
                "Notificación Web Push masiva enviada correctamente. "
                "La recibirán los dispositivos suscritos (según cola o envío inmediato).",
            )
        else:
            return error_json(mensaje=str(form.errors))

    def post_notificaciones_aviso_masivo(self, request, context, *args, **kwargs):
        """
        Crea un AvisoMasivo (aparece en el icono de campana del sitio) y,
        si se indica, envía el mismo título/mensaje como Web Push masivo.
        """
        form = AvisoMasivoEnviarForm(request.POST)
        if not form.is_valid():
            return error_json(mensaje=str(form.errors))
        d = form.cleaned_data
        publicado = d.get("publicado_en") or timezone.now()
        if publicado and timezone.is_naive(publicado):
            publicado = timezone.make_aware(
                publicado, timezone.get_current_timezone()
            )
        vigente = d.get("vigente_hasta")
        if vigente and timezone.is_naive(vigente):
            vigente = timezone.make_aware(
                vigente, timezone.get_current_timezone()
            )
        aviso = AvisoMasivo(
            titulo=d["titulo"],
            mensaje=(d.get("mensaje") or "").strip(),
            url=(d.get("url") or "").strip(),
            activo=True,
            publicado_en=publicado,
            vigente_hasta=vigente,
            created_by=request.user,
            modified_by=request.user,
        )
        aviso.save()
        if d.get("omitir_webpush"):
            return _success_recarga(
                request,
                "Aviso masivo publicado correctamente (solo en el sitio). "
                "Los usuarios lo verán en su campanita de notificaciones.",
            )
        application = AplicacionWeb.objects.first()
        logo_url = application.logo.url if application and application.logo else ""
        group_name = (
            application.group_name_webpush
            if application and application.group_name_webpush
            else "Main"
        )
        URL_BASE = settings.URL_BASE
        body_push = d["titulo"] if not (d.get("mensaje") or "").strip() else (d.get("mensaje") or "").strip()
        payload = {
            "head": d["titulo"][:100],
            "body": (body_push or d["titulo"])[:200],
            "icon": f"{URL_BASE}{logo_url}" if logo_url else "",
            "url": (d.get("url") or "").strip() or "/",
        }
        sent = send_notification_to_group(
            group_name=group_name,
            payload=payload,
            report_email=getattr(request.user, "email", None),
        )
        if not sent:
            m = (
                "El aviso masivo se guardó en el sitio, pero el Web Push no pudo enviarse. "
                "Revisa el grupo o las suscripciones."
            )
            messages.warning(request, m, fail_silently=True)
            return error_json(mensaje=m)
        return _success_recarga(
            request,
            "Aviso masivo publicado correctamente en el sitio y notificación Web Push masiva "
            "enviada correctamente a los suscriptores de navegador.",
        )

    def get(self, request, *args, **kwargs):
        self.data = request.POST
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        return render(request, 'core/administracion/notificaciones/pushapp.html', context)

    def get_notificaciones_android_masiva(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación a todos los usuarios'
        context['message'] = 'Se enviará una notificación a todos los usuarios'
        context['form'] = NotificacionAndroidMasivaForm()
        return render(request, 'core/modals/formModal.html', context)
    
    def get_notificaciones_push_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación push a un usuario'
        context['message'] = 'Se enviará una notificación push al usuario seleccionado'
        context['form'] = NotificacionPushUsuarioForm()
        return render(request, 'core/modals/formModal.html', context)

    def get_notificaciones_app_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación app a un usuario'
        context['message'] = 'Se enviará una notificación app al usuario seleccionado'
        context['form'] = NotificacionAppUsuarioForm()
        return render(request, 'core/modals/formModal.html', context)
    
    def get_notificaciones_pushapp_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación pushapp a un usuario'
        context['message'] = 'Se enviará una notificación pushapp al usuario seleccionado'
        context['form'] = NotificacionPushAppUsuarioForm()
        return render(request, 'core/modals/formModal.html', context)

    def get_notificaciones_push_masiva(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación push masiva'
        context['message'] = 'Se enviará una notificación push a todos los usuarios'
        context['form'] = NotificacionPushMasivaForm()
        return render(request, 'core/modals/formModal.html', context)

    def get_notificaciones_aviso_masivo(self, request, context, *args, **kwargs):
        context['title'] = 'Publicar aviso masivo (sitio y opcional Web Push)'
        context['message'] = (
            'Se creará un aviso de campaña: los usuarios lo verán en el icono de notificaciones '
            "sin duplicar filas por usuario. Puedes combinar con Web Push al navegador."
        )
        context['form'] = AvisoMasivoEnviarForm()
        return render(request, 'core/modals/formModal.html', context)
