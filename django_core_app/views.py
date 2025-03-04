import requests, os
from datetime import date

from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import login, logout
from django.contrib import messages
from django import forms
from django.apps import apps
from django.conf import settings
from django.views.generic.base import ContextMixin
from django.db import transaction
from django.db.models import Q

from allauth.account.adapter import DefaultAccountAdapter as account_adapter
from allauth.socialaccount.models import SocialAccount
from allauth.account.models import EmailAddress
from allauth.account.adapter import get_adapter
from dal import autocomplete

from applications.core.mixins import SecureModuleMixin
from applications.core.models import NotificacionUsuario, NotificacionUsuarioCount, CustomUser

from applications.core.utils import bad_json, success_json, get_query_params, \
    save_error, upload_image_to_firebase_storage


def obtener_extra_data(data):
    """
    Construye el diccionario con los datos extra de Google.
    """
    return {
        'id': data.get('sub'),
        'email': data.get('email'),
        'verified_email': data.get('email_verified'),
        'name': data.get('name'),
        'given_name': data.get('given_name'),
        'family_name': data.get('family_name'),
        'picture': data.get('picture'),
        'locale': 'es',
    }


def autenticar_usuario(request, user):
    """
    Autentica al usuario, asigna el backend, inicia sesión, muestra mensaje
    y redirige a la URL de referencia.
    """
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    messages.success(request, f'Ha iniciado sesión exitosamente como {user.username}')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@csrf_exempt
def one_tap_google_login(request):
    try:
        credential = request.POST.get('credential')
        if not credential:
            return HttpResponse('Error: Falta el token de credencial', status=400)
        
        # Se recomienda utilizar GET para consultar tokeninfo
        url = f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}'
        resp = requests.post(url)
        
        if resp.status_code != 200:
            return HttpResponse(f'Error: {resp.text}', status=resp.status_code)
        
        data = resp.json()
        extra_data = obtener_extra_data(data)
        uid = data.get('sub')
        email = data.get('email')
        # Convertir el valor de verificación a booleano
        is_email_verified = str(data.get('email_verified', 'false')).lower() == 'true'
        
        # Si el usuario ya tiene una cuenta social asociada con Google, actualizar y loguear
        if SocialAccount.objects.filter(uid=uid, provider='google').exists():
            social = SocialAccount.objects.get(uid=uid, provider='google')
            user = social.user
            try:
                email_obj, _ = EmailAddress.objects.get_or_create(user=user, email=email)
                email_obj.verified = is_email_verified
                email_obj.save()
            except Exception as ex:
                save_error(request, ex, "ONE TAP GOOGLE LOGIN - Actualización de EmailAddress")
            
            return autenticar_usuario(request, user)
        else:
            # Si existe un EmailAddress para este email, utilizar el usuario asociado
            try:
                email_obj = EmailAddress.objects.get(email=email)
                email_obj.verified = is_email_verified
                email_obj.save()
                user = email_obj.user
                SocialAccount.objects.create(
                    user=user,
                    uid=uid,
                    provider='google',
                    extra_data=extra_data
                )
                return autenticar_usuario(request, user)

            except EmailAddress.DoesNotExist:
                # Si no existe EmailAddress, se crea el usuario y se asocia
                form = forms.Form()
                form.cleaned_data = {
                    'first_name': data.get('given_name'),
                    'last_name': data.get('family_name'),
                    'email': email,
                }
                adapter = get_adapter()
                new_user = adapter.new_user(request)
                user = adapter.save_user(request, new_user, form=form)
                
                SocialAccount.objects.create(
                    user=user,
                    uid=uid,
                    provider='google',
                    extra_data=extra_data
                )
                EmailAddress.objects.create(
                    user=user,
                    email=email,
                    verified=is_email_verified,
                    primary=True
                )
                return autenticar_usuario(request, user)
    except Exception as ex:
        save_error(request, ex, "ONE TAP GOOGLE LOGIN")
        return redirect('account_login')


def api(request):
    action, data = get_query_params(request)

    if not action:
        return bad_json(mensaje="No se ha enviado el parametro action")
    if not request.user.is_authenticated:
        return bad_json(mensaje="No estás autenticado")

    if request.method == 'POST':
        try:    
            if action == 'reset_notificacion':
                user_id = data.get('user_id', None)
                if user_id:
                    NotificacionUsuarioCount.objects.filter(usuario_id=user_id).update(numero=0)
                return success_json(mensaje="Notificacion reseteada")
            
            elif action == 'ver_notificacion':
                id = data.get('id', None)
                if id:
                    NotificacionUsuario.objects.filter(id=id).update(visto=True)
                return success_json(mensaje="Notificacion vista")


            return bad_json(mensaje="No se encuentra la accion")
        
        except Exception as ex:
            save_error(request, ex, "API MAIN")
            return bad_json(mensaje="Ha ocurrido un error")
        

    if request.method == 'GET':
        if action == "volver_usuario":
            if request.session.get('volver_usuario', None) and request.session.get('usuario_original', None):
                usuario = CustomUser.objects.get(id=request.session['usuario_original'])
                usuario.backend = 'allauth.account.auth_backends.AuthenticationBackend'
                url = request.session.get('volver_usuario_url', "/administracion")
                logout(request)
                login(request, usuario)
                if "volver_usuario" in request.session:
                    del request.session['volver_usuario']
                if "volver_usuario_url" in request.session:
                 del request.session['volver_usuario_url']
                if "usuario_original" in request.session:
                    del request.session['usuario_original']
                return redirect(url)
            else:
                return redirect('/')

    else:
        return success_json(mensaje = "Ok")
    

class ModelAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        model = self.forwarded.get('model', None)
        list_applications = settings.AUTO_COMPLETE_APPS

        if not model:
            return
        
        for app in list_applications:
            try:
                model = apps.get_model(app, model)
                break
            except:
                pass
        
        if model and self.q:
            qs = model.flexbox_query(self.q)
        elif model:
            qs = model.objects.all()

        return qs
    

class CustomUserAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = CustomUser.objects.all()
        if self.q:
            qs = qs.filter(
                Q(first_name__search=self.q) | 
                Q(first_name__icontains=self.q) | 
                Q(last_name__icontains=self.q) | 
                Q(email__icontains=self.q) |
                Q(username__icontains=self.q)
            )
            
        return qs
    
    def get_result_label(self, item):
        return item.username + " " + item.first_name + " " + item.last_name
    
    def get_selected_result_label(self, item):
        return item.first_name + " " + item.last_name
    

@csrf_exempt
@login_required
def upload_image(request, series: str=None, article: str=None): 
       
    if request.method != "POST":
        return JsonResponse({'Error Message': "Wrong request"})
    
    if request.user.is_anonymous:
        return JsonResponse({'Error Message': "You are not authenticated"})

    file_obj = request.FILES['file']
    file_name_suffix = file_obj.name.split(".")[-1]
    if file_name_suffix not in ["jpg", "png", "gif", "jpeg", "webp"]:
        return JsonResponse({"Error Message": f"Wrong file suffix ({file_name_suffix}), supported are .jpg, .png, .gif, .webp, .jpeg"})

    if not settings.HABILITADO_FIREBASE:
        file_path = os.path.join(settings.MEDIA_ROOT, 'cargadas', file_obj.name)
        try:
            with open(file_path, 'wb+') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
        except Exception as ex:
            # Crear carpeta si no existe
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'cargadas_tiny'), exist_ok=True)
            with open(file_path, 'wb+') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)

        return JsonResponse({
            'message': 'Image uploaded successfully',
            'location': os.path.join(settings.MEDIA_URL, 'cargadas', file_obj.name)
        })
    else: 
        url = upload_image_to_firebase_storage(file_obj)        
        
        return JsonResponse({
            'message': 'Image uploaded successfully',
            'location': url
        })

class SuperuserRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseRedirect("/")
        return super().dispatch(request, *args, **kwargs)
    

class LoginModalView(View):
    def get(self, request, *args, **kwargs):
        context = {}
        context['form'] = forms.LoginForm()
        return render(request, 'forms/formLoginModal.html', context)
    

class ViewClassBase(ContextMixin, View):
    model = None
    titulo = ''
    modulo = ''
    metadescription = ''
    metakeywords = ''

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        action, data = get_query_params(request)
        self.action = action
        self.data = data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metadescription"] = self.metadescription
        context["metakeywords"] = self.metakeywords

        context["path"] = self.request.path
        context["fecha"] = str(date.today())
        context["action"] = self.action

        return context

    def dispatch(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        data = {}
        error_message = ""
        if request.method == "POST":
            action = request.POST.get("action")
            try:
                with transaction.atomic():
                    response = super().dispatch(request, *args, **kwargs)
            # except SomeValueException as ex:
            #     res_json = {"message": str(ex)}
            #     response = JsonResponse(res_json, status=202)
            #     has_except = True
            #     error_message = str(ex)
            # except FormException as ex:
            #     res_json = ex.dict_error
            #     response = JsonResponse(res_json, status=202)
            #     has_except = True
            #     error_message = "Formulario no válido"
            # except IntegrityError as ex:
            #     has_except = True
            #     msg = str(ex)
            #     error_message = "Integrity Error"
            #     for key in getattr(settings, 'CONSTRAINT_MSG', {}).keys():
            #         if re.search(f"\\b{key}\\b", msg):
            #             error_message = getattr(settings, 'CONSTRAINT_MSG', {}).get(key) or 'Integrity Error'
            #     if request.user.is_superuser:
            #         error_message = f"{error_message} | {msg}"
            #     res_json = {"message": error_message}
            #     response = JsonResponse(res_json, status=202)
            except Exception as ex:
                print(ex)
                error_message = "Intente Nuevamente"
                if request.user.is_superuser:
                    error_message = f"{error_message} | {ex}"
                data = {"mensaje": error_message, 'result': 'error'}

                if is_ajax:
                    response = JsonResponse(data, status=500)
                else:
                    messages.error(request, error_message)
                    response = redirect(request.path)

        elif request.method == "GET":
            try:
                response = super().dispatch(request, *args, **kwargs)
            except Exception as ex:
                error_message = "Ha ocurrido un error inesperado"
                if request.user.is_superuser:
                    error_message = f"{error_message} | {ex}"
                if is_ajax:
                    response = JsonResponse({"mensaje": error_message, 'result': 'error'}, status=500)
                else:
                    messages.error(request, error_message)
                    response = redirect(request.path)

        return response

class ViewAdministracionBase(LoginRequiredMixin, SecureModuleMixin, ViewClassBase):
    # def setup(self, request, *args, **kwargs):
    #     super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['agrupacion_modulos'] = []
        if self.request.user.is_authenticated:
            context["lista_modulos_id"] = self.request.user.mi_lista_modulos_id()
            agrupacion_modulos = self.request.user.mis_agrupaciones_modulos()
            # Ver cual agrupacion de modulos esta activa dependiendo de la url del modulo y la url actual
            url_actual = self.request.path
            for agrupacion in agrupacion_modulos:
                for modulo in agrupacion.modulos.all():
                    if modulo.url in url_actual:
                        setattr(agrupacion, 'activo', True)
                        context['modulo_activo'] = modulo
                        # context['agrupacion_activa'] = agrupacion
                        break
            context['agrupacion_modulos'] = agrupacion_modulos
        return context
