"""
Vista de ejemplo para demostrar el uso del sistema de layout
"""

from django.views.generic import FormView
from django.urls import reverse_lazy
from core.layout_examples import EjemploCompletoForm


class EjemploLayoutView(FormView):
    """
    Vista de ejemplo que muestra cómo usar el sistema de layout en un formulario.
    """
    template_name = 'core/forms/formLayoutExample.html'
    form_class = EjemploCompletoForm
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        # Procesar el formulario aquí
        # form.save() si es ModelForm
        # O hacer lo que necesites con los datos
        print("Formulario válido:", form.cleaned_data)
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Ejemplo de Formulario con Layout'
        return context
