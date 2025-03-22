from django.shortcuts import render
from core.models import Modulo
from core.views import ViewAdministracionBase
from core.administracion_forms import ModuloForm

from core.utils import error_json, success_json, get_redirect_url

class ModulosView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")
    
    def post_add(self, request, context, *args, **kwargs):
        form = ModuloForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def post_edit(self, request, context, *args, **kwargs):
        form = ModuloForm(request.POST, instance=Modulo.objects.get(pk=self.data.get('id')))
        if form.is_valid():
            form.save()
            return success_json(url = get_redirect_url(request))
        return error_json(mensaje="Error al guardar el modulo", errors=form.errors)
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        context['objects'] = Modulo.objects.order_by('orden', 'id')
        return render(request, 'administracion/modulos/lista.html', context)

    def get_add(self, request, context, *args, **kwargs):
        context['form'] = ModuloForm()
        return render(request, 'forms/formAdmin.html', context)
        
    def get_edit(self, request, context, *args, **kwargs):
        context['object'] = modulo = Modulo.objects.get(pk=self.data.get('id'))
        context['form'] = ModuloForm(instance=modulo)
        return render(request, 'forms/formAdmin.html', context)
