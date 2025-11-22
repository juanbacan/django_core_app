"""
Ejemplo del formulario TareaObra con el sistema de layout automático
"""

from core.forms import ModelBaseForm
from core.layout import FormHelper, Layout, Row, Column, Card, Field
from django import forms


class TareaObraForm(ModelBaseForm):
    """Formulario para crear/editar tareas del libro de obra."""
    
    class Meta:
        model = TareaObra  # Asume que existe este modelo
        fields = ['titulo', 'descripcion', 'estado', 'fecha_inicio', 'fecha_fin', 'responsables', 'materiales']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'titulo': 'Título descriptivo de la tarea',
            'descripcion': 'Detalle las actividades a realizar',
            'estado': 'Seleccione el estado actual de la tarea',
            'fecha_inicio': 'Fecha de inicio planificada',
            'fecha_fin': 'Fecha de finalización planificada',
            'responsables': 'Mantén presionada Ctrl (Cmd en Mac) para seleccionar varios',
            'materiales': 'Mantén presionada Ctrl (Cmd en Mac) para seleccionar varios',
        }
        labels = {
            'titulo': 'Título',
            'descripcion': 'Descripción',
            'estado': 'Estado',
            'fecha_inicio': 'Fecha Inicio',
            'fecha_fin': 'Fecha Fin',
            'responsables': 'Responsables',
            'materiales': 'Materiales',
        }

    def __init__(self, *args, **kwargs):
        proyecto_id = kwargs.pop('proyecto_id', None)
        super().__init__(*args, **kwargs)
        
        # ✨ Sistema de layout - se detecta automáticamente en los templates
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Card(
                'Información General',
                Field('titulo', placeholder='Título de la tarea'),
                Field('descripcion', placeholder='Descripción detallada de la tarea'),
                Field('estado'),
                css_class='mb-4',
            ),
            Card(
                'Planificación',
                Row(
                    Column('fecha_inicio', css_class='col-md-6'),
                    Column('fecha_fin', css_class='col-md-6'),
                ),
                css_class='mb-4',
            ),
            Card(
                'Asignación de Recursos',
                Row(
                    Column('responsables', css_class='col-md-6'),
                    Column('materiales', css_class='col-md-6'),
                ),
                css_class='mb-4',
            ),
        )
        
        # Filtrar materiales solo del mismo proyecto
        if proyecto_id:
            from .models import Material, Persona
            self.fields['materiales'].queryset = Material.objects.filter(proyecto_id=proyecto_id)
            self.fields['responsables'].queryset = Persona.objects.all()
        
        # Hacer responsables y materiales opcionales
        self.fields['responsables'].required = False
        self.fields['materiales'].required = False


# ═══════════════════════════════════════════════════════════════════════
# VISTA - No necesita cambios
# ═══════════════════════════════════════════════════════════════════════

class TareaObraView(ModelCRUDView):
    model = TareaObra
    form_class = TareaObraForm
    template_form = 'core/forms/formAdmin.html'  # ← Detecta automáticamente el helper
    # ... resto de configuración


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATE - No necesita cambios
# ═══════════════════════════════════════════════════════════════════════

"""
En tu template simplemente usa:

{% extends 'layout/base_admin.html' %}

{% block content %}
    <form method="POST">
        {% csrf_token %}
        {% include 'core/forms/form.html' %}
        {# ↑ Detecta automáticamente si form tiene helper #}
        
        <button type="submit" class="btn btn-primary">Guardar</button>
    </form>
{% endblock %}

O si usas el template de admin completo:
{% extends 'core/forms/formAdmin.html' %}
{# Ya incluye todo y detecta automáticamente #}


O en un modal:
{% include 'core/modals/formModal.html' %}
{# También detecta automáticamente #}
"""


# ═══════════════════════════════════════════════════════════════════════
# RESULTADO VISUAL
# ═══════════════════════════════════════════════════════════════════════

"""
El formulario se renderiza así:

┌─────────────────────────────────────────────────────────────┐
│ Información General                                         │
├─────────────────────────────────────────────────────────────┤
│ Título:        [___________________________________]        │
│ Descripción:   [                                   ]        │
│                [                                   ]        │
│ Estado:        [▼ Seleccionar                      ]        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Planificación                                               │
├─────────────────────────────────────────────────────────────┤
│ Fecha Inicio:          Fecha Fin:                          │
│ [________]              [________]                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Asignación de Recursos                                      │
├─────────────────────────────────────────────────────────────┤
│ Responsables:          Materiales:                          │
│ [▢ Juan Pérez    ]     [▢ Cemento        ]                 │
│ [▢ María López   ]     [▢ Arena          ]                 │
│ [▢ Pedro García  ]     [▢ Ladrillos      ]                 │
└─────────────────────────────────────────────────────────────┘

              [Guardar] [Guardar y Añadir Otro]
"""
