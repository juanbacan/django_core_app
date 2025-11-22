# Sistema de Layout para Formularios - Guía de Uso

Sistema similar a `crispy-forms` que te permite controlar completamente el layout de tus formularios Django.

## Instalación

El sistema ya está incluido en `core.layout`. Solo necesitas importarlo:

```python
from core.forms import ModelBaseForm, BaseForm
from core.layout import (
    FormHelper, Layout, Row, Column, Field, Fieldset, 
    Div, Card, HTML, Separator, Submit, ButtonGroup
)
```

## Uso Básico

### 1. Formulario Simple con Layout

```python
from core.forms import ModelBaseForm
from core.layout import FormHelper, Layout, Field

class PersonaForm(ModelBaseForm):
    class Meta:
        model = Persona
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            'nombre',
            'apellido',
            'email',
        )
```

### 2. Campos en Filas y Columnas

```python
class PersonaForm(ModelBaseForm):
    class Meta:
        model = Persona
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-6'),
                Column('apellido', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-8'),
                Column('telefono', css_class='col-md-4'),
            ),
            'direccion',
        )
```

### 3. Usando Fieldsets

```python
class PersonaForm(ModelBaseForm):
    class Meta:
        model = Persona
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                'Información Personal',
                'nombre',
                'apellido',
                'fecha_nacimiento',
            ),
            Fieldset(
                'Contacto',
                'email',
                'telefono',
                'celular',
            ),
            Fieldset(
                'Dirección',
                Row(
                    Column('calle', css_class='col-md-8'),
                    Column('numero', css_class='col-md-4'),
                ),
                Row(
                    Column('ciudad', css_class='col-md-6'),
                    Column('codigo_postal', css_class='col-md-6'),
                ),
            ),
        )
```

### 4. Posición de Labels

```python
# Label arriba del campo (por defecto)
Field('nombre', label_position='top')

# Label a la izquierda (horizontal)
Field('email', label_position='left')

# Label a la derecha (para checkboxes)
Field('activo', label_position='right')

# Sin label
Field('campo_oculto', label_position='hidden')
```

### 5. Tarjetas (Cards)

```python
self.helper.layout = Layout(
    Card(
        'Información del Usuario',
        'username',
        'email',
        'password',
        css_class='mb-4',
    ),
    Card(
        'Perfil',
        Row(
            Column('nombre', css_class='col-md-6'),
            Column('apellido', css_class='col-md-6'),
        ),
        'bio',
        css_class='mb-4',
    ),
)
```

### 6. Separadores y HTML Personalizado

```python
self.helper.layout = Layout(
    'campo1',
    'campo2',
    Separator('Sección Importante'),
    'campo3',
    'campo4',
    HTML('<hr class="my-4">'),
    HTML('<div class="alert alert-info">Información adicional</div>'),
    'campo5',
)
```

### 7. Contenedores Div

```python
self.helper.layout = Layout(
    Div(
        'nombre',
        'apellido',
        css_class='p-3 bg-light rounded',
    ),
    Div(
        Row(
            Column('email', css_class='col-md-6'),
            Column('telefono', css_class='col-md-6'),
        ),
        css_class='border p-3 mt-3',
        css_id='contacto-section',
    ),
)
```

### 8. Personalizar Campos Individuales

```python
self.helper.layout = Layout(
    Field('nombre', css_class='form-control-lg', placeholder='Ingrese su nombre'),
    Field('email', css_class='form-control-sm', readonly='readonly'),
    Field('descripcion', wrapper_class='mb-5', rows='5'),
)
```

### 9. Botones Personalizados

```python
self.helper.layout = Layout(
    'campo1',
    'campo2',
    ButtonGroup(
        Submit('Guardar', css_class='btn btn-primary'),
        Submit('Guardar y Continuar', css_class='btn btn-success', name='save_continue'),
        HTML('<a href="/" class="btn btn-secondary">Cancelar</a>'),
        css_class='d-flex gap-2 justify-content-end',
    ),
)
```

### 10. Ejemplo Completo Avanzado

```python
class ProductoForm(ModelBaseForm):
    class Meta:
        model = Producto
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Card(
                'Información Básica',
                Row(
                    Column('codigo', css_class='col-md-3'),
                    Column('nombre', css_class='col-md-9'),
                ),
                Row(
                    Column('categoria', css_class='col-md-6'),
                    Column('marca', css_class='col-md-6'),
                ),
                'descripcion',
            ),
            
            Card(
                'Precios e Inventario',
                Row(
                    Column(
                        Field('precio', css_class='form-control-lg'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Field('precio_oferta', css_class='form-control-lg'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Field('stock', css_class='form-control-lg text-center'),
                        css_class='col-md-4'
                    ),
                ),
                Row(
                    Column('iva', css_class='col-md-6'),
                    Column('unidad_medida', css_class='col-md-6'),
                ),
            ),
            
            Separator('Características Adicionales'),
            
            Row(
                Column(
                    Fieldset(
                        'Dimensiones',
                        'peso',
                        'ancho',
                        'alto',
                        'largo',
                    ),
                    css_class='col-md-6'
                ),
                Column(
                    Fieldset(
                        'Estado',
                        Field('activo', label_position='right'),
                        Field('destacado', label_position='right'),
                        Field('nuevo', label_position='right'),
                    ),
                    css_class='col-md-6'
                ),
            ),
            
            HTML('<hr class="my-4">'),
            
            Div(
                Field('imagen', wrapper_class='mb-3'),
                Field('galeria', wrapper_class='mb-3'),
                css_class='border p-4 bg-light',
            ),
            
            ButtonGroup(
                Submit('Guardar', css_class='btn btn-primary btn-lg'),
                Submit('Guardar y Nuevo', css_class='btn btn-success', name='save_new'),
                HTML('<a href="/productos/" class="btn btn-secondary">Volver</a>'),
                css_class='d-flex gap-3 justify-content-between mt-4',
            ),
        )
```

## Uso en Templates

### Opción 1: Usar el template con layout incluido

```django
{% extends 'layout/base_admin.html' %}

{% block content %}
<form method="POST">
    {% csrf_token %}
    {% include 'core/forms/formWithLayout.html' %}
    
    <button type="submit" class="btn btn-primary">Guardar</button>
</form>
{% endblock %}
```

### Opción 2: Renderizar manualmente

```django
{% extends 'layout/base_admin.html' %}

{% block content %}
<form method="POST">
    {% csrf_token %}
    
    {% if form.helper %}
        {{ form.helper.render_layout|safe }}
    {% else %}
        {{ form.as_p }}
    {% endif %}
    
    <button type="submit" class="btn btn-primary">Guardar</button>
</form>
{% endblock %}
```

## Componentes Disponibles

### Layout
Contenedor principal de todos los elementos.

### Row
Crea una fila de Bootstrap para organizar columnas.

### Column
Crea una columna dentro de una fila. Por defecto es `col-md-12`.

### Field
Representa un campo individual con opciones de personalización:
- `css_class`: clases CSS para el widget
- `wrapper_class`: clases para el contenedor
- `label_class`: clases para el label
- `label_position`: 'top', 'left', 'right', 'hidden'
- Cualquier atributo HTML adicional

### Fieldset
Agrupa campos bajo un título (legend).

### Card
Crea una tarjeta de Bootstrap con título opcional.

### Div
Contenedor div genérico para agrupar elementos.

### HTML
Inserta HTML personalizado en cualquier parte del layout.

### Separator
Crea un separador visual (hr) o con título.

### Submit
Botón de submit personalizable.

### ButtonGroup
Agrupa múltiples botones juntos.

## Consejos y Buenas Prácticas

1. **Orden de campos**: Define los campos en el orden que quieras mostrarlos en el layout.

2. **Responsive**: Usa las clases de columna de Bootstrap (`col-md-6`, `col-lg-4`, etc.) para hacer responsive.

3. **Reutilización**: Puedes crear layouts comunes y reutilizarlos en diferentes formularios.

4. **Combinación**: Puedes mezclar el sistema de layout con los templates tradicionales.

5. **Campos calculados**: Si tienes campos que no están en el formulario pero quieres mostrar HTML, usa `HTML()`.

6. **Validación**: Los errores de validación se muestran automáticamente debajo de cada campo.

## Migración desde el Sistema Anterior

Si tenías:
```python
fieldsets = [
    ('Título', {'fields': ['campo1', 'campo2']}),
]
```

Ahora usa:
```python
self.helper = FormHelper(self)
self.helper.layout = Layout(
    Fieldset('Título', 'campo1', 'campo2'),
)
```

## Compatibilidad

Este sistema es totalmente compatible con:
- BootstrapFieldsMixin
- Inline formsets
- Los widgets personalizados (IconPickerWidget, DropifyWidget, etc.)
- Los templates anteriores (puedes usar ambos sistemas)
