from django.shortcuts import render
from django.conf import settings

from core.views import ViewAdministracionBase
from core.administracion_forms import MensajeUsuarioForm
from core.utils import error_json, success_json, get_redirect_url
from core.whatsapp import send_whatsapp_message, WhatsappBot


class WhatsappBotAdminView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")
        
    def post_enviar_mensaje_usuario(self, request, context, *args, **kwargs):
        form = MensajeUsuarioForm(request.POST)
        if form.is_valid():
            mensaje = form.cleaned_data.get('mensaje').strip()
            numero = form.cleaned_data.get('numero').strip()
            ok = send_whatsapp_message(numero, mensaje)
            if not ok:
                return error_json(mensaje="Error al enviar el mensaje")
            return success_json()
        return error_json(mensaje="Error al enviar el mensaje", errors=form.errors)
    
    def post_desconectar(self, request, context, *args, **kwargs):
        whatsappbot = WhatsappBot()
        whatsappbot.disconnect()
        return success_json(url=get_redirect_url(request))
        
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        whatsappbot = WhatsappBot()
        context['status'] = status = whatsappbot.get_status()

        if not status:
            whatsappbot.create_session()
            context['qr'] = whatsappbot.get_qr_code()

        return render(request, 'core/administracion/whatsapp/whatsapp_admin.html', context)
    
    def get_enviar_mensaje_usuario(self, request, context, *args, **kwargs):
        context['form'] = MensajeUsuarioForm()
        context['title'] = "Enviar mensaje a usuarios"
        return render(request, 'core/modals/formModal.html', context)
    
    def get_desconectar(self, request, context, *args, **kwargs):
        context['title'] = "Desconectar WhatsApp"
        context['message'] = "¿Está seguro que desea desconectar WhatsApp?"
        context['delete_object'] = True
        return render(request, 'core/modals/formModal.html', context)