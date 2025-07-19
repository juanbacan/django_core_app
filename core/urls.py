from django.urls import include, path
from .views import *
from .views_admin import *

app_name = 'core'

urlpatterns = [
    path('loginModal/', LoginModalView.as_view(), name='loginModal'),
    path('model_autocomplete/', ModelAutocompleteView.as_view(), name='model_autocomplete'),
    path('api/', api, name='api_administracion'), 
    path('upload_image/', upload_image, name='upload_image'),
    path('custom_user_autocomplete/', CustomUserAutocompleteView.as_view(), name='custom_user_autocomplete'),
    path(
        "fk-lookup/<str:model_label>/",
        ModalForeignKeyLookupView.as_view(),
        name="modal-fk-lookup"
    ),
]


sistema_urls = (
    {
        "nombre": "Parámetros del Sitio",
        "url": 'parametros_sitio/',
        "vista": ParametrosAppView.as_view(),
        "namespace": 'admin_parametros_sitio',
    },
    {
        "nombre": "Usuarios",
        "url": 'usuarios/',
        "vista": UsuariosView.as_view(),
        "namespace": 'admin_usuarios',
    },
    {
        "nombre": "Modulos",
        "url": 'modulos/',
        "vista": ModulosView.as_view(),
        "namespace": 'admin_modulos',
    },
    {
        "nombre": "Módulos de un Grupo",
        "url": 'grupo-modulos/',
        "vista": GrupoModulosView.as_view(),
        "namespace": 'admin_grupo_modulos',
    },
    {
        "nombre": "Agrupacion Modulos",
        "url": 'agrupacion-modulos/',
        "vista": AgrupacionModulosView.as_view(),
        "namespace": 'admin_agrupacion_modulos',
    },
    {
        "nombre": "Grupos",
        "url": 'grupos/',
        "vista": GroupsView.as_view(),
        "namespace": 'admin_grupos',
    }, 
    {
        "nombre": "Credenciales de Correo",
        "url": 'correo-credentials/',
        "vista": EmailCredentialsView.as_view(),
        "namespace": 'admin_email_credentials',
    },
    {
        "nombre": "Alertas",
        "url": 'alertas/',
        "vista": AlertaView.as_view(),
        "namespace": 'admin_alertas',
    },
    {
        "nombre": "Llamados a la Acción",
        "url": 'llamados-accion/',
        "vista": LlamadoAccionView.as_view(),
        "namespace": 'admin_llamados_accion',
    },
)


notificaciones_urls = (
    {
        "nombre": "Notificaciones App",
        "url": 'notificaciones_app/',
        "vista": NotificacionesAppView.as_view(),
        "namespace": 'admin_notificaciones_app',
    },
    {
        "nombre": "Correo",
        "url": 'correo/',
        "vista": NotificacionesCorreoView.as_view(),
        "namespace": 'admin_correos',
    },
    {
        "nombre": "PushApp",
        "url": 'pushapp/',
        "vista": NotificacionesPushAppView.as_view(),
        "namespace": 'admin_pushapp',
    },
)