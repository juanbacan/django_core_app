import requests, re
from threading import Thread
from django.conf import settings

def format_phone_number(phone: str) -> str:
    """
    Formatea un número telefónico al formato internacional:
    - Si el número se ingresa como '0967006785' (10 dígitos, con 0 al inicio) o '967006785' (9 dígitos),
      lo transforma a '593967006785'.
    - Si se ingresa como '5930967006785' (13 dígitos, con 0 de más luego del código de país),
      lo convierte a '593967006785'.
    - Si ya está en el formato correcto ('593967006785'), se devuelve sin cambios.
    
    Lanza ValueError si el número no se ajusta a ninguno de los formatos esperados.
    """
    # Eliminar cualquier carácter que no sea un dígito
    num = re.sub(r'\D', '', phone)

    # Caso 1: Número con 9 dígitos (falta el 0 al inicio)
    if len(num) == 9:
        num = "593" + num

    # Caso 2: Número con 10 dígitos que empieza con 0 (por ejemplo, 0967006785)
    elif len(num) == 10 and num.startswith("0"):
        num = "593" + num[1:]

    # Caso 3: Número con 13 dígitos que empieza con 5930 (por ejemplo, 5930967006785)
    elif len(num) == 13 and num.startswith("5930"):
        num = "593" + num[4:]

    # Caso 4: Número ya en formato correcto: 12 dígitos y empieza con 593
    elif len(num) == 12 and num.startswith("593"):
        pass  # No se necesita transformación

    else:
        raise ValueError(f"Formato o longitud inválida para el número: {phone}")

    # Validar que el número final tenga 12 dígitos
    if len(num) != 12:
        raise ValueError(f"El número formateado no tiene 12 dígitos: {num}")

    return num


def send_whatsapp_message(number: str, message: str):
    """
    Envía un mensaje a través de WhatsApp Business API.
    :param number: El número de teléfono al que se enviará el mensaje.
    :param message: El mensaje a enviar.
    """
    WHATSAPP_API_URL = settings.WHATSAPP_API_URL
    API_KEY = settings.WHATSAPP_API_KEY
    SESSION_NAME = settings.WHATSAPP_SESSION_NAME

    url = f"{WHATSAPP_API_URL}/send-message/{SESSION_NAME}"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    data = {
        "number": format_phone_number(number),
        "message": message
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Levanta un error si la respuesta no es 200
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error enviando mensaje a WhatsApp: {e}")
        return None
    

class WhatsappMessageThread(Thread):
    def __init__(self, number, message):
        self.number = number
        self.message = message
        Thread.__init__(self)
        
    def run(self):
        try:
            send_whatsapp_message(self.number, self.message)
        except Exception as ex:
            print(ex)
            pass

def send_whatsapp_message_thread(number: str, message: str):
    """
    Envía un mensaje a través de WhatsApp Business API en un hilo.
    :param number: El número de teléfono al que se enviará el mensaje.
    :param message: El mensaje a enviar.
    """
    WhatsappMessageThread(number, message).start()


class WhatsappBot:
    """
    Clase para interactuar con la API de WhatsApp (múltiples sesiones).
    Puedes crear una instancia de esta clase por cada 'session_name' que quieras usar,
    o manejarlo dinámicamente (crear, enviar, etc.).
    """
    def __init__(self):
        self.session_name = settings.WHATSAPP_SESSION_NAME
        self.base_url = settings.WHATSAPP_API_URL 
        self.api_key = settings.WHATSAPP_API_KEY  

    def create_session(self):
        """
        Llama al endpoint /create-session para crear/inicializar una sesión con 'session_name'.
        Si la sesión ya existe, el servidor podría dar un error 500 (o 400) indicando que ya existe.
        """
        url = f"{self.base_url}/create-session"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        data = {
            "sessionName": self.session_name
        }
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.json()
        except requests.RequestException as e:
            return {"status": False, "message": f"Error al crear sesión: {str(e)}"}

    def get_qr_code(self):
        """
        Obtiene el QR en base64 de la sesión actual (/get-qr/<sessionName>).
        Devuelve None si no existe o no está disponible.
        """
        url = f"{self.base_url}/get-qr/{self.session_name}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json().get("qr")
            else:
                return None
        except requests.RequestException as e:
            print(f"Error al obtener el código QR: {e}")
        return None

    def get_status(self):
        """
        Verifica si la sesión está conectada. 
        Retorna True/False o None si hay error.
        """
        url = f"{self.base_url}/status/{self.session_name}"
        headers = {
            "x-api-key": self.api_key
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "connected"
            else:
                return None
        except requests.RequestException as e:
            print(f"Error al verificar estado: {e}")
            return None

    def send_message(self, number, message=""):
        """
        Envía un mensaje de texto a 'number' a través de la sesión actual.
        POST /send-message/<sessionName>
        """
        if not number or not message:
            return {
                "status": False,
                "message": "Número y mensaje son requeridos para enviar un mensaje."
            }
        url = f"{self.base_url}/send-message/{self.session_name}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        data = {
            "number": format_phone_number(number),      # Asumimos que el servidor formatea, si no, agregas '@c.us'
            "message": message
        }
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.json()  # El servidor retorna su JSON con el status
        except requests.RequestException as e:
            print(f"Error al enviar el mensaje: {e}")
            return {"status": False, "message": f"Error al enviar el mensaje: {str(e)}"}

    def send_image(self, number, image_base64):
        """
        Envía una imagen en formato Base64 al número especificado en la sesión actual.
        POST /send-image/<sessionName>
        Recuerda que la ruta /send-image/:sessionName debe existir en tu servidor Node.
        """
        if not number or not image_base64:
            return {
                "status": False,
                "message": "Número e imagen (Base64) son requeridos."
            }
        url = f"{self.base_url}/send-image/{self.session_name}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        data = {
            "number": format_phone_number(number),
            "image": image_base64  # Debes asegurarte de enviar la cadena base64 válida
        }
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.json()
        except requests.RequestException as e:
            print(f"Error al enviar la imagen: {e}")
            return {"status": False, "message": f"Error al enviar la imagen: {str(e)}"}

    def disconnect(self):
        """
        Desconecta (logout) la sesión actual.
        POST /disconnect/<sessionName>
        """
        url = f"{self.base_url}/disconnect/{self.session_name}"
        headers = {
            "x-api-key": self.api_key
        }
        try:
            response = requests.post(url, headers=headers)
            return response.json()
        except requests.RequestException as e:
            print(f"Error al desconectar el bot de WhatsApp: {e}")
            return {"status": False, "message": f"Error al desconectar: {str(e)}"}