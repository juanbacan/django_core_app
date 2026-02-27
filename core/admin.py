from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.contrib import admin
from django import forms

from tinymce.widgets import TinyMCE

from .models import CustomUser, AplicacionWeb, Alerta, EmailCredentials, ErrorApp, CorreoTemplate, \
    LlamadoAccion, Modulo, GrupoModulo, AgrupacionModulo, CredencialesAPI

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name')
    search_fields = ('username', 'first_name', 'last_name', 'id', 'email')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(AplicacionWeb)


class AlertaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'descripcion', 'activo')

admin.site.register(Alerta, AlertaAdmin)

admin.site.register(EmailCredentials)


class ErrorAppAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    readonly_fields = ('created_by',)

admin.site.register(ErrorApp, ErrorAppAdmin)
admin.site.register(CorreoTemplate)

admin.site.register(LlamadoAccion)


class FlatPageForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    class Meta:
        model = FlatPage
        fields = '__all__'


class PageAdmin(FlatPageAdmin):
    """
    Page Admin
    """
    form = FlatPageForm


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, PageAdmin)

admin.site.register(Modulo)
admin.site.register(GrupoModulo)
admin.site.register(AgrupacionModulo)


class CredencialesAPIAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'modified_at')
    readonly_fields = ('created_by', 'modified_by', 'created_at', 'modified_at')
    
    fieldsets = (
        ('Facebook', {
            'fields': ('facebook_page_id', 'facebook_token'),
            'classes': ('collapse',),
        }),
        ('Telegram', {
            'fields': ('telegram_bot_token', 'telegram_default_chat_id'),
            'classes': ('collapse',),
        }),
        ('WhatsApp - Evolution API', {
            'fields': (
                'evolution_api_url',
                'evolution_api_key',
                'evolution_instance_id',
                'evolution_instance_token',
                'evolution_channels'
            ),
            'classes': ('collapse',),
        }),
        ('Información de Registro', {
            'fields': ('created_by', 'modified_by', 'created_at', 'modified_at'),
            'classes': ('collapse',),
        }),
    )

admin.site.register(CredencialesAPI, CredencialesAPIAdmin)