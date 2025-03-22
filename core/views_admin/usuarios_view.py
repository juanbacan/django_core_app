from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib.auth import login, logout

from core.administracion_forms import CustomUserForm
from core.models import CustomUser
from core.views_admin import ViewAdministracionBase

from core.utils import success_json, error_json, get_url_params, get_redirect_url


class UsuariosView(ViewAdministracionBase):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        
        return error_json(mensaje="Acción no permitida")
    
    def post_add(self, request, context, *args, **kwargs):
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            return success_json(mensaje="Usuario ingresado correctamente", url=get_redirect_url(request))
        return error_json(forms=[form])
    
    def post_edit(self, request, context, *args, **kwargs):
        id = self.data.get('id')
        usuario = CustomUser.objects.get(id=id)
        form = CustomUserForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return success_json(mensaje="Usuario actualizado correctamente", url=get_redirect_url(request))
        print(form.errors)
        return error_json(forms=[form])
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        if self.data.get('search', None):
            usuarios = CustomUser.objects.filter(
                username__icontains=self.data.get('search')
            )
        else:
            usuarios = CustomUser.objects.all()
        
        context['usuarios'] = usuarios

        paginator = Paginator(usuarios, 30)
        page_number = request.GET.get('pagina', 1)
        context['page_obj'] = paginator.get_page(page_number)
        context['url_params'] = get_url_params(self.request)

        return render(request, 'administracion/usuarios/lista.html', context)
    
    def get_add(self, request, context, *args, **kwargs):
        context['form'] = CustomUserForm()
        return render(request, 'forms/formAdmin.html', context)
    
    def get_edit(self, request, context, *args, **kwargs):
        id = self.data.get('id')
        context['object'] = CustomUser.objects.get(id=id)
        context['form'] = CustomUserForm(instance=context['object'])
        return render(request, 'forms/formAdmin.html', context)
    
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
