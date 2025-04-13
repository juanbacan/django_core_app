import json, bson, requests, base64, math, sys, os, io
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image

from django.http import JsonResponse, Http404
from django.utils import timezone
from django.core.management.color import no_style
from django.db import connection, transaction
from django.views.debug import ExceptionReporter
from django.conf import settings
from django.contrib.auth.models import Group
from firebase_admin import storage

def reset_model(model):
    """
    Borra todos los registros de una tabla y reinicia los ID
    :param model: Modelo de la tabla
    :return: None
    """

    model.objects.all().delete()
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [model])
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)
    return


def db_table_exists(table_name):
    """
    Verifica si una tabla existe en la base de datos
    :param table_name: Nombre de la tabla
    :return: True si la tabla existe, False en caso contrario
    """
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}');")
        return cursor.fetchone()[0]

def gestionar_modulos(urls_sistema):
    """
    Crea o elimina los módulos y agrupaciones de módulos en la base de datos
    :param urls_sistema: Lista de diccionarios con las URL de los módulos y agrupaciones
    :return: None
    """

    from .models import CustomUser, Modulo, AgrupacionModulo, GrupoModulo
    try:
        if db_table_exists(Modulo._meta.db_table) and db_table_exists(AgrupacionModulo._meta.db_table) and db_table_exists(Group._meta.db_table):
            nombres_agrupaciones_validas = [url['nombre'] for url in urls_sistema]
            nombres_modulos_validos = [
                url['url'] + sub_url['url']
                for url in urls_sistema
                for sub_url in url['sub_urls']
            ]
            with transaction.atomic():
                for url in urls_sistema:
                    agrupacion, _ = AgrupacionModulo.objects.get_or_create(
                        url=url['url'],
                        defaults={
                            'nombre': url['nombre'],
                        }
                    )

                    for sub_url in url['sub_urls']:
                        modulo, _ = Modulo.objects.get_or_create(
                            url=url['url'] + sub_url['url'],
                            defaults={
                                'nombre': sub_url['nombre'],
                            }
                        )
                        agrupacion.modulos.add(modulo)

                AgrupacionModulo.objects.exclude(nombre__in=nombres_agrupaciones_validas).delete()
                Modulo.objects.exclude(url__in=nombres_modulos_validos).delete()

            group, _ = Group.objects.get_or_create(name='Desarrollador')
            try:
                grupo_modulos, _ = GrupoModulo.objects.get_or_create(grupo=group)
                grupo_modulos.modulos.set(Modulo.objects.all())
            except GrupoModulo.MultipleObjectsReturned:
                GrupoModulo.objects.filter(grupo=group).delete()
                grupo_modulos, _ = GrupoModulo.objects.get_or_create(grupo=group)
                grupo_modulos.modulos.set(Modulo.objects.all())

            for user in CustomUser.objects.filter(is_superuser=True):
                user.groups.add(group)
    except Exception as ex:
        print(ex)
        return


def null_safe_float_to_int(value):
    if pd.isnull(value):
        return None
    else:
        return int(value)

def null_safe_string(value):
    
    if pd.isnull(value):
        return None
    else:
        return str(value)


def success_json(mensaje=None, resp=None, url=None):
    data = {
        'result': 'ok',
        'redirected': bool(url)
    }
    if mensaje:
        data['mensaje'] = mensaje
    if resp:
        data['resp'] = resp
    if url:
        data['url'] = url
    return JsonResponse(data)


def bad_json(mensaje=None, error=None, form=None, extradata=None):
    data = {'result': 'error'}
    
    if mensaje:
        data['mensaje'] = mensaje

    error_messages = {
        0: "Solicitud incorrecta",
        1: "Error al guardar los datos",
        2: "Error al eliminar los datos"
    }
    
    if error is not None and error >= 0:
        data['mensaje'] = error_messages.get(error, data.get('mensaje', 'Error desconocido'))

    if extradata:
        data.update(extradata)
        
    return JsonResponse(data)

    
def error_json(mensaje=None, error=None, forms=[], extradata=None):
    data = {'result': 'error'}
    if mensaje:
        data['mensaje'] = mensaje
    try:
        if error and error >= 0:
            if error == 0:
                data['mensaje'] = "Solicitud incorrecta"
            elif error == 1:
                data['mensaje'] = "Error al guardar los datos"
            elif error == 2:
                data['mensaje'] = "Error al eliminar los datos"
        if extradata:
            data.update(extradata)

        if forms:
            errors = {}
            for form in forms:
                # Procesa los errores del formulario principal
                if form.errors:
                    for field, error_list in form.errors.items():
                        errors[field] = list(error_list)
                # Procesa los errores de los formsets inline
                for formset in getattr(form, 'inline_formsets', []):
                    for index, inline_form in enumerate(formset):
                        if inline_form.errors:
                            for field, error_list in inline_form.errors.items():
                                key = f"{formset.prefix}-{index}-{field}"
                                errors[key] = list(error_list)
            if errors:
                data['forms'] = errors
                if data['mensaje'] is None:
                    data['mensaje'] = "Hay errores en el formulario"

        return JsonResponse(data, status=400)
    except Exception as ex:
        return JsonResponse(data, status=400)
    

def get_query_params(request):
    
    if request.method == 'GET':
        action = request.GET.get('action', '')
        data = request.GET.dict()
        if 'action' in data:
            del data['action']
        return action, data
    elif request.method == 'POST':
        action = ""
        try:
            data = json.loads(request.body)
            if 'action' in data:
                if 'action' in data:
                    action = data['action']
                else:
                    action == None
            if action == None or action == "":
                try:
                    action = request.GET.get('action', '')    
                except Exception as e:
                    action = ""
        except:
            data = request.POST.dict()
            pass
        
        if action == "" or action == None:
            action = request.POST.get('action', None)  
           
        return action, data

def get_hace_tiempo(created):
    
    ahora = timezone.now()
    diferencia = ahora - created
    segundos = round(diferencia.total_seconds())
    minutos = math.floor(segundos / 60)
    horas = math.floor(minutos / 60)
    dias = math.floor(horas / 24)
    meses = math.floor(dias / 30)

    if meses == 1:
        return "hace un mes"
    elif meses > 1:
        return f"hace {meses} meses"
    elif dias == 1:
        return f"hace {dias} día"
    elif dias > 0:
        return f"hace {dias} días"
    elif horas == 1:
        return f"hace {horas} hora"
    elif horas > 0:
        return f"hace {horas} horas"
    elif minutos == 1:
        return f"hace {minutos} minuto"
    elif minutos > 0:
        return f"hace {minutos} minutos"
    else:
        return f"hace {segundos} segundos"
    
def get_tiempo_string(tiempo):
    horas = tiempo // 3600
    tiempo = tiempo % 3600
    minutos = tiempo // 60
    tiempo = tiempo % 60
    segundos = tiempo
    
    if horas > 0 and minutos > 0 and segundos > 0:
        return f"{horas} horas {minutos} minutos {segundos} segundos"
    if horas > 0 and minutos > 0 and segundos == 0:
        return f"{horas} horas {minutos} minutos"
    if horas > 0 and minutos == 0 and segundos > 0:
        return f"{horas} horas {segundos} segundos"
    if horas > 0 and minutos == 0 and segundos == 0:
        return f"{horas} horas"
    if horas == 0 and minutos > 0 and segundos > 0:
        return f"{minutos} minutos {segundos} segundos"
    if horas == 0 and minutos > 0 and segundos == 0:
        return f"{minutos} minutos"
    else:
        return f"{segundos} segundos"
    
def get_seconds_to_string(seconds): # Convert seconds to 20:10
    
    if seconds >= 3600:
        hours = seconds // 3600
        seconds = seconds % 3600
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{hours}:{minutes}:{seconds}"
    else:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds}"
    
def check_is_superuser(request):
    if request.user.is_superuser:
        return
    else:
        raise Http404("Página no encontrada")

def get_url_params(request, exclude=['pagina']):
    url_parameters = request.GET.copy()
    
    for param in exclude:
        if param in url_parameters:
            del url_parameters[param]
    
    return url_parameters.urlencode() 


def get_image_type(file_obj):
    """
    Retorna el tipo de imagen (por ejemplo, 'jpeg', 'png') a partir de un objeto de archivo.
    
    :param file_obj: objeto de archivo con método read()
    :return: cadena con el formato de la imagen en minúsculas, o None si no se pudo determinar.
    """
    data = file_obj.read()
    file_obj.seek(0)  # Reinicia el puntero para no afectar posteriores lecturas
    try:
        img = Image.open(io.BytesIO(data))
        return img.format.lower() if img.format else None
    except Exception:
        return None


def upload_image_to_firebase_storage(image, bucket_name=settings.FIREBASE_BUCKET_NAME, folder=settings.TINYMCE_IMAGES_FOLDER):
    print("Estamos cargando la imagen Firebase desde Imagen")
    try:
        from firebase_admin import storage
        bucket = storage.bucket(bucket_name)
        tipo_archivo = get_image_type(image)
        blob = bucket.blob(folder + "/" + str(bson.ObjectId()) + "." + tipo_archivo)
        image.seek(0)   # Pone el cursor al inicio del archivo
        content_type = image.content_type if hasattr(image, 'content_type') else "image/" + tipo_archivo

        blob.upload_from_file(image, content_type=content_type)
        blob.make_public()
        return blob.public_url
    except Exception as ex:
        print(ex)
        return None

    
def upload_url_image_to_firebase_storage(url, bucket_name=settings.FIREBASE_BUCKET_NAME, folder=settings.FIREBASE_IMAGES_FOLDER):
    print("Estamos cargando la imagen Firebase desde URL")
    try:
        from firebase_admin import storage
        bucket = storage.bucket(bucket_name)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.content
            tipo_archivo = get_image_type(io.BytesIO(content))
            blob = bucket.blob(folder + "/" + str(bson.ObjectId()) + "." + tipo_archivo)
            blob.upload_from_string(response.content, content_type=response.headers['content-type'])
            blob.make_public()
            return blob.public_url
        else:
            print(f"Error al obtener la imagen: {response.status_code}")
            return None
    except Exception as ex:
        print(ex)
        return None
    

def replace_images(html, bucket_name=settings.FIREBASE_BUCKET_NAME, folder=settings.TINYMCE_IMAGES_FOLDER):
    # bucket = storage.bucket("pre-online.appspot.com")
    bucket = storage.bucket(bucket_name)

    soup = BeautifulSoup(html, 'html.parser')
    for img in soup.find_all('img'):
        imagen = img['src']

        if not imagen.startswith('data:image'):
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                       'Referer': 'https://quizizz.com/admin/quiz/636186fc7c0111001dd1c409/adjectives?fromSearch=true&source=',
                       'Sec-Ch-Ua-Mobile': '?0',
                       'Sec-Ch-Ua': '" Not A;Brand";v="99", "Chromium";v="121", "Google Chrome";v="121"',
                       'Sec-Ch-Ua-Platform': '"Windows"',
                       'Connection': 'keep-alive',
                       'Accept-Encoding': 'gzip, deflate, br',
                       'Accept': '*/*',
                       }
            response = requests.get(imagen, headers=headers)

            if response.status_code == 200:
                content = response.content
                tipo_archivo = get_image_type(io.BytesIO(content))
                blob = bucket.blob(folder + "/" + str(bson.ObjectId()) + "." + tipo_archivo)
                blob.upload_from_string(response.content, content_type=response.headers['content-type'])
                blob.make_public()
                img['src'] = blob.public_url

                if "alt" in img.attrs:
                    img["alt"] = "Banco de preguntas"
                else:
                    img["alt"] = "Banco de preguntas"

        else :
            # Upload image to firebase storage
            imagen = imagen.replace('data:image/png;base64,', '')
            imagen = imagen.replace('data:image/jpeg;base64,', '')
            imagen = imagen.replace('data:image/jpg;base64,', '')
            imagen = imagen.replace('data:image/gif;base64,', '')
            imagen = imagen.replace('data:image/svg+xml;base64,', '')
            imagen = imagen.replace('data:image/webp;base64,', '')
            imagen = imagen.replace('data:image/bmp;base64,', '')
            imagen = imagen.replace('data:image/tiff;base64,', '')
            imagen = imagen.replace('data:image/vnd.microsoft.icon;base64,', '')
            imagen = imagen.replace('data:image/x-icon;base64,', '')
            imagen = imagen.replace('data:image/vnd.wap.wbmp;base64,', '')
            imagen = imagen.replace('data:image/x-xbitmap;base64,', '')
            imagen = imagen.replace('data:image/x-xbm;base64,', '')
            imagen = imagen.replace('data:image/x-win-bitmap;base64,', '')
            imagen = imagen.replace('data:image/x-windows-bmp;base64,', '')
            imagen = imagen.replace('data:image/x-ms-bmp;base64,', '')
            imagen = imagen.replace('data:image/bmp;base64,', '')
            imagen = imagen.replace('data:image/x-bmp;base64,', '')
            imagen = imagen.replace('data:image/x-bitmap;base64,', '')
            imagen = imagen.replace('data:image/x-xbitmap;base64,', '')
            imagen = imagen.replace('data:image/x-win-bitmap;base64,', '')

            imagen = imagen.encode('utf-8')
            imagen = base64.b64decode(imagen)

            blob = bucket.blob(folder + "/" + str(bson.ObjectId()))
            blob.upload_from_string(imagen, content_type="image/png")
            blob.make_public()
            img['src'] = blob.public_url

            if "alt" in img.attrs:
                img["alt"] = "Banco de preguntas"
            else:
                img["alt"] = "Banco de preguntas"

    return str(soup)


# *********************************************************************************
# Guardar errores de la aplicación
# *********************************************************************************
# Errores en la aplicacion
def save_error(request, exception, mensaje="Error general en la aplicación"):
    from .models import ErrorApp
    try:
        reporter = ExceptionReporter(request, *sys.exc_info())
        text = reporter.get_traceback_text()
        path = request.path
        url = request.META.get('HTTP_REFERER')
        user = request.user
        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('HTTP_X_REAL_IP')
        get = request.GET.dict()
        post = request.POST.dict()
        user_agent = request.META.get('HTTP_USER_AGENT')

        ErrorApp.objects.create(
            path=path if path is not None else "",
            error=text if text is not None else "",
            error_str=str(exception),
            mensaje=mensaje if mensaje is not None else "",
            url=url if url is not None else "",
            user=user if user.is_authenticated else None,
            ip=ip if ip is not None else "",
            get=get if get is not None else {},
            post=post if post is not None else {},
            user_agent=user_agent if user_agent is not None else "",
        )
        
    except Exception as ex:
        print(ex)
        return


def eliminar_imagenes(sender, instance, imagen_fields, delete=False):
    if not delete:
        try:
            if instance.pk:
                antigua_instancia = sender.objects.get(pk=instance.pk)
                i = 0
                for field in imagen_fields:
                    antigua_imagen = getattr(antigua_instancia, field)
                    nueva_imagen = getattr(instance, field)
                    if antigua_imagen and nueva_imagen != antigua_imagen:
                        if os.path.isfile(antigua_imagen.path):
                            os.remove(antigua_imagen.path)
                    i += 1
                    if i > 50: # Evita un bucle infinito
                        break
        except Exception as ex:
            print(ex)
    else:
        try:
            i = 0
            for field in imagen_fields:
                imagen = getattr(instance, field)
                if imagen:
                    if os.path.isfile(imagen.path):
                        os.remove(imagen.path)
                i += 1
                if i > 50: # Evita un bucle infinito
                    break
        except Exception as ex:
            print(ex)


def eliminar_parrafos_vacios(html):
    soup = BeautifulSoup(html, 'html.parser')
    while soup.p and (not soup.p.text.strip() and not soup.p.find('img')):
        soup.p.extract()

    while soup.p and (not soup.find_all('p')[-1].text.strip() and not soup.find_all('p')[-1].find('img')):
        soup.find_all('p')[-1].extract()
    cleaned_html = str(soup)
    cleaned_html = cleaned_html.lstrip('\n\r').rstrip('\n\r')

    if cleaned_html == "":
        cleaned_html = None
    return cleaned_html

def replace_quizziz_html(html):
    html = str(html)
    html = html.replace('font-medium', '')
    html = html.replace('font-semibold', 'fw-semibold')
    html = html.replace('font-bold', 'fw-bold')
    html = html.replace('font-light', 'fw-light')
    html = html.replace('font-regular', 'fw-regular')
    html = html.replace('font-italic', 'fs-italic')
    html = html.replace('font-normal', 'fs-normal')
    html = html.replace('font-small', 'fs-small')
    html = html.replace('font-medium', 'fs-medium')
    html = html.replace('font-large', 'fs-large')
    html = html.replace('font-xlarge', 'fs-xlarge')
    html = html.replace('color="dark.primary"', '')

    html = html.replace('<p class="fw-semibold"></p>', '')
    html = html.replace('<p></p>', '')
    html = html.replace('<!-- --><!-- --><!-- -->', '')
    html = html.replace('<!-- -->', '')

    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all('p'):
        for attr in list(tag.attrs):
            if attr.startswith('data-v-'):
                del tag[attr]

    for tag in soup.find_all('span'):
        for attr in list(tag.attrs):
            if attr.startswith('data-v-'):
                del tag[attr]

    for tag in soup.find_all('div'):
        for attr in list(tag.attrs):
            if attr.startswith('data-v-'):
                del tag[attr]

    for p_tag in soup.find_all('p', class_=lambda x: x and 'text-content-base' in x):
        div_tag = soup.new_tag('div')
        div_tag.attrs = p_tag.attrs  # Copiar los atributos del <p> al <div>
        
        while p_tag.contents:
            div_tag.append(p_tag.contents[0])

        p_tag.replace_with(div_tag)

    html = str(soup)
    html = html.replace('text-content-base ', '')
    return html

def get_redirect_url(request, object=None, action='edit'):
    """
    Genera la URL de redirección según los parámetros del formulario.

    :param request: Objeto HttpRequest
    :param form: Instancia del formulario
    :return: String con la URL de redirección
    """
    try:
        if '_addanother' in request.POST:
            return f'{request.path}?action=add'
        elif '_continue' in request.POST:
            if object and hasattr(object, 'instance'):
                return f'{request.path}?action={action}&id={object.instance.pk}'
            else:
                return f'{request.path}?action={action}&id={object.pk}'
        return request.path
    except Exception as ex:
        print(ex)
        return request.path


