from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.contrib import admin
from django import forms
import csv
import json
from io import StringIO
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render
from django.contrib import messages

from tinymce.widgets import TinyMCE
from allauth.account.models import EmailAddress

from .models import CustomUser, AplicacionWeb, Alerta, EmailCredentials, ErrorApp, CorreoTemplate, \
    LlamadoAccion, Modulo, GrupoModulo, AgrupacionModulo, CredencialesAPI


class PremiumFilter(admin.SimpleListFilter):
    """Filtro personalizado para usuarios premium"""
    title = 'Estado Premium'
    parameter_name = 'premium'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Premium'),
            ('0', 'No Premium'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(premium=True)
        if self.value() == '0':
            return queryset.filter(premium=False)
        return queryset


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'premium_display')
    search_fields = ('username', 'first_name', 'last_name', 'id', 'email')
    list_filter = (PremiumFilter, 'is_active', 'is_staff')
    actions = ['import_users_from_csv']
    change_list_template = 'admin/custom_user_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='customuser_import_csv'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        """Vista para mostrar el formulario de importación de CSV"""
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            try:
                # Decodificar el archivo
                decoded_file = csv_file.read().decode('utf-8')
                reader = csv.DictReader(StringIO(decoded_file))
                
                if not reader.fieldnames or 'email' not in reader.fieldnames:
                    messages.error(request, 'El archivo CSV debe contener la columna "email"')
                    return render(request, 'admin/import_csv.html', {
                        'error': 'El archivo CSV debe contener la columna "email"'
                    })
                
                created = 0
                updated = 0
                errors = []
                row_num = 1
                
                for row_num, row in enumerate(reader, start=2):  # start=2 porque row 1 es header
                    try:
                        email = row.get('email', '').strip()
                        name = row.get('name', '').strip()
                        attributes_str = row.get('attributes', '{}').strip()
                        
                        if not email:
                            errors.append(f"Fila {row_num}: Email requerido")
                            continue
                        
                        # Validar formato de email
                        if '@' not in email:
                            errors.append(f"Fila {row_num}: Email inválido")
                            continue
                        
                        # Parsear los atributos JSON
                        attributes = {}
                        if attributes_str and attributes_str != '{}':
                            try:
                                attributes = json.loads(attributes_str)
                                if not isinstance(attributes, dict):
                                    errors.append(f"Fila {row_num}: Atributos deben ser un objeto JSON")
                                    continue
                            except json.JSONDecodeError as je:
                                errors.append(f"Fila {row_num}: JSON inválido - {str(je)}")
                                continue
                        
                        # Crear o actualizar usuario
                        username = email.split('@')[0]
                        user, user_created = CustomUser.objects.get_or_create(
                            email=email,
                            defaults={
                                'username': username,
                                'first_name': name.split()[0] if name else '',
                                'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                            }
                        )
                        
                        if not user_created:
                            # Actualizar el usuario existente
                            if name:
                                parts = name.split()
                                user.first_name = parts[0]
                                user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
                                user.save()
                        
                        # Crear o actualizar EmailAddress
                        email_address, email_created = EmailAddress.objects.get_or_create(
                            user=user,
                            email=email,
                            defaults={
                                'verified': True,
                                'primary': True,
                            }
                        )
                        
                        # Nota sobre atributos: 
                        # Los atributos JSON se procesan pero allauth.account.models.EmailAddress 
                        # no tiene un campo dedicado por defecto. 
                        # Considere crear un modelo de extensión o usar cache/signals para guardar atributos adicionales.
                        # Ejemplo:
                        # from django.core.cache import cache
                        # cache.set(f'user_attributes_{user.id}_{email}', attributes, timeout=None)
                        
                        if user_created:
                            created += 1
                        else:
                            updated += 1
                            
                    except Exception as e:
                        errors.append(f"Fila {row_num}: Error inesperado - {str(e)}")
                
                # Mostrar resultados
                context = {
                    'created': created,
                    'updated': updated,
                    'errors': errors,
                    'total_rows': row_num - 1 if row_num > 1 else 0,
                }
                
                if created > 0:
                    messages.success(request, f"✅ {created} usuarios creados exitosamente")
                if updated > 0:
                    messages.success(request, f"✅ {updated} usuarios actualizados exitosamente")
                
                if errors:
                    for error in errors[:10]:  # Mostrar máximo 10 errores
                        messages.warning(request, error)
                    if len(errors) > 10:
                        messages.warning(request, f"⚠️ ... y {len(errors) - 10} errores más")
                
                return render(request, 'admin/import_csv.html', context)
                
            except UnicodeDecodeError:
                messages.error(request, "Error: El archivo debe estar en formato UTF-8")
                return render(request, 'admin/import_csv.html', {
                    'error': 'El archivo debe estar codificado en UTF-8'
                })
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
                return render(request, 'admin/import_csv.html', {'error': str(e)})
        
        return render(request, 'admin/import_csv.html')

    def premium_display(self, obj):
        """Muestra si el usuario es premium"""
        if obj.premium:
            return '✅'
        return '❌'
    premium_display.short_description = 'Premium'

    def import_users_from_csv(self, request, queryset):
        """Acción para acceder al formulario de importación"""
        return HttpResponse("Use the Import CSV option from the admin menu")
    import_users_from_csv.short_description = "Importar usuarios desde CSV"


admin.site.register(CustomUser, CustomUserAdmin)


class EmailAddressPremiumFilter(admin.SimpleListFilter):
    """Filtro personalizado para emails de usuarios premium"""
    title = 'Usuario Premium'
    parameter_name = 'user__premium'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Premium'),
            ('0', 'No Premium'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(user__premium=True)
        if self.value() == '0':
            return queryset.filter(user__premium=False)
        return queryset


class EmailAddressAdmin(admin.ModelAdmin):
    """Admin personalizado para EmailAddress con filtro de premium"""
    list_display = ('email', 'user_name', 'user_premium', 'verified', 'primary', 'user_email')
    search_fields = ('email', 'user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = (EmailAddressPremiumFilter, 'verified', 'primary')
    readonly_fields = ('created_by', 'modified_by', 'created_at', 'modified_at') if hasattr(EmailAddress, 'created_by') else ()
    actions = ['export_emails_to_csv']
    
    def user_name(self, obj):
        """Muestra el nombre del usuario asociado"""
        return obj.user.get_nombre_completo() if hasattr(obj.user, 'get_nombre_completo') else f"{obj.user.first_name} {obj.user.last_name}"
    user_name.short_description = 'Nombre del Usuario'
    
    def user_premium(self, obj):
        """Muestra si el usuario es premium"""
        if obj.user.premium:
            return '✅'
        return '❌'
    user_premium.short_description = 'Premium'
        
    def user_email(self, obj):
        """Muestra el email alternativo del usuario si existe"""
        return obj.user.email if obj.user.email else '(sin email)'
    user_email.short_description = 'Email Usuario'

    def export_emails_to_csv(self, request, queryset):
        """Exporta los emails seleccionados a CSV en formato importable"""
        import datetime
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f'correos_electrónicos_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Encabezados - Mismo formato que importación
        writer.writerow(['email', 'name', 'attributes'])
        
        # Datos
        for email_address in queryset:
            # Obtener nombre del usuario
            if hasattr(email_address.user, 'get_nombre_completo'):
                name = email_address.user.get_nombre_completo()
            else:
                name = f"{email_address.user.first_name} {email_address.user.last_name}".strip()
            
            # Crear atributos JSON con información del usuario
            attributes = {
                'premium': email_address.user.premium,
                'verified': email_address.verified,
                'primary': email_address.primary,
                'user_email': email_address.user.email if email_address.user.email else None,
            }
            
            writer.writerow([
                email_address.email,
                name,
                json.dumps(attributes),
            ])
        
        return response
    export_emails_to_csv.short_description = "📥 Descargar correos seleccionados como CSV"


# Desregistrar EmailAddress si ya estaba registrado (allauth puede tenerlo)
try:
    admin.site.unregister(EmailAddress)
except admin.sites.NotRegistered:
    pass

# Registrar con el nuevo admin personalizado
admin.site.register(EmailAddress, EmailAddressAdmin)

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
    list_display = ('id', 'estado_facebook', 'estado_telegram', 'estado_whatsapp')
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
    
    def estado_facebook(self, obj):
        if obj.facebook_page_id and obj.facebook_token:
            return "✅ Configurado"
        return "❌ No configurado"
    estado_facebook.short_description = "ESTADO FACEBOOK"
    
    def estado_telegram(self, obj):
        if obj.telegram_bot_token and obj.telegram_default_chat_id:
            return "✅ Configurado"
        return "❌ No configurado"
    estado_telegram.short_description = "ESTADO TELEGRAM"
    
    def estado_whatsapp(self, obj):
        if obj.evolution_api_url and obj.evolution_api_key and obj.evolution_instance_id:
            return "✅ Configurado"
        return "❌ No configurado"
    estado_whatsapp.short_description = "ESTADO WHATSAPP"

admin.site.register(CredencialesAPI, CredencialesAPIAdmin)