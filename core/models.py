import datetime, inspect

from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.db.models import Q
from django.utils.functional import cached_property

from allauth.socialaccount.models import SocialAccount
from allauth.account.models import EmailAddress
from django_resized import ResizedImageField
from tinymce import models as tinymce_models


class CustomUser(AbstractUser):
    premium = models.BooleanField(default=False)
    imagen = models.ImageField(upload_to='usuarios', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-id', 'last_name', 'first_name']

    def get_photo_user(self):
        if self.imagen:
            return self.imagen.url
        social = self.socialaccount_set.first()
        return social.get_avatar_url() if social else None
    
    def get_nombre_completo(self):
        nombre = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return nombre if nombre else self.username

    def mis_correos(self):
        return EmailAddress.objects.filter(user=self)
        
    def mis_social_accounts(self):
        return SocialAccount.objects.filter(user=self)
    
    def mi_email(self):
        correo_verificado = EmailAddress.objects.filter(user=self, verified=True).first()
        if correo_verificado:
            return correo_verificado.email
        if self.email:
            return self.email
        correo_no_verificado = EmailAddress.objects.filter(user=self).first()
        return correo_no_verificado.email if correo_no_verificado else None
         
    @cached_property
    def mis_modulos_y_agrupaciones(self):
        """
        Método optimizado que retorna en una sola consulta:
        - Agrupaciones con sus módulos filtrados por permisos del usuario
        - Lista de IDs de módulos a los que tiene acceso
        """
        if self.is_superuser:
            # Para superusuario: todas las agrupaciones con todos sus módulos activos
            agrupaciones = (
                AgrupacionModulo.objects
                .prefetch_related('modulos')
                .order_by('orden', 'nombre')
            )
            modulos_ids = set(Modulo.objects.values_list('id', flat=True))
            
            # Filtrar agrupaciones que tienen módulos activos
            agrupaciones_con_modulos = []
            for agrupacion in agrupaciones:
                modulos_activos = agrupacion.modulos_activos
                if modulos_activos:
                    agrupaciones_con_modulos.append(agrupacion)
            
            return {
                'agrupaciones': agrupaciones_con_modulos,
                'modulos_ids': modulos_ids
            }
        
        else:
            # Para usuario normal: una sola consulta optimizada
            user_groups = self.groups.all()
            
            # Obtener agrupaciones con módulos filtrados en una consulta
            agrupaciones = (
                AgrupacionModulo.objects
                .filter(modulos__grupomodulo__grupo__in=user_groups)
                .prefetch_related(
                    models.Prefetch(
                        'modulos',
                        queryset=Modulo.objects.filter(
                            activo=True,
                            grupomodulo__grupo__in=user_groups
                        ).distinct().order_by('orden'),
                        to_attr='modulos_permitidos'
                    )
                )
                .distinct()
                .order_by('orden', 'nombre')
            )
            
            # Obtener IDs de módulos permitidos
            modulos_ids = set(
                Modulo.objects
                .filter(grupomodulo__grupo__in=user_groups, activo=True)
                .distinct()
                .values_list('id', flat=True)
            )
            
            # Filtrar agrupaciones que tienen al menos un módulo permitido
            agrupaciones_con_modulos = []
            for agrupacion in agrupaciones:
                modulos_permitidos = getattr(agrupacion, 'modulos_permitidos', [])
                if modulos_permitidos:
                    agrupaciones_con_modulos.append(agrupacion)
            
            return {
                'agrupaciones': agrupaciones_con_modulos,
                'modulos_ids': modulos_ids
            }   
                
    @staticmethod
    def flexbox_query(query):
        return CustomUser.objects.filter(Q(first_name__search=query) | Q(first_name__icontains=query) | 
                                         Q(last_name__icontains=query) | Q(email__icontains=query) |
                                         Q(username__icontains=query))


class ModeloBase(models.Model):
    """
    Clase base para todos los modelos de la aplicación.
    """
    created_by = models.ForeignKey(CustomUser, related_name='%(app_label)s_%(class)s_created', editable=False, on_delete=models.SET_NULL, null=True)
    modified_by = models.ForeignKey(CustomUser, related_name='%(app_label)s_%(class)s_modified', editable=False, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if self.created_at is None:
            self.created_at = datetime.datetime.now()

        for frame_record in inspect.stack():
            if frame_record[3]=='get_response':
                request = frame_record[0].f_locals['request']
                break
            else:
                request = None

        user_id = request.user.id if request else 1
        
        if not self.pk and not self.created_by:
            self.created_by_id = user_id
        self.modified_by_id = user_id
        super(ModeloBase, self).save(*args, **kwargs)

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s' % self.id

        
class AplicacionWeb(ModeloBase):
    url = models.URLField(null=True, blank=True, max_length=200, verbose_name=u'URL SITIO')
    titulo_sitio = models.CharField(max_length=300, null=True, blank=True, verbose_name=u'Título Corto del Sitio')
    favicon = models.ImageField(upload_to='aplicacion_web', null=True, blank=True)
    logo = ResizedImageField(size=[160, 160], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True, verbose_name=u'Logo')
    logo_horizontal = ResizedImageField(size=[160, 160], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True, verbose_name=u'Logo horizontal')
    logo_horizontal_negativo = ResizedImageField(size=[160, 160], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True, verbose_name=u'Logo horizontal negativo')
    image_content = ResizedImageField(size=[1200, None], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True, verbose_name=u'Imagen Contenido')
    # SEO
    social_images = ResizedImageField(size=[1200, None], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True, verbose_name=u'Imagen Social')
    title = models.CharField(max_length=300, null=True, blank=True)
    meta_title = models.CharField(max_length=300, null=True, blank=True)
    meta_description = models.TextField(max_length=500, null=True, blank=True)
    # WEBPUSH
    logo_webpush = ResizedImageField(size=[300, 300], force_format="WEBP", quality=75, upload_to='aplicacion_web', null=True, blank=True)
    group_name_webpush = models.CharField(max_length=100, null=True, blank=True)
    # REDES SOCIALES
    email_contacto = models.EmailField(max_length=300, null=True, blank=True, verbose_name=u'Email de Contacto')
    celular_contacto = models.CharField(max_length=300, null=True, blank=True, verbose_name=u'Celular de Contacto')
    facebook = models.URLField(null=True, blank=True, max_length=200)
    instagram = models.URLField(null=True, blank=True, max_length=200)
    tiktok = models.URLField(null=True, blank=True, max_length=200)
    youtube = models.URLField(null=True, blank=True, max_length=200)
    linkedin = models.URLField(null=True, blank=True, max_length=200)

    def url_safe(self):
        if self.url and self.url[-1] == '/':
            return self.url[:-1]
        return self.url
    
    class Meta:
        verbose_name = 'Aplicación Web'
        verbose_name_plural = 'Aplicación Web'


CHOICES_COLOR = (
    ('primary', 'Primary'),
    ('secondary', 'Secondary'),
    ('success', 'Success'),
    ('danger', 'Danger'),
    ('warning', 'Warning'),
    ('info', 'Info'),
    ('light', 'Light'),
    ('dark', 'Dark'),
)

class Alerta(ModeloBase):
    titulo = models.CharField(max_length=100)
    descripcion = tinymce_models.HTMLField()
    color = models.CharField(max_length=100, choices=CHOICES_COLOR, null=True, blank=True)
    activo = models.BooleanField(default=False)
    url = models.URLField(null=True, blank=True, max_length=200, verbose_name=u'URL')
    orden = models.IntegerField(default=1)

    def __str__(self):
        return self.descripcion
    
    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"


class LlamadoAccion(ModeloBase):
    PAGINA_CHOICES = (
        ('home', 'Home'),
        ('pro', 'Pro'),
        ('free', 'Free'),
    )

    imagen = models.ImageField(upload_to='llamado_accion')
    url = models.URLField(max_length=200, verbose_name=u'URL')
    pagina = models.CharField(max_length=100, choices=PAGINA_CHOICES, default='home')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return self.url


class EmailCredentials(models.Model):
    host = models.CharField(max_length=255)
    port = models.IntegerField()
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    conteo = models.IntegerField(default=1)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "Credencial de Email"
        verbose_name_plural = "Credenciales de Email"


class TipoNotificacion(models.Model):
    tipo = models.CharField(max_length=100, unique=True)
    titulo = models.CharField(max_length=100)
    mensaje_final = models.TextField(max_length=600)

    def __str__(self):
        return self.tipo
    
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.strip()
        self.mensaje_final = self.mensaje_final.strip()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Tipo Notificacion"
        verbose_name_plural = "Tipos Notificaciones"


class NotificacionUsuario(ModeloBase):
    usuario_notifica = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    usuario_notificado = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='usuario_notificado')
    tipo = models.ForeignKey(TipoNotificacion, on_delete=models.CASCADE)
    url = models.CharField(max_length=100)
    mensaje = models.TextField(max_length=1000)
    visto = models.BooleanField(default=False)

    def __str__(self):
        return str(self.mensaje)

    class Meta:
        verbose_name = "Notificación Usuario"
        verbose_name_plural = "Notificaciones Usuarios"
        indexes = [
            models.Index(fields=["usuario_notificado"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["usuario_notificado", "created_at"]),
        ]

    
    def titulo(self):
        return self.tipo.titulo

    def mensaje_final(self, datos_extra=None):
        if self.tipo.tipo == 'notificacion_personalizada':
            return self.mensaje if self.mensaje else 'Notificación Personalizada'
        
        template = self.tipo.mensaje_final
        valores = {
            "usuario": self.usuario_notifica.username,
            "mensaje": self.mensaje,
            **(datos_extra or {})
        }
        return template.format(**valores)


# Modelo que representa el número de notificaciones que tiene un usuario
class NotificacionUsuarioCount(ModeloBase):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    numero = models.IntegerField(default=0)

    def __str__(self):
        return str(self.usuario)

    class Meta:
        unique_together = ('usuario',)
        verbose_name = "Notificacion Usuario Count"
        verbose_name_plural = "Notificaciones Usuarios Count"


class ErrorApp(ModeloBase):
    path = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    error = models.TextField()
    error_str = models.TextField()
    mensaje = models.TextField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip = models.CharField(max_length=255, null=True, blank=True)
    get = models.TextField(null=True, blank=True)
    post = models.TextField(null=True, blank=True)
    cookies = models.TextField(null=True, blank=True)
    headers = models.TextField(null=True, blank=True)
    trace = models.TextField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.url + " - " +  self.mensaje + " - " + self.created_at.strftime('%Y-%m-%d %H:%M:%S')
    
    class Meta:
        verbose_name = "Error de Aplicación"
        verbose_name_plural = "Errores de Aplicación"


class CorreoTemplate(ModeloBase):
    CHOICE_TIPO_CORREO = (
        ('correos', 'Correos'),
        ('inscripciones', 'Inscripciones'),
        ('premium', 'Premium'),
    )
    
    nombre = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    html = models.TextField()
    button_text = models.CharField(max_length=255, null=True, blank=True)
    button_url = models.CharField(max_length=255, null=True, blank=True)
    tipo = models.CharField(max_length=255, choices=CHOICE_TIPO_CORREO, default='correos')

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = "Correo Template"
        verbose_name_plural = "Correos Templates"
    

class Modulo(ModeloBase):
    url = models.CharField(max_length=255)
    nombre = models.CharField(max_length=255)
    icon = models.CharField(max_length=255)
    orden = models.IntegerField(default=1)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        ordering = ['orden']


class GrupoModulo(ModeloBase):
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, unique=True)
    modulos = models.ManyToManyField(Modulo)

    def __str__(self):
        return self.grupo.name
    
    class Meta:
        verbose_name = "Módulos de un Grupo"
        verbose_name_plural = "Módulos Pertenecientes a un Grupo"
        ordering = ['grupo__name']
    
    @cached_property
    def modulos_por_agrupacion(self):
        """Retorna módulos agrupados por AgrupacionModulo sin duplicados."""
        from collections import OrderedDict
        
        # Obtener todos los módulos con sus agrupaciones
        modulos = self.modulos.prefetch_related('agrupacionmodulo_set').order_by('orden')
        
        # Agrupar por agrupación
        agrupaciones_dict = OrderedDict()
        
        for modulo in modulos:
            # Obtener la primera agrupación del módulo (debería haber solo una)
            agrupacion = modulo.agrupacionmodulo_set.first()
            
            if agrupacion:
                if agrupacion.id not in agrupaciones_dict:
                    agrupaciones_dict[agrupacion.id] = {
                        'agrupacion': agrupacion,
                        'modulos': []
                    }
                agrupaciones_dict[agrupacion.id]['modulos'].append(modulo)
        
        # Ordenar agrupaciones por orden
        return sorted(
            agrupaciones_dict.values(),
            key=lambda x: (x['agrupacion'].orden, x['agrupacion'].nombre)
        )


class AgrupacionModulo(ModeloBase):
    url = models.CharField(max_length=255, unique=True)
    nombre = models.CharField('Nombre', max_length=100)
    icono = models.CharField('Ícono', max_length=100, null=True, blank=True)
    modulos = models.ManyToManyField(Modulo, verbose_name='Urls del Sistema')
    orden = models.IntegerField('Orden de Prioridad', default=1)

    def __str__(self):
        return '{} {}'.format(self.nombre, self.orden)

    class Meta:
        verbose_name = 'Agrupación de Módulo'
        verbose_name_plural = 'Agrupaciones de Módulos'
        ordering = ('orden', 'nombre')

    @cached_property
    def modulos_activos(self):
        return self.modulos.filter(activo=True).order_by('orden')
    