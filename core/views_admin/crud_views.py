from django.contrib.auth import login, logout

from core.views import ModelCRUDView
from core.models import AgrupacionModulo, Modulo, TipoNotificacion, NotificacionUsuario, \
    CustomUser, GrupoModulo
from core.administracion_forms import AgrupacionModuloForm, GrupoForm, ModuloForm, TipoNotificacionForm, CustomUserForm
from django.contrib.auth.models import Group

from core.utils import error_json, success_json, get_redirect_url

class AgrupacionModulosView(ModelCRUDView):
    model = AgrupacionModulo
    form_class = AgrupacionModuloForm
    list_display = [
        'nombre',
        'icono',
        'url',
        'orden',
    ]
    ordering = ['orden', 'id']


class GroupsView(ModelCRUDView):
    model = Group
    form_class = GrupoForm
    list_display = ['name']
    ordering = ['id']


class ModulosView(ModelCRUDView):
    model = Modulo
    form_class = ModuloForm
    list_display = ['nombre', 'icon', 'url', 'orden', 'activo']
    ordering = ['id']


class GrupoModulosView(ModelCRUDView):
    model = GrupoModulo
    list_display = ['grupo', 'modulos']
    ordering = ['id']

    def get_queryset(self):
        return super().get_queryset().filter(grupo__id=self.kwargs.get('grupo_id'))


class NotificacionesAppView(ModelCRUDView):
    """
    Clase base para vistas de administración que maneja las acciones CRUD
    y la renderización de formularios.
    """
    
    model = TipoNotificacion
    form_class = TipoNotificacionForm
    list_display = ['tipo', 'titulo', 'mensaje_final'] 
    ordering = ['id']

    def post_delete(self, request, context, *args, **kwargs):
        tipo = TipoNotificacion.objects.get(id=request.POST.get('id'))
        notificaciones = NotificacionUsuario.objects.filter(tipo=tipo)
        if notificaciones:
            return error_json(mensaje="No se puede eliminar el tipo de notificación, hay notificaciones asociadas")
        tipo.delete()
        return success_json(url=get_redirect_url(request))
    

class UsuariosView(ModelCRUDView):
    model = CustomUser
    form_class = CustomUserForm
    search_fields = ['username', 'email']
    template_list = 'core/administracion/usuarios/lista.html'
    list_display = [
        'username', 
        'email', 
        ('Grupos', lambda u: " ".join(
                f'<span class="badge bg-secondary">{g.name}</span>'
                for g in u.groups.all()
        )),
        'is_staff',
        'is_active'
    ]
    ordering = ['id']

    def get_queryset(self):
        return super().get_queryset().prefetch_related('groups')
    
    def get_ingresar_usuario(self, request, context, *args, **kwargs):
        usuario_original = request.user.id
        id = self.data.get('id')
        usuario = CustomUser.objects.get(id=id)
        usuario.backend = 'allauth.account.auth_backends.AuthenticationBackend'
        logout(request)
        login(request, usuario)
        request.session['usuario_original'] = usuario_original
        request.session['volver_usuario'] = True
        request.session['volver_usuario_url'] = request.META.get('HTTP_REFERER')
        return success_json(resp = {"sessionid": request.session.session_key})

