from django.shortcuts import render
from django.template.loader import render_to_string

from core.models import CorreoTemplate
from core.views import ViewAdministracionBase
from core.administracion_forms import CorreoUsuarioForm, CorreoTemplateForm, \
    CorreoTemplateEnviarForm, CorreoPersonalizadoForm, CorreoMasivoForm

from core.utils import success_json, bad_json
from core.correos import send_email_thread


class NotificacionesCorreoView(ViewAdministracionBase):

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        
        return bad_json(mensaje="Acción no permitida")

    def post_notificaciones_correo_usuario(self, request, context, *args, **kwargs):
        form = CorreoUsuarioForm(request.POST)
        if form.is_valid():
            context['title'] = form.cleaned_data['title']
            context['message'] = form.cleaned_data['message']
            context['button_text'] = form.cleaned_data['button_text']
            context['button_url'] = form.cleaned_data['button_url']
            template = render_to_string('correo/base_correo.html', context)
            send_email_thread(
                subject="Prueba de Envio de Correos", 
                body=template, 
                to=form.cleaned_data['usuario'].mi_email()
            )
            return success_json(mensaje="Correo enviado correctamente")
        else:
            return bad_json(mensaje=str(form.errors))
        
    def post_notificaciones_correo_masivo(self, request, context, *args, **kwargs):
        form = CorreoUsuarioForm(request.POST)
        if form.is_valid():
            context['title'] = form.cleaned_data['title']
            context['message'] = form.cleaned_data['message']
            context['button_text'] = form.cleaned_data['button_text']
            context['button_url'] = form.cleaned_data['button_url']
            template = render_to_string('correo/base_correo.html', context)
            # send_email_thread(
            #     subject="Prueba de Envio de Correos", 
            #     body=template, 
            #     to=form.cleaned_data['usuario'].mi_email()
            # )
            return success_json(mensaje="Correo enviado correctamente")
        else:
            return bad_json(mensaje=str(form.errors))

    def post_notificaciones_correo_template_crear(self, request, context, *args, **kwargs):
        form = CorreoTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(mensaje="Template creado correctamente", url = request.META.get('HTTP_REFERER'))
        else:
            return bad_json(mensaje=str(form.errors))


    def post_notificaciones_correo_template_editar(self, request, context, *args, **kwargs):
        template = CorreoTemplate.objects.get(id=self.data.get('id'))
        form = CorreoTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            return success_json(mensaje="Template editado correctamente", url = request.META.get('HTTP_REFERER'))
        else:
            return bad_json(mensaje=str(form.errors))

    def post_notificaciones_correo_template_eliminar(self, request, context, *args, **kwargs):
        template = CorreoTemplate.objects.get(id=self.data.get('id'))
        template.delete()
        return success_json(mensaje="Template eliminado correctamente", url = request.META.get('HTTP_REFERER'))

    def post_notificaciones_correo_template_enviar(self, request, context, *args, **kwargs):
        form = CorreoTemplateEnviarForm(request.POST)
        if form.is_valid():
            template = CorreoTemplate.objects.get(id=self.data.get('id'))
            context={}
            context['title'] = template.nombre
            context['message'] = template.html
            context['button_text'] = template.button_text
            context['button_url'] = template.button_url
            template_html = render_to_string('correo/base_correo.html', context)

            if form.cleaned_data['masivo']:
                print("TODO!!!!!")
            else:
                correo = form.cleaned_data['correo']
                usuario = form.cleaned_data['usuario']

                if not correo and not usuario:
                    return bad_json(mensaje="No se ha enviado el correo ni el usuario")

                if correo:
                    send_email_thread(
                        subject= template.subject,
                        body=template_html, 
                        to=correo
                    )

                elif usuario:
                    send_email_thread(
                        subject= template.subject,
                        body=template_html, 
                        to=usuario.mi_email()
                    )

            return success_json(mensaje="Correo enviado correctamente")
        else:
            return bad_json(mensaje=str(form.errors))


    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        templates = CorreoTemplate.objects.all()
        context['correos'] = templates.filter(tipo='correos')
        context['inscripciones'] = templates.filter(tipo='inscripciones')
        context['premium'] = templates.filter(tipo='premium')
        return render(request, 'administracion/notificaciones/correos.html', context)
        

    def get_notificaciones_correo_personalizado(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar correo personalizado'
        context['message'] = 'Se enviará un email a este correo'
        context['form'] = CorreoPersonalizadoForm()
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_correo_usuario(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar correo a un usuario'
        context['message'] = 'Se enviará un email al usuario seleccionado'
        context['form'] = CorreoUsuarioForm()
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_correo_masivo(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar correo a masivo'
        context['message'] = 'Se enviará un email a todos los usuarios activos'
        context['form'] = CorreoMasivoForm()
        return render(request, 'modals/formModal.html', context)
    0
    def get_notificaciones_correo_template_editar(self, request, context, *args, **kwargs):
        template = CorreoTemplate.objects.get(id=self.data.get('id'))
        context['title'] = 'Editar Template'
        context['form'] = CorreoTemplateForm(instance=template)
        context['formid'] = template.id
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_correo_template_crear(self, request, context, *args, **kwargs):
        context['title'] = 'Crear Template'
        form =  CorreoTemplateForm()
        tipo = self.data.get('tipo', 'correos')
        form.add_form(tipo)
        context['form'] = form
        return render(request, 'modals/formModal.html', context)
    
    def get_notificaciones_correo_template_eliminar(self, request, context, *args, **kwargs):
        template = CorreoTemplate.objects.get(id=self.data.get('id'))
        context['title'] = 'Eliminar Template'
        context['message'] = '¿Está seguro de que desea eliminar el template ' + template.nombre + '?'
        context['formid'] = template.id
        return render(request, 'modals/formModal.html', context)

    def get_notificaciones_correo_template_ver(self, request, context, *args, **kwargs):
        context['usuario'] = request.user
        html = CorreoTemplate.objects.get(id=self.data.get('id')).html
        context['message'] = html
        context['title'] = 'Ver Template'
        template = render_to_string('correo/base_correo.html', context)
        context['body'] = template
        return render(request, 'modals/modal.html', context)

    def get_notificaciones_correo_template_enviar(self, request, context, *args, **kwargs):
        context['title'] = 'Enviar Template'
        template = CorreoTemplate.objects.get(id=self.data.get('id'))
        context['formid'] = template.id
        context['form'] = CorreoTemplateEnviarForm()
        return render(request, 'administracion/notificaciones/correo_template_enviar.html', context)
                    