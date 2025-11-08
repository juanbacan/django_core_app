from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as trans
from core.models import GrupoModulo, Modulo

def has_access_module(request):
    """
    Retorna True si el usuario pertenece a un grupo que tenga un Modulo
    cuyo `url` coincida (o esté contenida) en `path`. De lo contrario False.
    """
    user = request.user
    path = request.path

    if not user.is_authenticated:
        return False
    elif user.is_superuser:
        return True

    # Obtenemos los ID de los grupos a los que pertenece el usuario
    group_ids = user.groups.values_list('id', flat=True)

    # Recuperamos todas las URLs de 'modulos' asociadas a esos grupos
    # (usando tu modelo GrupoModulo como nexo)
    modulos_urls = GrupoModulo.objects.filter(
        grupo_id__in=group_ids
    ).values_list('modulos__url', flat=True)

    permitidas = ['/administracion/', '/usuario/']
    # Las rutas en `permitidas` siempre deben permitirse
    for p in permitidas:
        if path.startswith(p):
            return True
 
    for modulo_url in modulos_urls:
        # if modulo_url and path.startswith(modulo_url):
        if modulo_url and modulo_url in path:
            return True

    return False


class SecureModuleMixin(AccessMixin):
    def handle_no_permission(self):
        # Si esta logueado pero no tiene acceso a la vista redirigir al inicio
        if self.request.user.is_authenticated:
            return redirect('/')
        return redirect('/accounts/login/?next=' + self.request.path)

    def dispatch(self, request, *args, **kwargs):
        has_access, error_message = False, None

        try:
            has_access = request.user.is_authenticated and has_access_module(request)
        except Exception as ex:
            print(ex)
            error_message = request.user.is_superuser and str(ex)

        if not has_access:
            messages.error(request, trans("No tienes acceso"))
            error_message and messages.error(request, f'Método: {request.method}, Error: {error_message}')
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)