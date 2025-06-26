# django-core-app

Aplicación reusable para Django que integra un conjunto de utilidades listas para usar. Incluye modelos, vistas, formularios y herramientas pensadas para crear rápidamente un backend administrativo con gestión de usuarios y notificaciones.

## Instalación

Puedes instalar el paquete directamente desde GitHub:

```bash
pip install git+https://github.com/juanbacan/django_core_app.git
```

## Características principales

El paquete `core` proporciona las siguientes funcionalidades:

### Modelos base

- **CustomUser**: Extiende el modelo de usuario de Django e incluye campo de imagen y operaciones para obtener correos o cuentas sociales vinculadas.
- **AplicacionWeb**: Configura información y metadatos del sitio (título, logos, imágenes sociales, etc.).
- **Alerta** y **LlamadoAccion**: Permiten mostrar mensajes o llamados a la acción en la interfaz.
- **EmailCredentials**: Maneja credenciales rotativas para el envío de correos.
- **TipoNotificacion**, **NotificacionUsuario** y **NotificacionUsuarioCount**: Gestionan las notificaciones internas y el conteo de no leídas.
- **ErrorApp**: Registra errores ocurridos en la aplicación.
- **CorreoTemplate**, **Modulo**, **GrupoModulo** y **AgrupacionModulo**: Estructuran plantillas de correo y la organización de módulos del sistema.

### Formularios y widgets

- **BootstrapFieldsMixin** y **ModelBaseForm**: Generan formularios compatibles con Bootstrap y soportan inlines.
- Formularios de administración para usuarios, notificaciones y módulos.

### Vistas y utilidades

- **LoginModalView** y autenticación con Google One‑Tap.
- **ModelAutocompleteView** para búsquedas con `django-autocomplete-light`.
- **ViewAdministracionBase**: clase genérica que implementa listados, búsqueda, filtros, paginación y exportación a Excel.
- **ModelCRUDView**: vista genérica para operaciones CRUD en la administración.
- **API** para operaciones comunes (resetear y marcar notificaciones, cambiar de usuario temporalmente).
- **upload_image** permite subir imágenes a Firebase o al almacenamiento local.

### Notificaciones y mensajería

- Envío de notificaciones *web push* a usuarios individuales o grupos.
- Notificaciones internas de la aplicación (almacenadas en base de datos).
- Plantillas de correo y envío de emails en segundo plano.
- Integración con la API de WhatsApp para enviar mensajes o gestionar un bot.

### Herramientas adicionales

- Mixin de seguridad para controlar el acceso a módulos según los grupos del usuario.
- Funciones auxiliares en `utils.py` para exportar a Excel, manejar imágenes, formatear tiempos y registrar errores.
