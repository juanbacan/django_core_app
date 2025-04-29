import os
from datetime import date

from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django import forms
from django.apps import apps
from django.conf import settings
from django.views.generic.base import ContextMixin
from django.db import transaction
from django.db.models import Q
from django.contrib.sites.models import Site
from django.views.decorators.http import require_POST


from allauth.account.adapter import get_adapter
from allauth.socialaccount.models import SocialAccount, SocialApp
from allauth.account.models import EmailAddress
import allauth.account.forms as forms_allauth

from dal import autocomplete

from google.oauth2 import id_token
from google.auth.transport import requests as g_requests

from .mixins import SecureModuleMixin
from .models import NotificacionUsuario, NotificacionUsuarioCount, CustomUser

from .utils import bad_json, success_json, get_query_params, \
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


@csrf_exempt          # no hay token csrf en el POST que llega desde el widget
@require_POST         # sólo permitimos método POST
@transaction.atomic   # todo-o-nada: BD coherente si algo falla
def one_tap_google_login(request):
    """
    Endpoint para Google One-Tap.  
    1. Recibe el id_token (`credential`) del widget.  
    2. Lo valida localmente con la librería oficial de Google.  
    3. Localiza o crea User, SocialAccount y EmailAddress.  
    4. Autentica al usuario en la sesión y responde.
    """
    try:
        token = request.POST.get("credential")
        if not token:
            return JsonResponse({"error": "missing_token"}, status=400)
        
        # ── 0) Obtener el client_id desde SocialApp ───────────────────────
        try:
            current_site = Site.objects.get_current(request)
            google_app   = SocialApp.objects.get(
                provider="google", sites=current_site
            )
            client_id = google_app.client_id
        except SocialApp.DoesNotExist:
            return JsonResponse({"error": "google_not_configured"}, status=500)

        # ── 1) Validar id_token ─────────────────────────────────────────────
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                g_requests.Request(),
                client_id
            )
        except ValueError:
            return JsonResponse({"error": "invalid_token"}, status=400)

        # idinfo ya está verificado (aud, exp, firma, issuer)
        uid         = idinfo["sub"]
        email       = idinfo["email"]
        is_verified = idinfo.get("email_verified", False)
        extra_data  = obtener_extra_data(idinfo)

        # ── 2) SocialAccount existente ─────────────────────────────────────
        try:
            social = SocialAccount.objects.select_related("user").get(
                uid=uid, provider="google"
            )
            user = social.user

        except SocialAccount.DoesNotExist:
            # ── 3) ¿Existe EmailAddress con el mismo email? ────────────────────
            email_obj = (
                EmailAddress.objects.select_related("user")
                .filter(email=email)
                .first()
            )

            if email_obj:
                # Hay usuario previo con ese email → lo actualizamos
                user = email_obj.user
                email_obj.verified = is_verified
                email_obj.save()
            else:
                # No hay email ni usuario → creamos el User primero
                adapter = get_adapter(request)
                user = adapter.new_user(request)

                user.first_name = idinfo.get("given_name", "")
                user.last_name  = idinfo.get("family_name", "")
                user.email      = email

                adapter.populate_username(request, user)
                user.save()

                # Ahora sí podemos crear EmailAddress enlazado al usuario
                EmailAddress.objects.create(
                    user=user,
                    email=email,
                    verified=is_verified,
                    primary=True,
                )

            # En ambos casos, si no existe SocialAccount aún, lo creamos
            SocialAccount.objects.get_or_create(
                user=user,
                uid=uid,
                provider="google",
                defaults={"extra_data": extra_data},
            )

        return autenticar_usuario(request, user)

    except Exception as ex:
        save_error(request, ex, "ONE TAP GOOGLE LOGIN")
        return JsonResponse({"error": "server_error"}, status=500)


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
        context['form'] = forms_allauth.LoginForm()
        return render(request, 'core/forms/formLoginModal.html', context)
    

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
