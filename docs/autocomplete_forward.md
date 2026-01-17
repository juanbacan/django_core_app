# Formato de `forward` para `core:model_autocomplete`

Este documento explica el formato que puede enviarse desde los widgets `dal` a
la vista `ModelAutocompleteView` a través de `forward.Const(...)` y cómo usar
la nueva funcionalidad de serialización de objetos `Q` para filtros complejos.

Resumen rápido
- Valores simples: `forward=(dal.forward.Const('app.Model', 'model'),)`
- Filtros dict: `forward=(dal.forward.Const({'filter': {'proyecto_id': 5}}, 'proyecto_id'),)`
- Excludes: `{'exclude': {'id__in': [1,2]}}`
- `extra_q`: lista de dicts con lookups adicionales a aplicar con `.filter(...)`
- Serialización de `Q`: la clave especial `__q__` contiene la estructura serializada

1) Formato soportado

- Simple (string/int/list): aplicado como `field=value` o `field__in` si es lista.
- Dict con keys opcionales:
  - `filter`: dict con kwargs para `.filter(**filter)`
  - `exclude`: dict con kwargs para `.exclude(**exclude)`
  - `extra_q`: lista de dicts, cada dict aplicado con `.filter(**lookup)` (AND)

Ejemplo (filter + exclude):

```
forward=(
    dal.forward.Const({'filter': {'proyecto_id': 5}, 'exclude': {'id__in': [1,2]}}, 'proyecto_id'),
)
```

Nota sobre `search_fields`:
- Si envías `search_fields` desde el `forward` (como lista o string coma-separado), la vista `ModelAutocompleteView` lo usará para la búsqueda de texto. Esto sobrescribirá los `search_fields` definidos en la `ModelCRUDView` registrada cuando se proporcione.

Ejemplo de override:

```py
widget = autocomplete.ModelSelect2(
  url='core:model_autocomplete',
  forward=(
    forward.Const('proyectos.Material', 'model'),
    forward.Const(['nombre','descripcion'], 'search_fields'),
  ),
)
```

2) Serialización de `Q` (para OR/AND/negaciones)

Se provee `serialize_q(Q(...))` en `core.forms` y un helper `build_forward_const(val, dst)`.
Cuando pasas un `Q` a `build_forward_const` el `forward.Const` resultante contiene:

```
{'__q__': {'connector': 'AND'|'OR', 'negated': bool, 'children': [...]}}
```

Cada elemento en `children` es bien una tupla `[lookup, value]` o un dict anidado
con la misma forma (para expresiones compuestas). La vista `ModelAutocompleteView`
detecta `__q__`, reconstruye el `Q` y aplica `qs.filter(reconstructed_q)`.

Ejemplo de uso en un `ModelForm` o configuración de widget:

```py
from django.db.models import Q
from core.forms import build_forward_const

q = Q(proyecto_id=5) | Q(id__in=[1,2])
widget = ModelSelect2(
    url='core:model_autocomplete',
    forward=(build_forward_const(q, 'proyecto_q'),),
)
```

3) Ejemplo completo en `TareaObraForm`

```py
from django.db.models import Q
from core.forms import build_forward_const

widget = autocomplete.ModelSelect2Multiple(
    url='core:model_autocomplete',
    forward=(
        build_forward_const('proyectos.Persona', 'model'),
        build_forward_const(Q(proyecto_id=5), 'proyecto_q'),
    ),
)
```

4) Notas de seguridad y rendimiento
- Valida y limita el tamaño de los forwards que acepta tu vista en producción.
- No ejecutar/deserializar contenido arbitrario desde clientes no confiables.
- La serialización de `Q` está diseñada para combinaciones simples; evita
  serializar objetos muy profundos o con datos binarios.

5) Internals - cómo se procesa en la vista

- La vista extrae `forwarded` (JSON desde el widget). Para cada key/value:
  - Si value es dict y contiene `__q__`, la vista reconstruye el `Q` y aplica
    `qs.filter(qobj)`.
  - Si contiene `filter`, `exclude`, `extra_q`, los aplica como kwargs.
  - Si es valor simple se intenta aplicar `qs.filter(field=value)` o
    `field__in` si es lista.

6) Recomendaciones para desarrolladores
- Usar `build_forward_const` para forwards complejos desde Python.
- Para forwards dinámicos desde JS, asegurar que el JSON respete el formato
  descrito aquí (`__q__` para Q serializados, o `filter`/`exclude`).

Si quieres, agrego ejemplos de JS que construyan `dal-forward-conf` con estas
estructuras para widgets dinámicos.

*** Fin de documento

## Ejemplo completo: dos filtros a la vez (dict + Q)

A continuación un ejemplo práctico que combina un `dict` con `filter`/`exclude` y un `Q` serializado, enviados ambos desde el widget al endpoint `core:model_autocomplete`.

Python (en el `ModelForm` o `forms.py`):

```py
from django import forms
from django.db.models import Q
from dal import autocomplete
from core.forms import build_forward_const, ModelBaseForm
from .models import TareaObra, Material, Persona

class TareaObraTwoFiltersFullForm(ModelBaseForm):
  class Meta:
    model = TareaObra
    fields = ['titulo', 'materiales', 'responsables']
    widgets = {
      'materiales': autocomplete.ModelSelect2Multiple(url='core:model_autocomplete'),
      'responsables': autocomplete.ModelSelect2Multiple(url='core:model_autocomplete'),
    }

  def __init__(self, *args, proyecto_id=None, **kwargs):
    super().__init__(*args, **kwargs)

    # 1) Filtro tipo dict: filter + exclude
    filtro_a = {
      'filter': {'proyecto_id': proyecto_id},
      'exclude': {'id__in': [1, 2]},
    }

    # 2) Filtro tipo Q (OR / combinaciones complejas)
    q_persona = Q(activo=True) | Q(asignaciones__proyecto_id=proyecto_id)

    # Asignar forwards al widget: ambos filtros llegarán al endpoint
    self.fields['materiales'].widget.forward = (
      build_forward_const('proyectos.Material', 'model'),
      build_forward_const(filtro_a, 'material_filter_a'),
      build_forward_const(['nombre', 'codigo'], 'search_fields'),
    )

    self.fields['responsables'].widget.forward = (
      build_forward_const('proyectos.Persona', 'model'),
      build_forward_const(q_persona, 'persona_q'),
      build_forward_const('nombre,apellido', 'search_fields'),
    )

    # Querysets iniciales para UX/seguridad
    if proyecto_id:
      self.fields['materiales'].queryset = Material.objects.filter(proyecto_id=proyecto_id)
      self.fields['responsables'].queryset = Persona.objects.filter(activo=True)

```

Qué ocurre en la vista `ModelAutocompleteView`:
- `material_filter_a` es un dict con `filter` y `exclude`; la vista aplicará `.filter(**filter)` y `.exclude(**exclude)`.
- `persona_q` contiene la serialización de un `Q` (por `build_forward_const`); la vista reconstruye el `Q` y hace `qs.filter(reconstructed_q)`.
- Ambos filtros se aplican en secuencia (AND entre ellos si afectan al mismo queryset).

Ejemplo equivalente desde el frontend (atributo `data-dal-forward` JSON):

```html
<select data-dal-forward='{
  "model": "proyectos.Material",
  "material_filter_a": {"filter": {"proyecto_id": 5}, "exclude": {"id__in":[1,2]}},
  "persona_q": {"__q__": {"connector": "OR", "negated": false, "children": [["activo", true], ["asignaciones__proyecto_id", 5]]}},
  "search_fields": "nombre,codigo"
}'></select>
```

Seguridad y recomendaciones:
- Valida/whitelistea qué keys aceptas en `forward` en producción.
- Limita la complejidad y el tamaño de los forwards que aceptas.
- Para OR entre condiciones usa un único `Q`; múltiples forwards distintos se combinan por AND.

