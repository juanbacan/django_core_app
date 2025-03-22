from dal import autocomplete, forward
from tinymce.widgets import TinyMCE

from django import forms
from django.contrib.auth.models import Group

from core.forms import BaseForm, ModelBaseForm
from core.models import CustomUser, CorreoTemplate, AplicacionWeb, Modulo, AgrupacionModulo, TipoNotificacion


TINYMCE_DEFAULT_CONFIG2 = {
    "theme": "silver",
    "height": 200,
    "menubar": False,
    "plugins": "preview,advlist,lists,link,charmap,image,media,table,paste,wordcount, code",
    "external_plugins": {
        "tiny_mce_wiris": 'https://www.wiris.net/demo/plugins/tiny_mce/plugin.min.js',                  
    },
    "toolbar": "image code forecolor formatselect | "
    "bold italic | alignleft aligncenter "
    "| bullist numlist | "
    "tiny_mce_wiris_formulaEditor tiny_mce_wiris_formulaEditorChemistry "
    "table superscript subscript charmap preview",
    "images_upload_url": "/upload_image/",
    #"paste_as_text": True,
}


class AplicacionWebForm(ModelBaseForm):
    class Meta:
        model = AplicacionWeb
        fields = '__all__'
        # exclude = []
        labels = {
            'descripcion': 'Descripción',
        }
        widgets = {
            'meta_description': forms.Textarea(attrs={'rows': 2}),
        }
    
# *****************************************************************************************************
# Usuarios
# *****************************************************************************************************
class CustomUserForm(ModelBaseForm):
    class Meta:
        model = CustomUser
        fields = '__all__'
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'is_active': 'Activo',
            'is_staff': 'Staff',
            'is_superuser': 'Super Usuario',
            'groups': 'Grupos',
            'user_permissions': 'Permisos',
            'password': 'Contraseña',
        }
        widgets = {
            'groups': autocomplete.ModelSelect2Multiple(),
            'user_permissions': forms.SelectMultiple(attrs={'size': 10}),
        }

    def clean_username(self):
        if self.instance and self.instance.pk:
            return self.cleaned_data['username']
        if CustomUser.objects.filter(username=self.cleaned_data['username']).exists():
            raise forms.ValidationError('El nombre de usuario ya existe')
        
    def clean_email(self):
        if self.instance and self.instance.pk:
            return self.cleaned_data['email']
        if CustomUser.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError('El correo electrónico ya existe')
        return self.cleaned_data['email']
    
    def clean_password(self):
        if self.instance and self.instance.pk:
            return self.cleaned_data['password']
        if not self.cleaned_data['password']:
            raise forms.ValidationError('Este campo es requerido')
        return self.cleaned_data['password']
    

# *****************************************************************************************************
# Sección Notificaciones
# *****************************************************************************************************
class TipoNotificacionForm(ModelBaseForm):
    class Meta:
        model = TipoNotificacion
        fields = '__all__'


class CorreoPersonalizadoForm(BaseForm):
    correo = forms.EmailField(max_length=100, label='Correo Electrónico')
    title = forms.CharField(max_length=500, label='Título')
    message = forms.CharField(required=True, label="Mensaje", widget=TinyMCE(mce_attrs = TINYMCE_DEFAULT_CONFIG2))
    button_text = forms.CharField(max_length=200, label='Texto del Botón')
    button_url = forms.CharField(max_length=200, label='Link del Botón')

class CorreoUsuarioForm(BaseForm):
    usuario = forms.ModelChoiceField(label="Usuario", queryset=CustomUser.objects.all(), required=True,
            widget=autocomplete.ModelSelect2(
                url='core:model_autocomplete',
                forward=(forward.Const('CustomUser', 'model'), ),
                attrs={'data-html': True},
            ))
    title = forms.CharField(max_length=500, label='Título')
    message = forms.CharField(required=True, label="Mensaje", widget=TinyMCE(mce_attrs = TINYMCE_DEFAULT_CONFIG2))
    button_text = forms.CharField(max_length=200, label='Texto del Botón')
    button_url = forms.CharField(max_length=200, label='Link del Botón')

class CorreoMasivoForm(BaseForm):
    title = forms.CharField(max_length=500, label='Título')
    message = forms.CharField(required=True, label="Mensaje", widget=TinyMCE(mce_attrs = TINYMCE_DEFAULT_CONFIG2))
    button_text = forms.CharField(max_length=200, label='Texto del Botón')
    button_url = forms.CharField(max_length=200, label='Link del Botón')


class NotificacionPushUsuarioForm(BaseForm):
    usuario = forms.ModelChoiceField(label="Usuario", queryset=CustomUser.objects.all(), required=True,
            widget=autocomplete.ModelSelect2(
                url='core:model_autocomplete',
                forward=(forward.Const('CustomUser', 'model'), ),
                attrs={'data-html': True},
            ))
    head = forms.CharField(required=True, label="Encabezado")
    body = forms.CharField(required=True, label="Cuerpo", widget=forms.Textarea(attrs={'rows': 3}))
    url = forms.CharField(required=True, label="URL")

class NotificacionAppUsuarioForm(BaseForm):
    usuario_notificado = forms.ModelChoiceField(label="Usuario", queryset=CustomUser.objects.all(), required=True,
            widget=autocomplete.ModelSelect2(
                url='core:model_autocomplete',
                forward=(forward.Const('CustomUser', 'model'), ),
                attrs={'data-html': True},
            ))
    tipo_notificacion = forms.ModelChoiceField(label="Tipo de Notificación", queryset=TipoNotificacion.objects.all(), required=True)
    mensaje = forms.CharField(required=True, label="Mensaje", widget=TinyMCE(mce_attrs = TINYMCE_DEFAULT_CONFIG2))
    url = forms.CharField(required=True, label="URL")

class NotificacionPushAppUsuarioForm(BaseForm):
    usuario_notificado = forms.ModelChoiceField(label="Usuario", queryset=CustomUser.objects.all(), required=True,
            widget=autocomplete.ModelSelect2(
                url='core:model_autocomplete',
                forward=(forward.Const('CustomUser', 'model'), ),
                attrs={'data-html': True},
            ))
    body = forms.CharField(required=True, label="Cuerpo", widget=forms.Textarea(attrs={'rows': 3}))
    url = forms.CharField(required=True, label="URL")
    tipo_notificacion = forms.ModelChoiceField(label="Tipo de Notificación", queryset=TipoNotificacion.objects.all(), required=True)


class NotificacionPushMasivaForm(BaseForm):
    head = forms.CharField(required=True, label="Encabezado")
    body = forms.CharField(required=True, label="Cuerpo", widget=forms.Textarea(attrs={'rows': 3}))
    url = forms.CharField(required=True, label="URL")


class NotificacionAndroidMasivaForm(BaseForm):
    title = forms.CharField(required=True, label="Título")
    body = forms.CharField(required=True, label="Cuerpo", widget=forms.Textarea(attrs={'rows': 3}))
    data = forms.CharField(required=True, label="Datos en JSON")

# Crear un Formulario para el modelo CorreoTemplate
class CorreoTemplateForm(ModelBaseForm):
    class Meta:
        model = CorreoTemplate
        fields = ['nombre', 'subject', 'html', 'button_text', 'button_url', 'tipo']
        labels = {
            'nombre': 'Título',
            'subject': 'Asunto',
            'html': 'HTML',
            'button_text': 'Texto del Botón',
            'button_url': 'Link del Botón',
        }
        widgets = {
            'html': TinyMCE(mce_attrs = TINYMCE_DEFAULT_CONFIG2),
            'tipo': forms.HiddenInput(),
        }

    def add_form(self, tipo):
        self.fields['tipo'].initial = tipo

class CorreoTemplateEnviarForm(BaseForm):
    masivo = forms.BooleanField(required=False, label='Enviar a todos los usuarios', 
            widget=forms.CheckboxInput(attrs={'separator': 'Si selecciona esta opción, el correo se enviará a todos los usuarios'}))
    correo = forms.EmailField(max_length=100, label='Correo Electrónico', required=False,
            widget=forms.TextInput(attrs={'placeholder': 'Correo Electrónico', 'separator': 'Ingrese solo el correo o seleccione un usuario'}))
    usuario = forms.ModelChoiceField(label="Usuario", queryset=CustomUser.objects.all(), required=False,
            widget=autocomplete.ModelSelect2(
                url='core:model_autocomplete',
                forward=(forward.Const('CustomUser', 'model'), ),
                attrs={'data-html': True},
            ))
    

# *****************************************************************************************************
# Sección Sistema
# *****************************************************************************************************
class ModuloForm(ModelBaseForm):
    class Meta:
        model = Modulo
        fields = '__all__'
        widgets = {
            'icon': forms.TextInput(attrs={'class': 'iconpicker'}),
            'url': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class AgrupacionModuloForm(ModelBaseForm):
    class Meta:
        model = AgrupacionModulo
        fields = '__all__'
        widgets = {
            'icono': forms.TextInput(attrs={'class': 'iconpicker'}),
            'url': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class GrupoForm(ModelBaseForm):
    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'permissions': forms.SelectMultiple(attrs={'size': 10}),
        }