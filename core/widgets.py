from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy

class ModalForeignKeyWidget(forms.Widget):
    template_name = "core/widgets/modal_foreignkey.html"

    def __init__(self, model, *, lookup_url=None,
                 display_attr="__str__", attrs=None,
                 list_display=None, search_fields=None, list_filter=None):
        
        super().__init__(attrs or {})
        self.model = model
        self.display_attr = display_attr
        self.lookup_url = lookup_url or reverse_lazy("core:modal-fk-lookup", args=[model._meta.label_lower])

        self.list_display  = list_display  or ["__str__"]
        self.search_fields = search_fields or ["__str__"]
        self.list_filter   = list_filter   or []

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        instance = None
        if value:
            try:
                instance = self.model.objects.get(pk=value)
            except self.model.DoesNotExist:
                pass

        ctx["widget"].update({
            "lookup_url": self.lookup_url,
            "display": getattr(instance, self.display_attr) if instance else "",
            "raw_id": value or "",
            "list_display": ",".join(self.list_display),
            "search_fields": ",".join(self.search_fields),
            "list_filter": ",".join(self.list_filter),
        })

        return ctx
    

class IconPickerWidget(forms.Widget):
    template_name = "core/widgets/iconpicker.html"

    def __init__(self, attrs=None):
        default_attrs = {'class': 'iconpicker-input iconpicker', 'autocomplete': 'off'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['icon_value'] = value or ''
        context['field_name'] = name
        return context


class DropifyWidget(forms.ClearableFileInput):
    template_name = "core/widgets/dropify_simple.html"

    def __init__(self, attrs=None, allowed_extensions=None, messages=None, height=200):
        default_attrs = {'class': 'dropify dropify-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
        
        # Extensiones permitidas por defecto para imágenes
        self.allowed_extensions = allowed_extensions or ['webp', 'png', 'jpg', 'jpeg']
        
        # Altura del widget
        self.height = height
        
        # Mensajes personalizables
        self.messages = messages or {
            'default': 'Arrastra aquí el archivo o haz clic para seleccionarlo',
            'replace': 'Arrastra aquí el archivo o haz clic para reemplazarlo',
            'remove': 'Eliminar',
            'error': '¡Uy! Algo salió mal.'
        }


    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'allowed_extensions': self.allowed_extensions,
            'messages': self.messages,
            'current_file': value if value else None,
            'field_name': name,
            'height': self.height
        })
        return context

    class Media:
        css = {
            'all': ('dropify/dropify.min.css', 'core/widgets/dropify/dropify-widget.css')
        }
        js = ('dropify/dropify.min.js', 'core/widgets/dropify/dropify-widget.js')


