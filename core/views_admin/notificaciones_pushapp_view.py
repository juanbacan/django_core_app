from django.shortcuts import render

from django.conf import settings

from core.models import CustomUser, AplicacionWeb
from core.views_admin import ViewAdministracionBase
from administracion_forms import NotificacionPushUsuarioForm, NotificacionAppUsuarioForm, \
    NotificacionPushAppUsuarioForm, NotificacionPushMasivaForm, NotificacionAndroidMasivaForm

from core.utils import success_json, bad_json
from core.notificaciones import send_notification_to_group, send_notification_to_user
from core.notificaciones  import notify_user, notify_push_app_user

class NotificacionesPushAppView(ViewAdministracionBase):

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        
        return bad_json(mensaje="Acción no permitida")
    
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
            return success_json(mensaje="Notificación enviada correctamente")
        else:
            return bad_json(mensaje=str(form.errors))
        
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
            return success_json(mensaje="Notificación enviada correctamente")
        else:
            return bad_json(mensaje=str(form.errors))
        
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
            return success_json(mensaje="Notificación enviada correctamente")

    def post_notificaciones_push_masiva(self, request, context, *args, **kwargs):
        logo_url = AplicacionWeb.objects.first().logo.url
        form = NotificacionPushMasivaForm(request.POST)
        if form.is_valid():
            URL_BASE = settings.URL_BASE
            payload = {
                "head": form.cleaned_data['head'], 
                "body": form.cleaned_data['body'],
                'icon': f"{URL_BASE}{logo_url}",
                'url': form.cleaned_data['url'],
            }
            send_notification_to_group(group_name="precavidos", payload=payload) 
            return success_json(mensaje="Notificación enviada correctamente")
        else:
            return bad_json(mensaje=str(form.errors))
        

    def get(self, request, *args, **kwargs):
        self.data = request.POST
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        return render(request, 'administracion/notificaciones/pushapp.html', context)

    def get_notificaciones_android_masiva(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación a todos los usuarios'
        context['message'] = 'Se enviará una notificación a todos los usuarios'
        context['form'] = NotificacionAndroidMasivaForm()
        return render(request, 'modals/formModal.html', context)
    
    def get_notificaciones_push_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación push a un usuario'
        context['message'] = 'Se enviará una notificación push al usuario seleccionado'
        context['form'] = NotificacionPushUsuarioForm()
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_app_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación app a un usuario'
        context['message'] = 'Se enviará una notificación app al usuario seleccionado'
        context['form'] = NotificacionAppUsuarioForm()
        return render(request, 'modals/formModal.html', context)
    
    def get_notificaciones_pushapp_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación pushapp a un usuario'
        context['message'] = 'Se enviará una notificación pushapp al usuario seleccionado'
        context['form'] = NotificacionPushAppUsuarioForm()
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_push_masiva(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar notificación push masiva'
        context['message'] = 'Se enviará una notificación push a todos los usuarios'
        context['form'] = NotificacionPushMasivaForm()
        return render(request, 'modals/formModal.html', context)
