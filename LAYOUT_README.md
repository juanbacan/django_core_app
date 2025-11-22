# 🎨 Sistema de Layout para Formularios

Sistema similar a **crispy-forms** para Django que te permite controlar completamente el diseño de tus formularios.

## ⚡ Detección Automática

**¡No necesitas cambiar tus templates!** El sistema detecta automáticamente si tu formulario usa `helper`:

```python
# Simplemente agrega helper a tu formulario
class MiFormulario(ModelBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)  # ← Esto es todo lo que necesitas
        self.helper.layout = Layout(...)
```

Los templates `formAdmin.html`, `formModal.html` y `form.html` **detectan automáticamente** el helper y renderizan con el nuevo sistema. Si no tiene helper, usan el sistema tradicional.

## ✨ Características

- ✅ **Filas y columnas** responsive con Bootstrap
- ✅ **Fieldsets** para agrupar campos
- ✅ **Cards** para secciones visuales
- ✅ **Posición de labels** configurable (arriba, izquierda, derecha, oculto)
- ✅ **HTML personalizado** en cualquier parte del formulario
- ✅ **Separadores** visuales
- ✅ **Botones** personalizables
- ✅ Compatible con todos los widgets personalizados

## 🚀 Inicio Rápido

```python
from core.forms import ModelBaseForm
from core.layout import FormHelper, Layout, Row, Column, Field

class MiFormulario(ModelBaseForm):
    class Meta:
        model = MiModelo
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-6'),
                Column('apellido', css_class='col-md-6'),
            ),
            'email',
            'telefono',
        )
```

## 📝 Ejemplos Comunes

### Dos columnas
```python
Row(
    Column('campo1', css_class='col-md-6'),
    Column('campo2', css_class='col-md-6'),
)
```

### Fieldset
```python
Fieldset(
    'Título de la Sección',
    'campo1',
    'campo2',
    'campo3',
)
```

### Card
```python
Card(
    'Información del Usuario',
    'username',
    'email',
    'password',
)
```

### Label arriba o al lado
```python
Field('nombre', label_position='top')      # Arriba (default)
Field('email', label_position='left')      # Izquierda
Field('activo', label_position='right')    # Derecha
```

### Separador
```python
Separator('Nueva Sección')
```

### HTML personalizado
```python
HTML('<div class="alert alert-info">Mensaje importante</div>')
```

## 🎯 En el Template

**¡No necesitas hacer nada especial!** Los templates detectan automáticamente si el formulario tiene `helper`:

```django
{# Funciona automáticamente con formAdmin.html #}
{% extends 'layout/base_admin.html' %}

{% block content %}
<form method="POST">
    {% csrf_token %}
    {% include 'core/forms/form.html' %}
    <button type="submit" class="btn btn-primary">Guardar</button>
</form>
{% endblock %}
```

```django
{# También funciona con formModal.html #}
{% include 'core/modals/formModal.html' %}
```

**Si el formulario tiene `helper`**, usa automáticamente el sistema de layout.  
**Si no tiene `helper`**, usa el sistema tradicional (formRender.html).

### Templates que soportan detección automática:
- ✅ `core/forms/form.html`
- ✅ `core/forms/formAdmin.html`
- ✅ `core/modals/formModal.html`
- ✅ `core/forms/formWithLayout.html`

## 📚 Componentes Disponibles

| Componente | Descripción |
|------------|-------------|
| `Layout` | Contenedor principal |
| `Row` | Fila de Bootstrap |
| `Column` | Columna dentro de una fila |
| `Field` | Campo individual personalizable |
| `Fieldset` | Agrupación con título |
| `Card` | Tarjeta de Bootstrap |
| `Div` | Contenedor div genérico |
| `HTML` | HTML personalizado |
| `Separator` | Separador visual |
| `Submit` | Botón de submit |
| `ButtonGroup` | Grupo de botones |

## 📖 Documentación Completa

Ver `LAYOUT_GUIDE.md` para ejemplos detallados y documentación completa.

Ver `core/layout_examples.py` para 8 ejemplos completos de diferentes tipos de formularios.

## 🔧 Compatibilidad

✅ BootstrapFieldsMixin  
✅ Inline formsets  
✅ Widgets personalizados (IconPicker, Dropify, etc.)  
✅ Templates anteriores  
✅ Sistema de fieldsets antiguo
