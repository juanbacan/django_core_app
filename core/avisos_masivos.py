from django.db.models import Q
from django.utils import timezone

from .models import AvisoMasivo, AvisoMasivoLectura


def avisos_masivos_vigentes_qs():
    now = timezone.now()
    return AvisoMasivo.objects.filter(
        activo=True,
        publicado_en__isnull=False,
        publicado_en__lte=now,
    ).filter(
        Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=now)
    )


def avisos_masivos_pendientes_para_usuario(user):
    if not user or not user.is_authenticated:
        return AvisoMasivo.objects.none()
    v = avisos_masivos_vigentes_qs()
    leido_ids = list(
        AvisoMasivoLectura.objects.filter(usuario=user).values_list(
            'aviso_id', flat=True
        )
    )
    if not leido_ids:
        return v
    return v.exclude(id__in=leido_ids)


def contar_pendientes_avisos_masivos(user):
    return avisos_masivos_pendientes_para_usuario(user).count()


def marcar_todos_avisos_masivos_vistos(user):
    if not user or not user.is_authenticated:
        return 0
    # get_or_create por fila: fiable en cualquier motor y con concurrencia
    n = 0
    for aviso in avisos_masivos_pendientes_para_usuario(user).iterator():
        AvisoMasivoLectura.objects.get_or_create(aviso=aviso, usuario=user)
        n += 1
    return n
