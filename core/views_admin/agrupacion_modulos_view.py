from django.shortcuts import render
from core.models import AgrupacionModulo
from core.views import ViewAdministracionBase
from administracion_forms import AgrupacionModuloForm

from core.utils import error_json, success_json, get_redirect_url

class AgrupacionModulosView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")
    
    def post_add(self, request, context, *args, **kwargs):
        form = AgrupacionModuloForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def post_edit(self, request, context, *args, **kwargs):
        form = AgrupacionModuloForm(request.POST, instance=AgrupacionModulo.objects.get(pk=self.data.get('id')))
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        context['objects'] = AgrupacionModulo.objects.order_by('orden', 'id')
        return render(request, 'administracion/agrupacion_modulos/lista.html', context)

    def get_add(self, request, context, *args, **kwargs):
        context['form'] = AgrupacionModuloForm()
        return render(request, 'forms/formAdmin.html', context)
        
    def get_edit(self, request, context, *args, **kwargs):
        context['object'] = modulo = AgrupacionModulo.objects.get(pk=self.data.get('id'))
        context['form'] = AgrupacionModuloForm(instance=modulo)
        return render(request, 'forms/formAdmin.html', context)
