# 🎨 Sistema de Layout para Formularios

Sistema similar a **crispy-forms** para Django que te permite controlar completamente el diseño de tus formularios.

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

```django
<form method="POST">
    {% csrf_token %}
    {% include 'core/forms/formWithLayout.html' %}
    <button type="submit" class="btn btn-primary">Guardar</button>
</form>
```

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
