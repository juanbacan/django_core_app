from django.shortcuts import render
from core.views import ViewAdministracionBase
from core.administracion_forms import GrupoForm
from django.contrib.auth.models import Group

from core.utils import error_json, success_json, get_redirect_url

class GroupsView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")
    
    def post_add(self, request, context, *args, **kwargs):
        form = GrupoForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def post_edit(self, request, context, *args, **kwargs):
        form = GrupoForm(request.POST, instance=Group.objects.get(pk=self.data.get('id')))
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        context['objects'] = Group.objects.order_by('id')
        return render(request, 'core/administracion/grupos/lista.html', context)

    def get_add(self, request, context, *args, **kwargs):
        context['form'] = GrupoForm()
        return render(request, 'core/forms/formAdmin.html', context)
        
    def get_edit(self, request, context, *args, **kwargs):
        context['object'] = modulo = Group.objects.get(pk=self.data.get('id'))
        context['form'] = GrupoForm(instance=modulo)
        return render(request, 'core/forms/formAdmin.html', context)
