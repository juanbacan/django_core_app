import os, json
from datetime import date
from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404, HttpResponseBadRequest
from django.views.generic import View, ListView
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
from django.db import models
from django.contrib.sites.models import Site
from django.views.decorators.http import require_POST
from django.forms import modelform_factory
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage, InvalidPage
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from allauth.account.adapter import get_adapter
from allauth.socialaccount.models import SocialAccount, SocialApp
from allauth.account.models import EmailAddress
import allauth.account.forms as forms_allauth

from dal import autocomplete, forward
from core.crud_registry import crud_registry

from google.oauth2 import id_token
from google.auth.transport import requests as g_requests
import urllib

from .mixins import SecureModuleMixin
from .models import NotificacionUsuario, NotificacionUsuarioCount, CustomUser, AgrupacionModulo, Modulo
from .forms import ModelBaseForm
from .forms import configure_auto_complete_widgets

from .utils import bad_json, queryset_to_excel, success_json, get_query_params, \
    save_error, upload_image_to_firebase_storage, get_redirect_url, \
    error_json, get_header, resolve_attr


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
        model_name = self.forwarded.get('model', None)
        if not model_name:
            return

        model = None
        # Si el forward viene como 'app_label.ModelName', usarlo directamente
        if isinstance(model_name, str) and '.' in model_name:
            try:
                app_label, model_cls = model_name.split('.', 1)
                model = apps.get_model(app_label, model_cls)
            except Exception:
                model = None

        # Intentar buscar en AUTO_COMPLETE_APPS (mantener compatibilidad)
        if model is None:
            list_applications = getattr(settings, 'AUTO_COMPLETE_APPS', [])
            for app in list_applications:
                try:
                    model = apps.get_model(app, model_name)
                    break
                except Exception:
                    continue

        # Último recurso: buscar en todas las apps por nombre de clase
        if model is None:
            for m in apps.get_models():
                if m.__name__ == model_name or f"{m._meta.app_label}.{m.__name__}" == model_name:
                    model = m
                    break

        if not model:
            return

        # Buscar la vista CRUD registrada para este modelo
        info = crud_registry.get(model)
        if not info:
            raise ValueError(f"No hay una ModelCRUDView registrada para el modelo {model.__name__}")

        view_cls = info.get('view')
        search_fields = getattr(view_cls, 'search_fields', None)
        if not search_fields:
            raise ValueError(f"La vista CRUD de {model.__name__} no define 'search_fields'")

        qs = model.objects.all()
        if self.q:
            for word in self.q.strip().split():
                q = Q()
                for field in search_fields:
                    q |= Q(**{f"{field}__icontains": word})
                qs = qs.filter(q)

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
    

class ModalForeignKeyLookupView(ListView):
    template_name = "core/widgets/modal_foreignkey_results.html"
    paginate_by = 10

    def dispatch(self, request, model_label, *args, **kwargs):
        self.model = apps.get_model(model_label)
        if self.model is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.model.objects.all()
        q  = self.request.GET.get("q", "").strip()
        if q:
            search_fields = self.request.GET.get("search_fields", "__str__").split(",")
            query = Q()
            for f in search_fields:
                query |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(query)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["list_display"] = self.request.GET.get("list_display", "__str__").split(",")
        return ctx
    

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
        file_path = os.path.join(settings.MEDIA_ROOT, 'cargadas_tiny', file_obj.name)
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
            'location': os.path.join(settings.MEDIA_URL, 'cargadas_tiny', file_obj.name)
        })
    else: 
        url = upload_image_to_firebase_storage(file_obj)        
        
        return JsonResponse({
            'message': 'Image uploaded successfully',
            'location': url
        })

ALLOWED_PREFIXES = (
    settings.URL_BASE,
    "https://storage.googleapis.com/",
    "https://firebasestorage.googleapis.com/",
)

@csrf_exempt
def tinymce_proxy(request):
    url = request.GET.get("url", "")
    if not url or not any(url.startswith(p) for p in ALLOWED_PREFIXES):
        return HttpResponseBadRequest("Invalid source")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TinyMCE-Proxy"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
    except Exception as e:
        return HttpResponse(f"Proxy error: {e}", status=502)

    r = HttpResponse(data, content_type=content_type)
    # Permite al editor dibujar en canvas el recurso proxied
    origin = request.headers.get("Origin", "*")
    r["Access-Control-Allow-Origin"] = origin
    r["Vary"] = "Origin"
    r["Cache-Control"] = "private, max-age=300"
    r["X-Content-Type-Options"] = "nosniff"
    return r

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
            # Una sola llamada que obtiene todo lo necesario
            datos_modulos = self.request.user.mis_modulos_y_agrupaciones
            
            # Asignar datos al contexto
            context["lista_modulos_id"] = list(datos_modulos['modulos_ids'])
            agrupaciones = datos_modulos['agrupaciones']
            
            # Detectar agrupación y módulo activo basado en la URL actual
            url_actual = self.request.path
            
            for agrupacion in agrupaciones:
                # Obtener módulos según el tipo de usuario
                if self.request.user.is_superuser:
                    modulos = agrupacion.modulos_activos
                else:
                    modulos = getattr(agrupacion, 'modulos_permitidos', [])
                
                # Verificar si algún módulo está activo (su URL coincide con la actual)
                for modulo in modulos:
                    if modulo.url in url_actual:
                        setattr(agrupacion, 'activo', True)
                        context['modulo_activo'] = modulo
                        context['agrupacion_activa'] = agrupacion
                        break
                
                # Asegurar que tenemos la propiedad correcta para el template
                if not self.request.user.is_superuser:
                    agrupacion.modulos_activos_filtrados = modulos
            
            context['agrupacion_modulos'] = agrupaciones
        return context


def _get_field_from_path(model, path):
    parts = path.split('__')
    field = model._meta.get_field(parts[0])
    for part in parts[1:]:
        if field.is_relation:
            model = field.related_model
            field = model._meta.get_field(part)
        else:
            raise ValueError(f"{path} no es un lookup válido.")

    # Si el campo final es relacional y no hubo más partes, usar su related_model
    if field.is_relation:
        model = field.related_model

    return field, model


class ModelCRUDView(ViewAdministracionBase):
    """
    Clase base para vistas CRUD de modelos en la administración.
    Debes definir los siguientes atributos en la subclase:
    - `model`: El modelo Django que se va a gestionar.
    - `form_class`: La clase de formulario para crear/editar el modelo.
    - `template_list`: La plantilla para listar los objetos del modelo.
    - `template_form`: La plantilla para el formulario de creación/edición.
    - `list_display`: Lista de campos a mostrar en la vista de lista (opcional).
    - `list_filter`: Lista de filtros a aplicar en la vista de lista (opcional).
    - `search_fields`: Campos a buscar en la vista de lista (opcional).
    - `exclude_fields`: Campos a excluir del formulario (opcional, por defecto incluye campos de auditoría).
    - `paginate_by`: Número de objetos por página en la vista de lista (opcional, por defecto 25).
    - `raw_id_fields`: Campos que se mostrarán como campos de búsqueda (opcional).
    - `auto_complete_fields`: Campos que se beneficiarán de la búsqueda automática (opcional).
    - `ordering`: Lista de campos para ordenar el queryset (opcional, por defecto ['-id']).
    """
    model = None
    form_class = None
    template_form = 'core/forms/formAdmin.html'
    template_list = 'core/layout/list.html'
    list_display = None
    list_filter = []
    search_fields = None
    exclude_fields = ('created_at', 'updated_at', 'created_by', 'modified_by')
    paginate_by = 25
    raw_id_fields = []
    auto_complete_fields = []
    ordering = ['-id']  # Ordenamiento por defecto

    # ATRIBUTOS PARA EXPORTACIÓN A EXCEL
    export_headers = None  # ['Código', 'Descripción']
    export_fields = None   # ['codigo', 'descripcion']
    export_filename = 'reporte.xlsx'

    # ACCIONES POR REGISTRO
    row_actions = [
        {
            "name": "edit",
            "label": "Editar",
            "icon": "fa-pencil",
            "url": lambda o: f"?action=edit&id={o.id}",
            'attrs': {
                'data-bs-toggle': 'tooltip',
                'title': 'Editar',
            },
        },
        {
            "name": "delete",
            "label": "Eliminar",
            "icon": "fa-trash",
            "url": lambda o: f"?action=delete&id={o.id}",
            "modal": True, # Indica que es un modal
            'attrs': {
                'data-bs-toggle': 'tooltip',
                'title': 'Eliminar',
            },
        },
    ]

    def get_row_actions(self, obj):
        """
        Devuelve la lista final de acciones que se mostrarán para `obj`.
        Cada elemento es un dict con keys: label, icon, url, modal (opcional).
        Puedes filtrar con 'visible_if'.
        """
        actions = []
        for a in self.row_actions:
            show = a.get("visible_if", lambda o: True)
            if show(obj):
                # Evaluar la URL (si es callable)
                url = a["url"](obj) if callable(a["url"]) else a["url"]
                actions.append({**a, "url": url})
        return actions
    
    def _querystring(self, exclude=('page','pagina')):
        """Devuelve la query-string actual sin los parámetros excluidos."""
        params = self.request.GET.copy()
        for p in exclude:
            params.pop(p, None)
        return urlencode(params, doseq=True)
    
    def paginate_queryset(self, queryset, raw_page=None, paginate_by=None):
        """
        Devuelve (page_obj, is_paginated) aceptando ?page= o ?pagina=
        y corrigiendo:
        • valores no numéricos
        • valores menores que 1
        • páginas fuera de rango
        """
        if paginate_by is None:
            paginate_by = self.paginate_by
        paginator   = Paginator(queryset, self.paginate_by)

        if raw_page is None:
            # acepta ?page= ó ?pagina= (en minúscula)
            raw_page    = (
                self.request.GET.get('page') or
                self.request.GET.get('pagina') or
                1
            )

        # ── 1) convertir a entero seguro ──────────────────
        try:
            page_number = int(raw_page)
        except (TypeError, ValueError):
            page_number = 1

        # ── 2) evitar valores < 1 ──────────────────────────
        if page_number < 1:
            page_number = 1

        # ── 3) obtener la página; si tuviera overflow va a última ──
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, InvalidPage, EmptyPage):
            # `InvalidPage` cubre “menor que 1” y “mayor que num_pages”,
            # pero ya prevenimos <1; aquí solo nos importa overflow.
            page_obj = paginator.page(paginator.num_pages)

        return page_obj, paginator.num_pages > 1
        

    def dispatch(self, request, *args, **kwargs):
        if not self.model:
            raise ValueError("Debes definir el atributo 'model'")
        
        if not self.form_class:
            self.form_class = modelform_factory(
                self.model,
                exclude=self.exclude_fields,
                form=ModelBaseForm
            )

        if self.raw_id_fields:
            setattr(self.form_class, "raw_id_fields", self.raw_id_fields)

        if self.auto_complete_fields:
            configure_auto_complete_widgets(self.form_class, self.model, getattr(self, 'auto_complete_fields', None))


        if not self.template_list:
            if not self.list_display:
                raise ValueError("Si no defines 'template_list', debes definir 'list_display'")
            self.template_list = 'core/layout/list.html'  # Template genérico por defecto

        return super().dispatch(request, *args, **kwargs)
    
    def get_export(self, request, context, *args, **kwargs):
        queryset = self.get_queryset()

        if not self.export_headers or not self.export_fields:
            raise ValueError("Debes definir `export_headers` y `export_fields` para exportar")

        excel_file = queryset_to_excel(queryset, self.export_headers, self.export_fields)
        filename = urllib.parse.quote(self.export_filename)

        response = HttpResponse(
            excel_file,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def get_queryset(self):
        """
        Retorna el queryset filtrado por búsqueda si se provee un término y 'search_fields' está definido.
        Permite múltiples palabras separadas por espacios.
        """
        queryset = self.model.objects.all()
        search = self.data.get("search")

        # --- Búsqueda ---
        if search and self.search_fields:
            for word in search.strip().split():
                q = Q()
                for field in self.search_fields:
                    q |= Q(**{f"{field}__icontains": word})
                queryset = queryset.filter(q)

        # --- Filtros ---
        for field in self.list_filter:
            value = self.request.GET.get(field)
            if value not in [None, ""]:
                queryset = queryset.filter(**{field: value})
        
        return queryset.distinct()  # Elimina duplicados si hay joins
    
    def get_filter_options(self):
        options = []
        for path in self.list_filter:
            header = get_header(self.model, path).lower()
            field, final_model = _get_field_from_path(self.model, path)

            # 1) Field con choices
            if field.choices:
                choices = list(field.choices)

            # 2) BooleanField
            elif field.get_internal_type() in ("BooleanField", "NullBooleanField"):
                choices = [("1", "Sí"), ("0", "No")]

            # 3) Relación   -> lista objetos relacionados
            elif field.is_relation:
                rel_qs  = final_model.objects.all()
                choices = [(obj.pk, str(obj)) for obj in rel_qs]

            # 4) Otros      -> valores distintos
            else:
                vals = (self.model.objects
                                .values_list(path, flat=True)
                                .distinct()
                                .order_by())
                choices = [(v, v) for v in vals if v is not None]

            options.append((header, choices))
        return options 
    
    def get_ordering(self):
        """
        Retorna la lista de campos para ordenar el queryset.
        Puede ser sobrescrito en subclases para lógica personalizada.
        """
        return self.ordering
    
    def build_display(self):
        headers, specs = [], []
        # si es popup, añadimos el campo ID como primera columna
        if self.request.GET.get("popup") == "1":
            headers.append("ID")
            specs.append(
                lambda o: format_html(
                    '<a href="#" onclick="window.opener.dismissAddPopup({}, {}, {}); window.close(); return false;">{}</a>',
                    json.dumps(o.pk),
                    json.dumps(str(o)),
                    json.dumps(self.request.GET.get("field_id", "")),
                    o.pk
                )
            )

        for item in self.list_display:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                label, spec = item
            else:
                label, spec = get_header(self.model, item), item
            headers.append(label)
            specs.append(spec)
        return headers, specs

    def build_table_rows(self, objs, specs):
        """
        Devuelve [(obj, [celda1, celda2, …]), …]
        para que el template tenga el objeto (para las acciones)
        y las celdas ya renderizadas.
        """
        rows = []
        for o in objs:
            cells = []
            for spec in specs:
                value = spec(o) if callable(spec) else resolve_attr(o, spec)
                cells.append(mark_safe(value))
            rows.append((o, cells))
        return rows

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'post_{self.action}'):
            return getattr(self, f'post_{self.action}')(request, context, *args, **kwargs)
        return error_json(mensaje="Acción no permitida")

    def post_add(self, request, context, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES or None)
        if form.is_valid():
            obj = form.save()
 
            # Si es popup se está agregando desde un popup
            if request.GET.get("popup") == "1":
                return JsonResponse({
                    "result": "ok",
                    "popup": True,
                    "pk": obj.pk,
                    "repr": str(obj),
                    "field_id": request.GET.get("field_id", ""),
                })
        
            return success_json(url=get_redirect_url(request))
        return error_json(mensaje="Error al guardar el objeto", forms=[form])

    def post_edit(self, request, context, *args, **kwargs):
        instance = self.model.objects.get(pk=self.data.get('id'))
        form = self.form_class(request.POST, request.FILES or None, instance=instance)
        if form.is_valid():
            obj = form.save()

            if request.GET.get("popup") == "1":
                return JsonResponse({
                    "result": "ok",
                    "popup": True,
                    "pk": obj.pk,
                    "repr": str(obj),
                    "field_id": request.GET.get("field_id", ""),
                })
            messages.success(request, "Objeto actualizado correctamente")
            return success_json(url=get_redirect_url(request, object=instance))
        return error_json(mensaje="Error al guardar el objeto", forms=[form])

    def post_delete(self, request, context, *args, **kwargs):
        obj = self.model.objects.get(id=request.POST.get('id'))
        obj.delete()
        return success_json(url=get_redirect_url(request))

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if self.action and hasattr(self, f'get_{self.action}'):
            return getattr(self, f'get_{self.action}')(request, context, *args, **kwargs)
        
        qs = self.get_queryset()
        ordering = self.get_ordering()
        if ordering:
            qs = qs.order_by(*ordering)
        page_obj, is_paginated = self.paginate_queryset(qs)

        context.update({
            "page_obj":      page_obj,
            "objs":          page_obj,                
            "is_paginated":  is_paginated,
            "url_params":    self._querystring(),
            "view":          self,                    
        })

        # Build display data for templates. If `list_display` is not defined
        # we still provide a sensible fallback so custom `template_list`
        # can render data without forcing every view to declare list_display.
        if self.list_display:
            headers, specs = self.build_display()
            table_rows = self.build_table_rows(page_obj, specs)
        else:
            # Fallback: single column with str(obj)
            headers = ["Objeto"]
            # specs is a list with a single callable that returns the object's string repr
            specs = [lambda o: str(o)]
            # build_table_rows expects callables or attribute names; reuse the method for markup
            # but build_table_rows will call mark_safe on the returned value, so use it safely.
            table_rows = []
            for o in page_obj:
                cells = [mark_safe(str(o))]
                table_rows.append((o, cells))

        context.update({
            'display_headers': headers,
            'table_rows': table_rows,
        })

        if self.list_filter:
            context['filter_options'] = self.get_filter_options()
        
        return render(request, self.template_list, context)

    def get_add(self, request, context, *args, **kwargs):
        context['form'] = self.form_class()
        return render(request, self.template_form, context)

    def get_edit(self, request, context, *args, **kwargs):
        obj = self.model.objects.get(pk=self.data.get('id'))
        context['object'] = obj
        context['form'] = self.form_class(instance=obj)
        return render(request, self.template_form, context)

    def get_delete(self, request, context, *args, **kwargs):
        obj = self.model.objects.get(pk=self.data.get('id'))
        context.update({
            'title': "Eliminar Objeto",
            'message': "¿Está seguro de que desea eliminar el objeto?",
            'formid': obj.id,
            'delete_obj': True
        })
        return render(request, 'core/modals/formModal.html', context)