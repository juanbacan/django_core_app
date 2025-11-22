"""
Ejemplos de uso del sistema de Layout para formularios
"""

from django import forms
from core.forms import ModelBaseForm, BaseForm
from core.layout import (
    FormHelper, Layout, Row, Column, Field, Fieldset,
    Div, Card, HTML, Separator, Submit, ButtonGroup
)


# EJEMPLO 1: Formulario básico con dos columnas
class EjemploBasicoForm(BaseForm):
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    email = forms.EmailField()
    telefono = forms.CharField(max_length=20)
    
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
        )


# EJEMPLO 2: Formulario con fieldsets
class EjemploFieldsetsForm(BaseForm):
    # Datos personales
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    fecha_nacimiento = forms.DateField()
    
    # Contacto
    email = forms.EmailField()
    telefono = forms.CharField(max_length=20)
    celular = forms.CharField(max_length=20)
    
    # Dirección
    calle = forms.CharField(max_length=200)
    numero = forms.CharField(max_length=10)
    ciudad = forms.CharField(max_length=100)
    codigo_postal = forms.CharField(max_length=10)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                'Información Personal',
                Row(
                    Column('nombre', css_class='col-md-6'),
                    Column('apellido', css_class='col-md-6'),
                ),
                'fecha_nacimiento',
            ),
            Fieldset(
                'Contacto',
                Row(
                    Column('email', css_class='col-md-12'),
                ),
                Row(
                    Column('telefono', css_class='col-md-6'),
                    Column('celular', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Dirección',
                Row(
                    Column('calle', css_class='col-md-9'),
                    Column('numero', css_class='col-md-3'),
                ),
                Row(
                    Column('ciudad', css_class='col-md-8'),
                    Column('codigo_postal', css_class='col-md-4'),
                ),
            ),
        )


# EJEMPLO 3: Formulario con cards
class EjemploCardsForm(BaseForm):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    bio = forms.CharField(widget=forms.Textarea)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Card(
                'Información de la Cuenta',
                'username',
                'email',
                'password',
                css_class='mb-4',
            ),
            Card(
                'Perfil Personal',
                Row(
                    Column('nombre', css_class='col-md-6'),
                    Column('apellido', css_class='col-md-6'),
                ),
                'bio',
                css_class='mb-4',
            ),
        )


# EJEMPLO 4: Formulario con diferentes posiciones de labels
class EjemploLabelsForm(BaseForm):
    nombre_completo = forms.CharField(max_length=200)
    email = forms.EmailField()
    acepto_terminos = forms.BooleanField(required=False)
    recibir_notificaciones = forms.BooleanField(required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            # Label arriba (por defecto)
            Field('nombre_completo', label_position='top'),
            
            # Label a la izquierda (horizontal)
            Field('email', label_position='left'),
            
            # Labels a la derecha (para checkboxes)
            Field('acepto_terminos', label_position='right'),
            Field('recibir_notificaciones', label_position='right'),
        )


# EJEMPLO 5: Formulario con HTML personalizado y separadores
class EjemploHTMLForm(BaseForm):
    campo1 = forms.CharField(max_length=100)
    campo2 = forms.CharField(max_length=100)
    campo3 = forms.CharField(max_length=100)
    campo4 = forms.CharField(max_length=100)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            HTML('<div class="alert alert-info"><i class="fas fa-info-circle"></i> Completa todos los campos requeridos</div>'),
            'campo1',
            'campo2',
            Separator('Información Adicional'),
            'campo3',
            'campo4',
            HTML('<hr class="my-4">'),
        )


# EJEMPLO 6: Formulario complejo con múltiples técnicas
class EjemploCompletoForm(BaseForm):
    # Información básica
    codigo = forms.CharField(max_length=20)
    nombre = forms.CharField(max_length=200)
    categoria = forms.ChoiceField(choices=[('1', 'Categoría 1'), ('2', 'Categoría 2')])
    marca = forms.CharField(max_length=100)
    descripcion = forms.CharField(widget=forms.Textarea)
    
    # Precios
    precio = forms.DecimalField(max_digits=10, decimal_places=2)
    precio_oferta = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    stock = forms.IntegerField()
    
    # Características
    peso = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    ancho = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    alto = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Estado
    activo = forms.BooleanField(required=False)
    destacado = forms.BooleanField(required=False)
    
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
                Field('descripcion', rows='4'),
                css_class='mb-4',
            ),
            
            Card(
                'Precios e Inventario',
                Row(
                    Column(
                        Field('precio', css_class='form-control-lg', placeholder='0.00'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Field('precio_oferta', css_class='form-control-lg', placeholder='0.00'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Field('stock', css_class='form-control-lg text-center'),
                        css_class='col-md-4'
                    ),
                ),
                css_class='mb-4',
            ),
            
            Separator('Características Adicionales'),
            
            Row(
                Column(
                    Fieldset(
                        'Dimensiones',
                        'peso',
                        'ancho',
                        'alto',
                    ),
                    css_class='col-md-6'
                ),
                Column(
                    Fieldset(
                        'Estado',
                        Field('activo', label_position='right'),
                        Field('destacado', label_position='right'),
                    ),
                    css_class='col-md-6'
                ),
            ),
            
            HTML('<hr class="my-4">'),
            
            ButtonGroup(
                Submit('Guardar', css_class='btn btn-primary btn-lg'),
                Submit('Guardar y Nuevo', css_class='btn btn-success', name='save_new'),
                HTML('<a href="/" class="btn btn-secondary">Cancelar</a>'),
                css_class='d-flex gap-3 justify-content-end',
            ),
        )


# EJEMPLO 7: Tres columnas responsive
class EjemploTresColumnasForm(BaseForm):
    campo1 = forms.CharField(max_length=100)
    campo2 = forms.CharField(max_length=100)
    campo3 = forms.CharField(max_length=100)
    campo4 = forms.CharField(max_length=100)
    campo5 = forms.CharField(max_length=100)
    campo6 = forms.CharField(max_length=100)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('campo1', css_class='col-lg-4 col-md-6'),
                Column('campo2', css_class='col-lg-4 col-md-6'),
                Column('campo3', css_class='col-lg-4 col-md-12'),
            ),
            Row(
                Column('campo4', css_class='col-lg-4 col-md-6'),
                Column('campo5', css_class='col-lg-4 col-md-6'),
                Column('campo6', css_class='col-lg-4 col-md-12'),
            ),
        )


# EJEMPLO 8: Layout con Divs personalizados
class EjemploDivsForm(BaseForm):
    titulo = forms.CharField(max_length=200)
    subtitulo = forms.CharField(max_length=200)
    contenido = forms.CharField(widget=forms.Textarea)
    autor = forms.CharField(max_length=100)
    fecha = forms.DateField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                'titulo',
                'subtitulo',
                css_class='p-4 bg-light rounded mb-3',
                css_id='seccion-titulos',
            ),
            Div(
                'contenido',
                css_class='border p-3 mb-3',
            ),
            Div(
                Row(
                    Column('autor', css_class='col-md-8'),
                    Column('fecha', css_class='col-md-4'),
                ),
                css_class='bg-white p-3 shadow-sm',
            ),
        )
