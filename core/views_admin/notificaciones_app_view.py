from django.shortcuts import render
from core.models import TipoNotificacion, NotificacionUsuario
from core.views_admin import ViewAdministracionBase
from administracion_forms import TipoNotificacionForm

from core.utils import error_json, success_json, get_redirect_url

class NotificacionesAppView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")
    
    def post_add(self, request, context, *args, **kwargs):
        form = TipoNotificacionForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def post_edit(self, request, context, *args, **kwargs):
        form = TipoNotificacionForm(request.POST, instance=TipoNotificacion.objects.get(pk=self.data.get('id')))
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def post_delete(self, request, context, *args, **kwargs):
        tipo = TipoNotificacion.objects.get(id=request.POST.get('id'))
        notificaciones = NotificacionUsuario.objects.filter(tipo=tipo)
        if notificaciones:
            return error_json(mensaje="No se puede eliminar el tipo de notificación, hay notificaciones asociadas")
        tipo.delete()
        return success_json(url=get_redirect_url(request))
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        context['objects'] = TipoNotificacion.objects.order_by('id')
        return render(request, 'administracion/notificaciones/notificaciones_app.html', context)

    def get_add(self, request, context, *args, **kwargs):
        context['form'] = TipoNotificacionForm()
        return render(request, 'forms/formAdmin.html', context)
        
    def get_edit(self, request, context, *args, **kwargs):
        context['object'] = tipo = TipoNotificacion.objects.get(pk=self.data.get('id'))
        context['form'] = TipoNotificacionForm(instance=tipo)
        return render(request, 'forms/formAdmin.html', context)
    
    def get_delete(self, request, context, *args, **kwargs):
        id = self.data.get('id', None)
        tipo = TipoNotificacion.objects.get(id=id)
        context['title'] = "Eliminar módulo"
        context['message'] = "¿Esta seguro de que desea eliminar el tipo de notificacion: " + tipo.titulo + "?"
        context['formid'] = tipo.id 
        context['delete_obj'] = True
        return render(request, 'modals/formModal.html', context)
