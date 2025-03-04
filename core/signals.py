import os

from django.db.models.signals import pre_save, pre_delete, post_save
from django.dispatch import receiver

from .models import AplicacionWeb
from .utils import eliminar_imagenes


@receiver(pre_save, sender=AplicacionWeb)
def pre_save_eliminar_imagen_antigua(sender, instance, **kwargs):
    eliminar_imagenes(sender, instance, ['logo', 'logo_horizontal', 'image_content', 'logo_webpush', 'social_images'])

@receiver(pre_delete, sender=AplicacionWeb)
def pre_delete_eliminar_imagen(sender, instance, **kwargs):
    eliminar_imagenes(sender, instance, ['logo', 'logo_horizontal', 'image_content', 'logo_webpush', 'social_images'], delete=True)

