from django.views.generic import View
from django.contrib import messages
from django.shortcuts import render, redirect
from core.utils import success_json, error_json

from core.models import AplicacionWeb
from core.views import ViewAdministracionBase
from core.administracion_forms import AplicacionWebForm

class ParametrosAppView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        aplicacionweb = AplicacionWeb.objects.get_or_create(id=1)[0]
        form = AplicacionWebForm(request.POST, request.FILES, instance=aplicacionweb)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos guardados correctamente")
            return success_json(url=request.path)
        else:
            return error_json(foms=[form])

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        aplicacionweb = AplicacionWeb.objects.get_or_create(id=1)[0]
        context['form'] = AplicacionWebForm(instance=aplicacionweb)
        return render(request, 'administracion/aplicacion/parametros_app.html', context)
    
        
