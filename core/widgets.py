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


