from django.shortcuts import render
from core.views_admin import ViewAdministracionBase
from administracion_forms import *

class PanelView(ViewAdministracionBase):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, 'administracion/administracion.html', context)

