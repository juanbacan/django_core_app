from dal import autocomplete, forward
from tinymce.widgets import TinyMCE

from django import forms
from django.contrib.auth.models import Group

from core.widgets import IconPickerWidget, DropifyWidget
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
            'logo': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
            ),
            'meta_keywords': forms.Textarea(attrs={'rows': 2}),
            'favicon': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg', 'ico'],
            ),
            'logo_horizontal': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
            ),
            'logo_horizontal_negativo': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
            ),
            'social_images': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
            ), 
            'logo_webpush': DropifyWidget(
                height=100,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
            ),
        }
    
# *****************************************************************************************************
# Usuarios
# *****************************************************************************************************
class CustomUserForm(ModelBaseForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups', 'password']
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
            'imagen': DropifyWidget(
                height=200,
                allowed_extensions=['webp', 'png', 'jpg', 'jpeg'],
                messages={
                    'default': 'Arrastra aquí tu imagen o haz clic para seleccionarla',
                    'replace': 'Arrastra aquí tu imagen o haz clic para reemplazarla',
                    'remove': 'Eliminar imagen',
                    'error': '¡Error! Formato de imagen no válido.'
                }
            ),
            'groups': autocomplete.ModelSelect2Multiple(),
            'user_permissions': forms.SelectMultiple(attrs={'size': 10}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if self.instance and self.instance.pk:
            return username
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('El nombre de usuario ya existe')
        return username  # <- importante

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance and self.instance.pk:
            return email
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('El correo electrónico ya existe')
        return email

    def clean_password(self):
        # OBLIGATORIO devolver algo siempre
        pwd = self.cleaned_data.get('password')
        if self.instance and self.instance.pk:
            # en edición puedes permitir dejarlo vacío para no cambiarlo
            return pwd
        if not pwd:
            raise forms.ValidationError('Este campo es requerido')
        return pwd
    
    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')

        if pwd:
            if not str(pwd).startswith(('pbkdf2_', 'argon2$', 'bcrypt$', 'scrypt$')):
                user.set_password(pwd)
            else:
                user.password = pwd  # asumes que pegaste un hash válido

        if commit:
            user.save()
            self.save_m2m()
        return user

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
    icon = forms.CharField(label="Icono", required=True, widget=IconPickerWidget())
    class Meta:
        model = Modulo
        fields = '__all__'
        widgets = {
            'url': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class AgrupacionModuloForm(ModelBaseForm):
    icono = forms.CharField(label="Icono", required=True, widget=IconPickerWidget())
    class Meta:
        model = AgrupacionModulo
        fields = '__all__'
        widgets = {
            'url': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class GrupoForm(ModelBaseForm):
    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'permissions': forms.SelectMultiple(attrs={'size': 10}),
        }

class MensajeUsuarioForm(BaseForm):
    numero = forms.CharField(label="Número de teléfono", required=True)
    mensaje = forms.CharField(label="Mensaje", required=True, widget=forms.Textarea(attrs={'rows': 3}))



### Ejemplo de cómo usar ModalForeignKeyWidget en un formulario
# from app.models import Libro, Autor
# from core.widgets import ModalForeignKeyWidget

# class LibroForm(ModelBaseForm):
#     autor = forms.ModelChoiceField(
#         queryset=Autor.objects.all(),
#         widget=ModalForeignKeyWidget(
#             model=Autor,
#             list_display=["nombre"],
#             search_fields=["nombre"]
#         )
#     )
#     class Meta:
#         model  = Libro
#         fields = ["titulo", "autor"]