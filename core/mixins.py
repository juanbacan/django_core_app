from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as trans


def has_access_module(request):
    if request.user.is_superuser:
        return True

    # if not request.user.es_administrativo:
    #     return False

    # has_module = Modulo.objects.no_deleted_filter(
    #     id__in=GroupModulo.objects.no_deleted_filter(
    #         group__in=request.user.groups.all()
    #     ).values_list(
    #         'modulos__id', flat=True
    #     )
    # ).annotate(
    #     url_2=CustomValueDb(request.path)
    # ).filter(url_2__istartswith=F('url')).exists()

    # return has_module


class SecureModuleMixin(AccessMixin):
    def handle_no_permission(self):
        return redirect("/")

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