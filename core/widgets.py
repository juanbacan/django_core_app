from django import forms
from django.utils.safestring import mark_safe

class ModalForeignKeyWidget(forms.Widget):
    """
    Widget genérico para campos ForeignKey con búsqueda por modal.
    Renderiza:
      - input visible (readonly)
      - input hidden (ID real)
      - botón que abre un modal
    """

    template_name = "core/widgets/modal_foreignkey.html"

    def __init__(self, modal_id, display_attr="__str__", attrs=None):
        self.modal_id = modal_id
        self.display_attr = display_attr
        super().__init__(attrs or {})

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        display_text = ""
        raw_id = value
        if value:
            try:
                if hasattr(value, self.display_attr):
                    display_text = getattr(value, self.display_attr)
                elif self.display_attr == "__str__":
                    display_text = str(value)
                raw_id = getattr(value, "id", value)
            except Exception:
                pass

        context.update({
            "modal_id": self.modal_id,
            "display_value": display_text,
            "value": raw_id,
            "field_name": name
        })
        return context

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


