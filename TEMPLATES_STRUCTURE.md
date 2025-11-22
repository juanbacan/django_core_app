# 🔧 Estructura de Templates de Formularios - Reutilización de Código

## 📦 Archivos Comunes Creados

Para evitar duplicación de código, se han creado 3 archivos de includes reutilizables:

### 1. `core/forms/form_css.html`
Contiene todos los estilos CSS comunes para formularios:
- Estilos para botones de Foreign Key (`.fk-btn`, `.fk-block`)
- Estilos para raw FK fields (`.fk-raw`)
- Estilos para widgets personalizados

### 2. `core/forms/form_js.html`
Contiene todo el JavaScript común para formularios:
- **Funciones de utilidad:**
  - `slugify()` - Convierte texto a slug
  - `quitarTildes()` - Elimina acentos
  
- **Funciones para Foreign Keys:**
  - `openFKPopup()` - Abre popup para agregar FK
  - `openFKEditPopup()` - Abre popup para editar FK
  - `dismissAddPopup()` - Callback cuando se cierra el popup
  - `clearFKField()` - Limpia selección de FK
  - `openFKRawPopup()` - Abre popup para raw_id_fields

- **Soporte automático:**
  - Prepopulated fields (slugs automáticos)
  - Form media (CSS/JS del formulario)
  - Inline formsets
  - Iconpicker
  - Select2 integration

### 3. `core/forms/form_modals.html`
Contiene modales comunes:
- Modal de selección de iconos (iconpicker)
- Otros modales según sea necesario

## 🎯 Templates que Usan los Includes

Todos estos templates ahora incluyen automáticamente los recursos comunes:

### ✅ `formAdmin.html`
```django
{% block extracss %}
    {% include 'core/forms/form_css.html' %}
{% endblock %}

{% block extrajs %}
    {% include 'core/forms/form_js.html' %}
{% endblock %}

{# Al final del contenido #}
{% include 'core/forms/form_modals.html' %}
```

### ✅ `formModal.html`
```django
{# Al inicio #}
<style>
    {% include 'core/forms/form_css.html' %}
</style>

{# En el bloque extrajs #}
{% block extrajs %}
    {% include 'core/forms/form_js.html' %}
{% endblock %}
```

### ✅ `form.html`
```django
{# Al inicio #}
{% include 'core/forms/form_css.html' %}

{# Al final #}
{% include 'core/forms/form_modals.html' %}
```

### ✅ `formWithLayout.html`
```django
{# Al inicio #}
{% include 'core/forms/form_css.html' %}

{# Al final #}
{% include 'core/forms/form_js.html' %}
{% include 'core/forms/form_modals.html' %}
```

## 💡 Ventajas de Esta Estructura

### 1. **DRY (Don't Repeat Yourself)**
- El código JavaScript y CSS está en un solo lugar
- Cambios en una función afectan todos los formularios
- Más fácil de mantener

### 2. **Consistencia**
- Todos los formularios tienen la misma funcionalidad
- No importa qué template uses, todo funciona igual

### 3. **Fácil Extensión**
- Para agregar nueva funcionalidad, editas un solo archivo
- Automáticamente disponible en todos los formularios

### 4. **Carga Condicional**
- Los recursos solo se cargan si el formulario los necesita
- Ejemplo: iconpicker solo se carga si `form.iconpicker == True`

## 🔄 Funcionalidad Incluida Automáticamente

Cuando usas cualquiera de los templates de formularios, **automáticamente** tienes:

### ✅ Foreign Keys
- Botones de agregar/editar en campos FK
- Popups para crear nuevos registros
- Soporte para raw_id_fields
- Integración con Select2

### ✅ Prepopulated Fields
- Slugs automáticos desde otros campos
- Conversión a minúsculas y eliminación de tildes

### ✅ Inline Formsets
- JavaScript para agregar/eliminar filas
- Validación automática

### ✅ Iconpicker
- Modal de selección de iconos
- Búsqueda y paginación

### ✅ Form Media
- CSS y JS definidos en formularios y widgets
- Carga automática

## 📝 Cómo Usar en Tus Propios Templates

Si creas un template personalizado y quieres tener toda la funcionalidad:

```django
{% extends 'base.html' %}
{% load static %}

{% block content %}
    {# Incluir CSS común #}
    <style>
        {% include 'core/forms/form_css.html' %}
    </style>

    <form method="POST">
        {% csrf_token %}
        
        {# Tu formulario aquí #}
        {{ form.as_p }}
        
        <button type="submit">Guardar</button>
    </form>

    {# Incluir JavaScript común #}
    {% include 'core/forms/form_js.html' %}
    
    {# Incluir modales #}
    {% include 'core/forms/form_modals.html' %}
{% endblock %}
```

## 🎨 Personalización

### Agregar CSS Adicional
```django
{% block extracss %}
    {% include 'core/forms/form_css.html' %}
    
    <style>
        /* Tus estilos personalizados aquí */
        .mi-clase-custom {
            color: blue;
        }
    </style>
{% endblock %}
```

### Agregar JavaScript Adicional
```django
{% block extrajs %}
    {% include 'core/forms/form_js.html' %}
    
    <script>
        // Tu JavaScript personalizado aquí
        console.log('Mi código custom');
    </script>
{% endblock %}
```

## 🔍 Archivos en la Estructura

```
core/templates/core/forms/
├── form.html                  # ✅ Usa includes
├── formAdmin.html             # ✅ Usa includes
├── formWithLayout.html        # ✅ Usa includes
├── formRender.html            # Template base de renderizado
├── formRender2.html           # Variante de renderizado
├── formRender3.html           # Renderizado con fieldsets
├── fieldRender.html           # Renderizado de campo individual
├── form_inline.html           # Formsets inline
├── form_inline_js.html        # JavaScript para inline
├── form_css.html              # 🆕 CSS común (include)
├── form_js.html               # 🆕 JavaScript común (include)
└── form_modals.html           # 🆕 Modales comunes (include)

core/templates/core/modals/
└── formModal.html             # ✅ Usa includes
```

## 🚀 Resultado Final

Ahora **todos tus formularios** tienen automáticamente:

- ✅ Botones de FK funcionando
- ✅ Popups de agregar/editar
- ✅ Slugs automáticos
- ✅ Iconpicker
- ✅ Inline formsets
- ✅ Select2 integration
- ✅ Form media

**Sin duplicar ni una línea de código.** 🎉
