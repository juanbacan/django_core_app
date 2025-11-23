"""
Sistema de Layout para Formularios - Similar a crispy-forms
Permite controlar completamente la estructura y presentación de formularios.

Uso básico:
    from core.layout import Layout, Row, Column, Field, Fieldset, HTML

    class MiFormulario(ModelBaseForm):
        class Meta:
            model = MiModelo
            fields = '__all__'
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.helper = FormHelper()
            self.helper.layout = Layout(
                Row(
                    Column('nombre', css_class='col-md-6'),
                    Column('apellido', css_class='col-md-6'),
                ),
                Fieldset(
                    'Dirección',
                    'calle',
                    'ciudad',
                ),
                Field('email', css_class='form-control-lg'),
                HTML('<hr>'),
                'descripcion',
            )
"""

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class LayoutObject:
    """Clase base para todos los objetos de layout"""
    
    def render(self, form, context=None):
        """Renderiza el objeto de layout"""
        raise NotImplementedError("Cada objeto de layout debe implementar render()")


class FormHelper:
    """
    Ayudante principal para configurar el layout y comportamiento del formulario.
    Similar a crispy-forms FormHelper.
    """
    
    def __init__(self, form=None):
        self.form = form
        self.layout = None
        self.form_tag = True
        self.form_method = 'post'
        self.form_action = ''
        self.form_id = ''
        self.form_class = ''
        self.attrs = {}
        
        # Configuración de labels
        self.label_class = ''
        self.field_class = ''
        self.label_position = 'left'  # 'left', 'top', 'right'
        
        # Configuración de layout horizontal
        self.horizontal = False
        self.label_col = 'col-md-3'
        self.field_col = 'col-md-9'
    
    def render_layout(self, context=None):
        """Renderiza el layout completo del formulario"""
        if not self.form:
            return ''
        
        if not self.layout:
            return self._render_default(self.form)
        
        return self.layout.render(self.form, context or {})
    
    def _render_default(self, form):
        """Renderiza el formulario de manera predeterminada"""
        html = '<div class="form-fields">'
        for field in form:
            html += Field(field.name).render(form)
        html += '</div>'
        return mark_safe(html)


class Layout(LayoutObject):
    """
    Contenedor principal del layout del formulario.
    Acepta múltiples objetos de layout como hijos.
    
    Ejemplo:
        Layout(
            'campo1',
            'campo2',
            Row(Column('campo3'), Column('campo4')),
        )
    """
    
    def __init__(self, *fields):
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Field(field))
            else:
                self.fields.append(field)
    
    def render(self, form, context=None):
        html_parts = []
        for field_obj in self.fields:
            html_parts.append(field_obj.render(form, context))
        return mark_safe(''.join(html_parts))


class Field(LayoutObject):
    """
    Representa un campo individual del formulario.
    
    Parámetros:
        field_name: nombre del campo
        css_class: clases CSS adicionales
        wrapper_class: clases para el contenedor
        label_class: clases para el label
        template: template personalizado
        label_position: 'top', 'left', 'right', 'hidden'
        **kwargs: atributos HTML adicionales
    """
    
    def __init__(self, field_name, css_class='', wrapper_class='', 
                 label_class='', template=None, label_position='top', **kwargs):
        self.field_name = field_name
        self.css_class = css_class
        self.wrapper_class = wrapper_class or 'mb-3'
        self.label_class = label_class
        self.template = template
        self.label_position = label_position
        self.attrs = kwargs
    
    def render(self, form, context=None):
        if self.field_name not in form.fields:
            return ''
        
        field = form[self.field_name]
        
        # Agregar clases CSS al widget si se especificaron
        if self.css_class:
            existing_class = field.field.widget.attrs.get('class', '')
            field.field.widget.attrs['class'] = f"{existing_class} {self.css_class}".strip()
        
        # Agregar atributos HTML adicionales (placeholder, etc.)
        for key, value in self.attrs.items():
            field.field.widget.attrs[key] = value
        
        # Si hay un template personalizado, usarlo
        if self.template:
            return render_to_string(self.template, {'field': field, 'form': form})
        
        # Renderizar según la posición del label
        # IMPORTANTE: El campo ya tiene las clases CSS y atributos aplicados
        return self._render_field(field)
    
    def _render_field(self, field):
        """Renderiza el campo con el layout apropiado usando fieldRender.html"""
        html = f'<div class="{self.wrapper_class}" id="fieldset_{field.name}">'
        
        if self.label_position == 'hidden':
            # Sin label, solo el campo
            field_html = render_to_string('core/forms/fieldRender.html', {'field': field})
            html += field_html
        elif self.label_position == 'top':
            # Label arriba (por defecto)
            if field.label:
                label_class = f"form-label {self.label_class}".strip()
                html += f'<label for="id_{field.name}" class="{label_class}">{field.label}</label>'
            # Renderizar campo con fieldRender.html (incluye botones FK, help_text, errores)
            field_html = render_to_string('core/forms/fieldRender.html', {'field': field})
            html += field_html
        elif self.label_position == 'left':
            # Label a la izquierda (horizontal)
            html += '<div class="row">'
            label_class = f"col-form-label {self.label_class}".strip()
            html += f'<label for="id_{field.name}" class="col-md-3 {label_class}">{field.label}</label>'
            html += '<div class="col-md-9">'
            # Renderizar campo con fieldRender.html
            field_html = render_to_string('core/forms/fieldRender.html', {'field': field})
            html += field_html
            html += '</div>'
            html += '</div>'
        elif self.label_position == 'right':
            # Label a la derecha (para checkboxes)
            html += '<div class="d-flex align-items-center gap-2">'
            # Renderizar campo con fieldRender.html
            field_html = render_to_string('core/forms/fieldRender.html', {'field': field})
            html += field_html
            if field.label:
                html += f'<label for="id_{field.name}" class="{self.label_class}">{field.label}</label>'
            html += '</div>'
        
        html += '</div>'
        return mark_safe(html)


class Row(LayoutObject):
    """
    Crea una fila (row) de Bootstrap para organizar campos en columnas.
    
    Ejemplo:
        Row(
            Column('campo1', css_class='col-md-6'),
            Column('campo2', css_class='col-md-6'),
        )
    """
    
    def __init__(self, *fields, css_class=''):
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Column(Field(field)))
            elif isinstance(field, Field):
                self.fields.append(Column(field))
            else:
                self.fields.append(field)
        self.css_class = css_class
    
    def render(self, form, context=None):
        css_class = f"row {self.css_class}".strip()
        html = f'<div class="{css_class}">'
        for field_obj in self.fields:
            html += field_obj.render(form, context)
        html += '</div>'
        return mark_safe(html)


class Column(LayoutObject):
    """
    Crea una columna de Bootstrap dentro de una fila.
    
    Ejemplo:
        Column('campo1', css_class='col-md-6')
        Column(Field('campo2'), css_class='col-lg-4')
    """
    
    def __init__(self, *fields, css_class='col-md-12'):
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Field(field))
            else:
                self.fields.append(field)
        self.css_class = css_class
    
    def render(self, form, context=None):
        html = f'<div class="{self.css_class}">'
        for field_obj in self.fields:
            html += field_obj.render(form, context)
        html += '</div>'
        return mark_safe(html)


class Fieldset(LayoutObject):
    """
    Agrupa campos dentro de un fieldset con título.
    
    Ejemplo:
        Fieldset(
            'Información Personal',
            'nombre',
            'apellido',
            'email',
            css_class='border p-3'
        )
    """
    
    def __init__(self, legend, *fields, css_class='', legend_class=''):
        self.legend = legend
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Field(field))
            else:
                self.fields.append(field)
        self.css_class = css_class
        self.legend_class = legend_class or 'h5 mb-3'
    
    def render(self, form, context=None):
        css_class = f"fieldset-container mb-4 {self.css_class}".strip()
        html = f'<div class="{css_class}">'
        html += f'<legend class="{self.legend_class}">{self.legend}</legend>'
        for field_obj in self.fields:
            html += field_obj.render(form, context)
        html += '</div>'
        return mark_safe(html)


class Div(LayoutObject):
    """
    Contenedor div genérico para agrupar campos.
    
    Ejemplo:
        Div(
            'campo1',
            'campo2',
            css_class='card card-body'
        )
    """
    
    def __init__(self, *fields, css_class='', css_id='', **kwargs):
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Field(field))
            else:
                self.fields.append(field)
        self.css_class = css_class
        self.css_id = css_id
        self.attrs = kwargs
    
    def render(self, form, context=None):
        attrs_str = ' '.join([f'{k}="{v}"' for k, v in self.attrs.items()])
        id_attr = f'id="{self.css_id}"' if self.css_id else ''
        html = f'<div class="{self.css_class}" {id_attr} {attrs_str}>'
        for field_obj in self.fields:
            html += field_obj.render(form, context)
        html += '</div>'
        return mark_safe(html)


class HTML(LayoutObject):
    """
    Inserta HTML personalizado en el layout.
    
    Ejemplo:
        HTML('<hr class="my-4">')
        HTML('<h3>Sección Importante</h3>')
    """
    
    def __init__(self, html):
        self.html = html
    
    def render(self, form, context=None):
        return mark_safe(self.html)


class Separator(LayoutObject):
    """
    Inserta un separador visual (hr o título).
    
    Ejemplo:
        Separator()  # Solo línea
        Separator('Datos Personales')  # Con título
    """
    
    def __init__(self, text='', css_class='my-3'):
        self.text = text
        self.css_class = css_class
    
    def render(self, form, context=None):
        if self.text:
            return mark_safe(
                f'<div class="alert alert-primary {self.css_class}" role="alert" '
                f'style="font-size:0.9rem; padding: 5px 20px; margin-bottom: 10px">'
                f'{self.text}</div>'
            )
        else:
            return mark_safe(f'<hr class="{self.css_class}">')


class Card(LayoutObject):
    """
    Crea una tarjeta de Bootstrap con campos dentro.
    
    Ejemplo:
        Card(
            'Información del Usuario',
            'username',
            'email',
            'password',
            css_class='mb-4'
        )
    """
    
    def __init__(self, title, *fields, css_class='', header_class='', body_class=''):
        self.title = title
        self.fields = []
        for field in fields:
            if isinstance(field, str):
                self.fields.append(Field(field))
            else:
                self.fields.append(field)
        self.css_class = css_class or 'mb-4'
        self.header_class = header_class or 'bg-primary text-white'
        self.body_class = body_class
    
    def render(self, form, context=None):
        html = f'<div class="card {self.css_class}">'
        if self.title:
            html += f'<div class="card-header {self.header_class}">{self.title}</div>'
        html += f'<div class="card-body {self.body_class}">'
        for field_obj in self.fields:
            html += field_obj.render(form, context)
        html += '</div></div>'
        return mark_safe(html)


class Submit(LayoutObject):
    """
    Botón de submit personalizable.
    
    Ejemplo:
        Submit('Guardar', css_class='btn btn-primary btn-lg')
    """
    
    def __init__(self, value='Guardar', css_class='btn btn-primary', name='submit', **kwargs):
        self.value = value
        self.css_class = css_class
        self.name = name
        self.attrs = kwargs
    
    def render(self, form, context=None):
        attrs_str = ' '.join([f'{k}="{v}"' for k, v in self.attrs.items()])
        html = (
            f'<button type="submit" name="{self.name}" '
            f'class="{self.css_class}" {attrs_str}>{self.value}</button>'
        )
        return mark_safe(html)


class ButtonGroup(LayoutObject):
    """
    Agrupa múltiples botones.
    
    Ejemplo:
        ButtonGroup(
            Submit('Guardar'),
            HTML('<button type="reset" class="btn btn-secondary">Cancelar</button>'),
        )
    """
    
    def __init__(self, *buttons, css_class=''):
        self.buttons = buttons
        self.css_class = css_class or 'd-flex gap-2'
    
    def render(self, form, context=None):
        html = f'<div class="{self.css_class}">'
        for button in self.buttons:
            if isinstance(button, LayoutObject):
                html += button.render(form, context)
            else:
                html += str(button)
        html += '</div>'
        return mark_safe(html)
