from threading import Thread

from django.core.mail import EmailMessage
from django.db import transaction

from applications.core.models import EmailCredentials, AplicacionWeb
from django.core.mail.backends.smtp import EmailBackend

def get_next_email():
    with transaction.atomic():
        current_active = EmailCredentials.objects.filter(activo=True).first()
        
        if current_active:
            current_active.activo = False
            current_active.save()
            next_account = EmailCredentials.objects.filter(id__gt=current_active.id).order_by('id').first()
        else:
            next_account = EmailCredentials.objects.order_by('id').first()

        if not next_account:
            next_account = EmailCredentials.objects.order_by('id').first()

        if not next_account.activo:
            next_account.activo = True
            next_account.save()

        return next_account

def send_email(subject, body, to):
    email_credentials = get_next_email()
    if email_credentials is None:
        print("No hay cuentas de correo disponibles")
        return
    try:
        backend = EmailBackend(
            host=email_credentials.host,
            port=email_credentials.port,
            username=email_credentials.username,
            password=email_credentials.password,
            use_tls=email_credentials.use_tls,
            use_ssl=email_credentials.use_ssl
        )
        if isinstance(to, list):
            to_final = to
        else:
            to_final = [to]

        application = AplicacionWeb.objects.first()
        titulo = application.titulo_sitio

        email = EmailMessage(
            subject,
            body,
            f'{titulo} <{email_credentials.username}>',
            to_final,
            connection=backend
        )
        email.content_subtype = "html"
        email.send()
        email_credentials.conteo += 1
        email_credentials.save()

    except Exception as ex:
        print(f"Error al enviar el correo: {ex}")


class GroupEmailThread(Thread):
    def __init__(self, subject, body, to):
        self.subject = subject
        self.body = body
        self.to = to
        Thread.__init__(self)
        
    def run(self):
        try:
            send_email(self.subject, self.body, self.to)
        except Exception as ex:
            print(ex)
            pass

# ************************************************************************************************
# Funciones
# ************************************************************************************************
def send_email_thread(subject, body, to):
    """
    Envía un correo electrónico en un hilo.
    :param subject: El asunto del correo.
    :param body: El cuerpo del correo.
    :param to: El destinatario del correo
    """
    GroupEmailThread(subject, body, to).start()
    return
