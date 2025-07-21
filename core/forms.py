from django import forms
from django.utils.safestring import mark_safe
from tinymce.widgets import TinyMCE
from dal_select2.widgets import ModelSelect2, Select2, Select2Multiple, ModelSelect2Multiple

from core.crud_registry import crud_registry
from core.widgets import IconPickerWidget

class BootstrapFieldsMixin:
    """
    Mixin para configurar automáticamente los campos de un formulario,
    agregando estilos de Bootstrap y otras personalizaciones.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.is_bound:
            return

        if hasattr(self.__class__, 'prepopulated_fields'):
            self.prepopulated_fields = self.__class__.prepopulated_fields

        for field_name, field in self.fields.items():
            self.configure_field(field)

        for field_name in self.fields:
            if field_name == 'DELETE':
                continue
            if self.errors.get(field_name):
                self.fields[field_name].widget.attrs.setdefault('autofocus', '')
                break

        # Si el formulario define fieldsets, precomputamos los bound fields
        if hasattr(self, 'fieldsets'):
            self.fieldset_bound = []
            for title, options in self.fieldsets:
                # Obtenemos la lista de nombres de campos definidos en el fieldset
                field_names = options.get('fields', [])
                # Creamos una lista con los bound fields, comprobando que existan en self.fields
                bound_fields = [self[field_name] for field_name in field_names if field_name in self.fields]
                self.fieldset_bound.append((title, bound_fields))

    def configure_field(self, field):
        # Aplica automáticamente DateInput en los DateField
        if isinstance(field, forms.DateField):
            field.widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
            if field.initial and isinstance(field.initial, (str, int, float)) == False:
                field.initial = field.initial.strftime('%Y-%m-%d')
                
        excluded_widgets = (TinyMCE, Select2, Select2Multiple, ModelSelect2, ModelSelect2Multiple)
        if not isinstance(field.widget, excluded_widgets):
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += " form-control"
            else:
                field.widget.attrs["class"] = "form-control"

            # Check if field.widget has input_type attribute
            if hasattr(field.widget, "input_type"):
                if field.widget.input_type == "checkbox":
                    field.widget.attrs["class"] = field.widget.attrs["class"].replace("form-control", "form-check-input")
                elif field.widget.input_type == "select":
                    field.widget.attrs["class"] += " form-select"
                elif field.widget.input_type == "radio":
                    field.widget.attrs["class"] = field.widget.attrs["class"].replace("form-control", "form-check-input")
                    
            if "validate" in field.widget.attrs:
                validation_attrs = self.get_validation_attrs(field.widget.attrs["validate"])
                field.widget.attrs.update(validation_attrs)
        
        if field.required and hasattr(field, 'label') and field.label:
            field.label = mark_safe(field.label + '<span class="text-danger">*</span> ')

        # Si el campo usa el widget IconPickerWidget, establecer iconpicker en True
        if isinstance(field.widget, IconPickerWidget):
            self.iconpicker = True

        # Detectar ForeignKey y agregar URL para "Agregar"
        if hasattr(field, 'queryset') and getattr(field, 'queryset', None):
            model = getattr(field.queryset, 'model', None)
            if model and model in crud_registry:
                fk_conf = crud_registry[model]
                field.widget.attrs['fk_add_url'] = f"{fk_conf['url']}?action=add"


    def get_validation_attrs(self, validation_type):
        validation_attrs = {}
        if validation_type == "telefono_movil":
            validation_attrs['pattern'] = "[0]{1}[9]{1}[0-9]{8}"
            validation_attrs['validate'] = "Núm. móvil incorrecto. Ejm: 0987654321"
        elif validation_type == "telefono_fijo":
            validation_attrs['pattern'] = "[0]{1}[2-8]{1}[0-9]{7}"
            validation_attrs['validate'] = "Núm. fijo incorrecto. Ejm: 022345678"
        elif validation_type == "cedula":
            validation_attrs['pattern'] = "[0-9]{10}"
            validation_attrs['validate'] = "La cédula debe tener 10 dígitos"
        elif validation_type == "email":
            validation_attrs['pattern'] = "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"
            validation_attrs['validate'] = "Correo electrónico incorrecto."
        return validation_attrs


class BaseForm(BootstrapFieldsMixin, forms.Form):
    pass


class ModelBaseForm(BootstrapFieldsMixin, forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        if hasattr(self.__class__, 'inlines'):
            """
            Al inicializar el formulario, se instancian los formsets para cada inline
            definido en la propiedad "inlines" y se asignan a self.inline_formsets.
            """
            super(ModelBaseForm, self).__init__(*args, **kwargs)
            data = kwargs.get('data')
            files = kwargs.get('files')

            if data is None and len(args) > 0:
                data = args[0]
            if files is None and len(args) > 1:
                files = args[1]

            self.inline_formsets = []
            parent_instance =  self.instance if self.instance.pk else self.Meta.model()
            for inline in self.inlines:
                formset = inline.get_formset(parent_instance=parent_instance, data=data, files=files)
                self.inline_formsets.append(formset)
                
        else:
            super(ModelBaseForm, self).__init__(*args, **kwargs)


    def is_valid(self):
        valid = super(ModelBaseForm, self).is_valid()
        for formset in getattr(self, 'inline_formsets', []):
            if not formset.is_valid():
                valid = False
        return valid

    def save(self, commit=True):
        instance = super(ModelBaseForm, self).save(commit=commit)
        for formset in getattr(self, 'inline_formsets', []):
            if formset.is_valid():
                for form in formset:
                    print("Campos del formulario:", list(form.fields.keys()))
                formset.instance = instance
                formset.save()
        return instance
    
    @property
    def media(self):
        media = super().media
        for formset in getattr(self, 'inline_formsets', []):
            media += formset.media
        return media



class BaseInline:
    """
    Clase base para definir un inline.
    Debe definirse:
      - model: el modelo relacionado (por ejemplo, Comment)
      - form: el ModelForm a utilizar para el inline. Si no se proporciona, se generará uno automáticamente.
      - extra: número de formularios extra (por defecto 1)
      - can_delete: si se permite marcar para eliminar (por defecto True)
      - prefix: prefijo para el formset (opcional)
      - verbose_name: nombre singular del inline (opcional)
      - verbose_name_plural: nombre plural del inline (opcional)
    """
    model = None
    form = None
    extra = 1
    can_delete = True
    prefix = None
    verbose_name = None
    verbose_name_plural = None
    fields = None

    def get_formset(self, parent_instance, data=None, files=None, **kwargs):
        parent_model = parent_instance.__class__
        formset_params = {
            "parent_model": parent_model,
            "model": self.model,
            "extra": self.extra,
            "can_delete": self.can_delete,
        }
        
        if self.form is not None:
            if not hasattr(self.form, 'Meta') or not hasattr(self.form.Meta, 'model'):
                raise ValueError("El formulario proporcionado debe tener un 'Meta' con 'model' especificado.")
            
            # Si el formulario tiene un modelo especificado en su Meta, actualizamos formset_params
            form_model = self.form.Meta.model
            if form_model is not None:
                formset_params["model"] = form_model
            
            # Pasar el formulario al formset
            formset_params["form"] = self.form
            
        else:
            # Si no se proporciona un formulario, se genera uno automáticamente
            BootstrapInlineForm = type(
                "BootstrapInlineForm",
                (BootstrapFieldsMixin, forms.ModelForm),
                {"Meta": type("Meta", (), {"model": self.model, "fields": self.fields})}
            )
            formset_params["form"] = BootstrapInlineForm

        # Generar el FormSet con el modelo adecuado
        FormSet = forms.inlineformset_factory(**formset_params)
        
        # Crear instancia del FormSet
        formset_instance = FormSet(instance=parent_instance, data=data, files=files, prefix=self.prefix, **kwargs)

        # Asignar verbose_name y verbose_name_plural al formset_instance
        formset_instance.verbose_name = self.verbose_name or self.model._meta.verbose_name
        formset_instance.verbose_name_plural = self.verbose_name_plural or self.model._meta.verbose_name_plural

        return formset_instance