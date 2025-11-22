# 💡 Tips y Mejores Prácticas - Sistema de Layout

## 🎯 Patrones Comunes

### 1. Formulario de Registro/Login
```python
self.helper = FormHelper(self)
self.helper.layout = Layout(
    Card(
        'Crear Cuenta',
        'username',
        'email',
        Row(
            Column('password', css_class='col-md-6'),
            Column('password_confirm', css_class='col-md-6'),
        ),
        Field('acepto_terminos', label_position='right'),
        css_class='mx-auto',
        body_class='p-4',
    ),
    ButtonGroup(
        Submit('Registrarse', css_class='btn btn-primary btn-block'),
        HTML('<a href="/login/" class="btn btn-link">¿Ya tienes cuenta?</a>'),
        css_class='d-grid gap-2',
    ),
)
```

### 2. Formulario de Búsqueda (Filters)
```python
self.helper = FormHelper(self)
self.helper.layout = Layout(
    Row(
        Column('buscar', css_class='col-md-4'),
        Column('categoria', css_class='col-md-3'),
        Column('fecha_desde', css_class='col-md-2'),
        Column('fecha_hasta', css_class='col-md-2'),
        Column(
            Submit('Buscar', css_class='btn btn-primary w-100'),
            css_class='col-md-1 d-flex align-items-end',
        ),
    ),
)
```

### 3. Formulario Wizard (Multi-paso)
```python
# Paso 1
self.helper.layout = Layout(
    HTML('<div class="progress mb-4"><div class="progress-bar" style="width: 33%">Paso 1 de 3</div></div>'),
    Fieldset('Información Personal', 'nombre', 'apellido', 'email'),
    ButtonGroup(
        Submit('Siguiente', css_class='btn btn-primary'),
        css_class='justify-content-end',
    ),
)
```

### 4. Formulario de Perfil
```python
self.helper = FormHelper(self)
self.helper.layout = Layout(
    Row(
        Column(
            Div(
                HTML('<div class="text-center mb-3"><img src="avatar.jpg" class="rounded-circle" width="150"></div>'),
                'foto',
                css_class='border p-4 text-center',
            ),
            css_class='col-md-4',
        ),
        Column(
            Fieldset(
                'Datos Personales',
                'nombre',
                'apellido',
                'bio',
            ),
            Fieldset(
                'Contacto',
                'email',
                'telefono',
            ),
            css_class='col-md-8',
        ),
    ),
)
```

## 🎨 Estilos y Clases CSS Útiles

### Tamaños de Campos
```python
Field('nombre', css_class='form-control-lg')      # Grande
Field('email', css_class='form-control-sm')       # Pequeño
Field('precio', css_class='form-control text-end') # Alineado derecha
```

### Colores y Estados
```python
Field('error', css_class='is-invalid')
Field('success', css_class='is-valid')
Field('readonly', css_class='form-control-plaintext', readonly='readonly')
```

### Espaciado
```python
Field('campo', wrapper_class='mb-5')  # Más margen abajo
Field('campo', wrapper_class='mt-4')  # Margen arriba
```

## 📱 Responsive Design

### Diferentes tamaños según pantalla
```python
Column('campo', css_class='col-12 col-md-6 col-lg-4')
# Móvil: 100% ancho
# Tablet: 50% ancho
# Desktop: 33% ancho
```

### Ocultar en diferentes dispositivos
```python
HTML('<div class="d-none d-md-block">Solo visible en tablet+</div>')
HTML('<div class="d-md-none">Solo visible en móvil</div>')
```

## ⚡ Performance

### 1. No renderizar campos no necesarios
```python
if self.request.user.is_staff:
    self.helper.layout.append('campo_admin')
```

### 2. Lazy loading de opciones
```python
# En lugar de cargar todas las opciones
# Usa autocomplete para campos con muchas opciones
```

## 🔒 Seguridad

### Campos readonly basados en permisos
```python
if not self.request.user.is_superuser:
    self.fields['precio'].widget.attrs['readonly'] = True
```

### Ocultar campos sensibles
```python
if not self.request.user.has_perm('ver_campo_secreto'):
    self.helper.layout.fields = [
        f for f in self.helper.layout.fields 
        if not isinstance(f, Field) or f.field_name != 'campo_secreto'
    ]
```

## 🎭 UX Mejorado

### 1. Agregar íconos a labels
```python
Field('email', label_class='d-flex align-items-center gap-2'),
HTML('<i class="fas fa-envelope"></i>'),
```

### 2. Placeholders útiles
```python
Field('telefono', placeholder='Ej: 0987654321')
Field('email', placeholder='usuario@ejemplo.com')
```

### 3. Mensajes de ayuda contextuales
```python
HTML('<div class="alert alert-info"><i class="fas fa-lightbulb"></i> Tip: Tu contraseña debe tener al menos 8 caracteres</div>')
```

### 4. Campos dependientes con JavaScript
```python
Div(
    'pais',
    Field('provincia', css_id='provincia-field', style='display: none;'),
    css_id='direccion-container',
)
# Luego en JS mostrar/ocultar según selección
```

## 🧩 Reutilización

### Crear componentes reutilizables
```python
# En un archivo common_layouts.py
def direccion_fieldset():
    return Fieldset(
        'Dirección',
        Row(
            Column('calle', css_class='col-md-8'),
            Column('numero', css_class='col-md-4'),
        ),
        Row(
            Column('ciudad', css_class='col-md-6'),
            Column('codigo_postal', css_class='col-md-6'),
        ),
    )

# Luego usar en múltiples formularios
self.helper.layout = Layout(
    'nombre',
    'email',
    direccion_fieldset(),
)
```

### Layouts base para heredar
```python
class FormularioBasePersona(ModelBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = self.get_base_layout()
    
    def get_base_layout(self):
        return Layout(
            Row(
                Column('nombre', css_class='col-md-6'),
                Column('apellido', css_class='col-md-6'),
            ),
            'email',
        )

class FormularioCliente(FormularioBasePersona):
    def get_base_layout(self):
        layout = super().get_base_layout()
        layout.fields.append(Fieldset('Datos de Cliente', 'empresa', 'ruc'))
        return layout
```

## 🐛 Debugging

### Ver estructura del layout
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper(self)
    self.helper.layout = Layout(...)
    
    # En desarrollo, imprimir estructura
    if settings.DEBUG:
        print("Layout fields:", [
            f.field_name if isinstance(f, Field) else type(f).__name__ 
            for f in self.helper.layout.fields
        ])
```

## 🎨 Temas Personalizados

### Cambiar colores de cards
```python
Card(
    'Información Importante',
    '...',
    header_class='bg-danger text-white',
    body_class='bg-light',
)
```

### Agregar clases custom
```python
Fieldset(
    'Título',
    '...',
    css_class='custom-fieldset shadow-sm rounded p-4',
    legend_class='fw-bold text-primary',
)
```

## 📊 Formularios con datos complejos

### Mostrar datos relacionados
```python
HTML(f'<div class="alert alert-secondary">Editando: {self.instance.nombre}</div>')
```

### Campos calculados
```python
if self.instance.pk:
    subtotal = self.instance.calcular_subtotal()
    HTML(f'<div class="fs-4 fw-bold">Subtotal: ${subtotal}</div>')
```

## 🔄 AJAX y actualizaciones dinámicas

```python
# Campo que dispara actualización
Field('categoria', css_id='id_categoria', 
      onchange='actualizarSubcategorias(this.value)')

# Contenedor que se actualiza
Div(
    'subcategoria',
    css_id='subcategoria-container',
)
```

## ✅ Validación visual mejorada

```python
self.helper.layout = Layout(
    HTML('<div id="validation-summary" class="alert alert-danger d-none"></div>'),
    '...',
)
# Luego con JS mostrar errores en el summary
```
