import random, math, datetime
from bs4 import BeautifulSoup

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.html import escape


register = template.Library()

def callmethod(obj, methodname):
    method = getattr(obj, methodname)
    if "__callArg" in obj.__dict__:
        # if obj.__dict__.has_key("__callArg"):
        ret = method(*obj.__callArg)
        del obj.__callArg
        return ret
    return method()


def args(obj, arg):
    if not "__callArg" in obj.__dict__:
        # if not obj.__dict__.has_key("__callArg"):
        obj.__callArg = []
    obj.__callArg.append(arg)
    return obj


def to_char(value):
    return chr(64+value)

def seconds_to_string(seconds):
    if seconds >= 3600:
        hours = seconds // 3600
        seconds = seconds % 3600
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{hours}:{minutes}:{seconds}"
    else:
        minutes = seconds // 60
        seconds = seconds % 60
        
        if minutes < 10:
            minutes = f"0{minutes}"
        if seconds < 10:
            seconds = f"0{seconds}"
            
        return f"{minutes}:{seconds}"
    
def seconds_to_string2(seconds, total):
    tiempo = total - seconds
    return seconds_to_string(tiempo)
    
def add_class(field):
    # Check if it is a checkbox
    if field.field.widget.input_type == "checkbox":
        if "class" in field.field.widget.attrs:
            field.field.widget.attrs["class"] += " form-check-input"
        else:
            field.field.widget.attrs["class"] = "form-check-input"
    # Check if it is a select
    elif field.field.widget.input_type == "select":
        if "class" in field.field.widget.attrs:
            field.field.widget.attrs["class"] += " form-select"
        else:
            field.field.widget.attrs["class"] = "form-select"
    else:
        if "class" in field.field.widget.attrs:
            field.field.widget.attrs["class"] += " form-control"
        else:
            field.field.widget.attrs["class"] = "form-control"
    return field

@register.simple_tag
def num_question(page, num, questions = 5):
    return (page - 1) * questions + num
    

def get_minutes(seconds):
    minutes =  seconds // 60
    if minutes >= 10:
        return minutes
    else:
        return f"0{minutes}"

def get_seconds(seconds):
    seconds = seconds % 60
    if seconds >= 10:
        return seconds
    else:
        return f"0{seconds}"
    
@register.simple_tag
def random_number(a, b=None):
    if b is None:
        a, b = 0, a
    return random.randint(a, b)


def get_photo_user(user):
        if user.socialaccount_set.exists():
            social_account = user.socialaccount_set.first()
            return social_account.get_avatar_url()
        else:
            return None
        
def get_first_name(user):
    if user.first_name == "":
        return user.username
    return user.first_name


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
    
def get_nombre_completo(user):
    nombre = ""
    if user.first_name != "":
        nombre = user.first_name
    if user.last_name != "":
        nombre += f" {user.last_name}"
    if nombre == "":
        nombre = user.username
    return nombre

def string(value):
    return str(value)


@register.simple_tag
def avatar_small(usuario, width=40):
    photo = usuario.get_photo_user()
    avatar = f"border: solid 1px #b5b5b5; width:{width}px; height:{width}px; border-radius: 50%; object-fit: cover;"

    if photo:
        html = f'<div style="background-image: url({photo}); background-size: cover; {avatar}"></div>'
    else:
        font_size = width * 0.5  # Ajuste de tamaño de letra proporcional al tamaño del avatar
        initial = usuario.get_nombre_completo()[0].upper()
        html = f'<div class="bg-lightgray d-flex justify-content-center align-items-center" style="{avatar}; font-size:{font_size}px;">{initial}</div>'
    
    return mark_safe(html)  


@register.simple_tag
def custom_avatar_small(content, background="bg-lightgray", color="text-dark"):
    html = f'<div class="avatar {background} {color} d-flex justify-content-center align-items-center h2">{content}</div>'
    return mark_safe(html)   


# Función para agregar un filtro a la url, por ejemplo, si se quiere agregar el filtro pagina
# con el valor 2, se debe pasar como parámetro "pagina,2"
@register.simple_tag
def filter_url(url, filter, value, exclude="pagina,kword"):
    exclude = exclude.split(",")
    url_paremeters = url.split("?")
    if len(url_paremeters) > 1:
        url = url_paremeters[0]
        parameters = url_paremeters[1].split("&")

        for parameter in parameters[:]:  # Creamos una copia de la lista
            for exc in exclude:
                if parameter.startswith(exc):
                    parameters.remove(parameter)
                    break
        for i, parameter in enumerate(parameters):
            if parameter.startswith(filter):
                parameters[i] = f"{filter}={value}"
                break
        # Chequear si filter ya existe en los parametros
        if f"{filter}={value}" not in parameters:
            parameters.append(f"{filter}={value}")

        url_final = f"{url}?{'&'.join(parameters)}"
        return url_final
    else:
        url_final = f"{url}?{filter}={value}"
        return url_final


# Función para excluir un filtro de la url, por ejemplo, si se quiere excluir el filtro pagina
# y kword, se debe pasar como parámetro "pagina,kword"
@register.simple_tag
def exclude_filter_url(url, exclude="pagina,kword"):
    # Split exclude by comma
    exclude = exclude.split(",")
    url_paremeters = url.split("?")
    if len(url_paremeters) > 1:
        url = url_paremeters[0]
        parameters = url_paremeters[1].split("&")
        # Eliminar los parametros que se quieren excluir
        for parameter in parameters[:]:  # Creamos una copia de la lista
            for ex in exclude:
                if parameter.startswith(ex):
                    parameters.remove(parameter)
                    break

        url_final = f"{url}?{'&'.join(parameters)}"
        return url_final
    else:
        return url
    

@register.filter(expects_localtime=True)
def fecha_con_mes(fecha):
    meses = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    if isinstance(fecha, datetime.date):
        return f"{fecha.day} de {meses[fecha.month - 1]}"
    return fecha


@register.simple_tag
def descripcion_corta(html, longitud=130):
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text()
    if len(texto) > longitud:
        return f"{texto[:longitud]}..."
    return texto


@register.simple_tag
def descripcion(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()


@register.simple_tag
def avatar_small(usuario, width=40):
    photo = usuario.get_photo_user()
    avatar = f"border: solid 1px #b5b5b5; width:{width}px; height:{width}px; border-radius: 50%; object-fit: cover;"

    if photo:
        html = f'<div style="background-image: url({photo}); background-size: cover; {avatar}"></div>'
    else:
        html = f'<div class="bg-lightgray d-flex justify-content-center align-items-center h2" style="{avatar}">{usuario.get_nombre_completo()[0]}</div>'
    return mark_safe(html)


@register.simple_tag
def avatar_img(url, width=40, padding=5, extra_styles="", html_attrs=""):
    """
    Generate an HTML div element with an image inside for an avatar, centered with padding.
    
    :param url: The URL of the avatar image.
    :param width: The width and height of the avatar in pixels. Default is 40px.
    :param padding: The padding around the image in pixels. Default is 5px.
    :param extra_styles: Additional CSS styles to apply to the div.
    :param html_attrs: Additional HTML attributes to include in the div.
    :return: A safe HTML string containing the div element with an image inside.
    """
    # Escape the URL to prevent injection attacks
    escaped_url = escape(url)
    
    # Calculate the inner width and height considering padding
    inner_width = width - 2 * padding
    
    # Create the base style for the outer container
    outer_styles = (
        f"display: inline-block; "
        f"width: {width}px; "
        f"min-width: {width}px; "
        f"height: {width}px; "
        f"padding: {padding}px; "
        f"border: solid 1px #b5b5b5; "
        f"border-radius: 50%; "
        f"box-sizing: border-box; "
        f"overflow: hidden; "
        f"background-color: #f9f9f9; "
        f"{extra_styles}"
    )
    
    # Create the base style for the inner image
    inner_styles = (
        f"width: {inner_width}px; "
        f"height: {inner_width}px; "
        f"object-fit: cover;"
    )
    
    # Construct the HTML element
    html = (
        f'<div style="{outer_styles}" {html_attrs}>'
            f'<img src="{escaped_url}" style="{inner_styles}" alt="Avatar" />'
        f'</div>'
    )
    
    return mark_safe(html)
  

@register.simple_tag
def custom_avatar_small(content, background="bg-lightgray", color="text-dark"):
    html = f'<div class="avatar {background} {color} d-flex justify-content-center align-items-center h2">{content}</div>'
    return mark_safe(html)  


@register.simple_tag
def wrap_images(html):
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        if img.parent.name == "a" and img.parent.parent.name == "div" and "simmplelightbox" in img.parent.parent.get("class", []):
            continue

        src = img.get("src")
        new_wrapper = soup.new_tag("div", **{"class": "simmplelightbox"})
        link = soup.new_tag("a", href=src)
        img.wrap(link)
        link.wrap(new_wrapper)
        img.insert_after("\n")  # Opcional: para mantener formato

    return str(soup)


register.filter("call", callmethod)
register.filter("args", args)
register.filter("to_char", to_char)
register.filter("time_to_string", seconds_to_string)
register.filter("time_to_string2", seconds_to_string2)
register.filter("add_class", add_class)
register.filter("num_question", num_question)
register.filter("get_minutes", get_minutes)
register.filter("get_seconds", get_seconds)
register.filter("get_photo_user", get_photo_user)
register.filter("get_first_name", get_first_name)
register.filter("get_hace_tiempo", get_hace_tiempo)
register.filter("get_nombre_completo", get_nombre_completo)
register.filter("string", string)
register.filter("filter_url", filter_url)
register.filter("exclude_filter_url", exclude_filter_url)
register.filter("fecha_con_mes", fecha_con_mes)
register.filter("descripcion_corta", descripcion_corta)
register.filter("descripcion", descripcion)
register.filter("wrap_images", wrap_images)