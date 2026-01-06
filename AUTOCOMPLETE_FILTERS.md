# Sistema de Autocomplete con Filtros

Este documento explica cómo usar el sistema de autocomplete con filtrado dinámico basado en django-autocomplete-light (DAL).

## Características

- ✅ Autocomplete genérico para cualquier modelo registrado en `ModelCRUDView`
- ✅ Filtrado automático basado en campos del modelo
- ✅ Filtrado personalizado mediante método estático
- ✅ Búsqueda por texto en múltiples campos
- ✅ Soporte para forward de campos relacionados

## Requisitos Previos

1. El modelo debe tener una vista CRUD registrada (`ModelCRUDView`)
2. La vista CRUD debe definir `search_fields`

```python
class UsuariosView(ModelCRUDView):
    model = CustomUser
    search_fields = ['username', 'email', 'first_name', 'last_name']
    # ... resto de configuración
```

## Uso Básico (Sin Filtros)

### En tu formulario:

```python
from dal import autocomplete, forward

class MiFormulario(ModelBaseForm):
    usuario = forms.ModelChoiceField(
        label="Usuario",
        queryset=CustomUser.objects.all(),
        required=True,
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('core.CustomUser', 'model'),
            ),
            attrs={'data-html': True},
        )
    )
    
    class Meta:
        model = MiModelo
        fields = '__all__'
```

**Nota:** El formato del modelo debe ser `'app_label.ModelName'` (ej: `'core.CustomUser'`)

## Filtrado Automático

El sistema puede filtrar automáticamente basándose en otros campos del formulario.

### Ejemplo: Filtrar ciudades por país

```python
class DireccionForm(ModelBaseForm):
    pais = forms.ModelChoiceField(
        label="País",
        queryset=Pais.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('geografia.Pais', 'model'),),
        )
    )
    
    ciudad = forms.ModelChoiceField(
        label="Ciudad",
        queryset=Ciudad.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('geografia.Ciudad', 'model'),
                forward.Field('pais', 'pais_id'),  # ← Filtrar por país
            ),
        )
    )
    
    class Meta:
        model = Direccion
        fields = ['pais', 'ciudad', 'calle']
```

**Cómo funciona:**
- `forward.Field('pais', 'pais_id')` envía el valor del campo `pais` como parámetro `pais_id`
- El sistema filtra automáticamente: `Ciudad.objects.filter(pais_id=<valor_seleccionado>)`

### Ejemplo: Múltiples filtros

```python
class AsignacionForm(ModelBaseForm):
    departamento = forms.ModelChoiceField(
        label="Departamento",
        queryset=Departamento.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('rrhh.Departamento', 'model'),),
        )
    )
    
    cargo = forms.ModelChoiceField(
        label="Cargo",
        queryset=Cargo.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('rrhh.Cargo', 'model'),),
        )
    )
    
    empleado = forms.ModelChoiceField(
        label="Empleado",
        queryset=Empleado.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('rrhh.Empleado', 'model'),
                forward.Field('departamento', 'departamento_id'),
                forward.Field('cargo', 'cargo_id'),
            ),
        )
    )
    
    class Meta:
        model = Asignacion
        fields = '__all__'
```

## Filtrado Personalizado

Para lógica de filtrado más compleja, define el método estático `filter_autocomplete_queryset` en tu vista CRUD.

### Ejemplo 1: Filtrar por estado activo

```python
class CiudadView(ModelCRUDView):
    model = Ciudad
    search_fields = ['nombre', 'codigo']
    list_display = ['nombre', 'pais', 'activo']
    
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        """
        Filtrado personalizado para autocomplete.
        
        Args:
            qs: QuerySet del modelo
            forward_filters: dict con los parámetros forward (sin 'model')
            search_term: término de búsqueda del usuario (puede ser None)
        
        Returns:
            QuerySet filtrado
        """
        # Filtrar por país si viene en forward
        if 'pais_id' in forward_filters:
            qs = qs.filter(pais_id=forward_filters['pais_id'])
        
        # Solo mostrar ciudades activas
        qs = qs.filter(activo=True)
        
        # Ordenar por nombre
        qs = qs.order_by('nombre')
        
        return qs
```

### Ejemplo 2: Filtrado con lógica compleja

```python
class ProductoView(ModelCRUDView):
    model = Producto
    search_fields = ['codigo', 'nombre', 'descripcion']
    
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        # Filtrar por categoría
        if 'categoria_id' in forward_filters:
            qs = qs.filter(categoria_id=forward_filters['categoria_id'])
        
        # Filtrar por rango de precios
        if 'precio_min' in forward_filters:
            qs = qs.filter(precio__gte=forward_filters['precio_min'])
        if 'precio_max' in forward_filters:
            qs = qs.filter(precio__lte=forward_filters['precio_max'])
        
        # Si hay búsqueda de texto, dar prioridad a coincidencias exactas
        if search_term:
            from django.db.models import Q, Case, When, IntegerField
            
            qs = qs.annotate(
                match_priority=Case(
                    When(codigo__iexact=search_term, then=1),
                    When(nombre__iexact=search_term, then=2),
                    When(codigo__istartswith=search_term, then=3),
                    When(nombre__istartswith=search_term, then=4),
                    default=5,
                    output_field=IntegerField(),
                )
            ).order_by('match_priority', 'nombre')
        
        # Solo productos en stock
        qs = qs.filter(stock__gt=0)
        
        return qs
```

### Ejemplo 3: Filtrar basándose en el usuario actual

```python
class DocumentoView(ModelCRUDView):
    model = Documento
    search_fields = ['titulo', 'codigo']
    
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        # Nota: No tenemos acceso directo a request aquí
        # Para usar el usuario actual, debes pasar su ID via forward
        
        if 'usuario_id' in forward_filters:
            usuario_id = forward_filters['usuario_id']
            # Mostrar solo documentos del usuario o documentos públicos
            qs = qs.filter(
                Q(creado_por_id=usuario_id) | Q(publico=True)
            )
        
        if 'departamento_id' in forward_filters:
            qs = qs.filter(departamento_id=forward_filters['departamento_id'])
        
        return qs.filter(activo=True).order_by('-fecha_creacion')
```

En el formulario:

```python
class AsignarDocumentoForm(ModelBaseForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    documento = forms.ModelChoiceField(
        label="Documento",
        queryset=Documento.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('documentos.Documento', 'model'),
                forward.Const(user.id, 'usuario_id'),  # Pasar ID del usuario
            ),
        )
    )
```

## Filtrado con Valores Constantes

Puedes enviar valores fijos para filtrar:

```python
# Solo mostrar productos de categoría específica
producto = forms.ModelChoiceField(
    label="Producto",
    queryset=Producto.objects.all(),
    widget=autocomplete.ModelSelect2(
        url='core:model_autocomplete',
        forward=(
            forward.Const('tienda.Producto', 'model'),
            forward.Const(5, 'categoria_id'),  # Categoría fija
            forward.Const(True, 'activo'),     # Solo activos
        ),
    )
)
```

## Filtrado con Campos Relacionados (Foreign Keys)

```python
class PedidoDetalleForm(ModelBaseForm):
    pedido = forms.ModelChoiceField(
        queryset=Pedido.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('ventas.Pedido', 'model'),),
        )
    )
    
    producto = forms.ModelChoiceField(
        label="Producto",
        queryset=Producto.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('inventario.Producto', 'model'),
                # Filtrar por el cliente del pedido (relación anidada)
                forward.Field('pedido', 'pedido_id'),
            ),
        )
    )
```

En la vista CRUD:

```python
class ProductoView(ModelCRUDView):
    model = Producto
    search_fields = ['nombre', 'codigo']
    
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        if 'pedido_id' in forward_filters:
            from ventas.models import Pedido
            try:
                pedido = Pedido.objects.get(id=forward_filters['pedido_id'])
                # Filtrar productos del proveedor habitual del cliente
                qs = qs.filter(proveedor=pedido.cliente.proveedor_habitual)
            except Pedido.DoesNotExist:
                pass
        
        return qs
```

## Filtrado por Múltiples Valores (Listas)

El sistema detecta automáticamente si el valor es una lista y usa `__in`:

```python
# En tu vista CRUD
class EmpleadoView(ModelCRUDView):
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        # Si forward_filters['departamentos_ids'] es [1, 2, 3]
        # Se aplicará: qs.filter(departamento_id__in=[1, 2, 3])
        return qs
```

## Consideraciones Importantes

1. **Rendimiento**: Los filtros se aplican en cada petición AJAX. Para grandes conjuntos de datos, considera:
   - Agregar índices de base de datos en campos filtrados
   - Usar `select_related()` o `prefetch_related()` en filtros personalizados
   - Limitar el tamaño del queryset base

2. **Seguridad**: 
   - Los parámetros forward son enviados desde el cliente
   - Valida siempre los valores en `filter_autocomplete_queryset`
   - No confíes ciegamente en IDs de usuario enviados desde el frontend

3. **Orden de aplicación**:
   - Primero se aplican los filtros (automáticos o personalizados)
   - Luego se aplica la búsqueda de texto (`search_fields`)

4. **Campos no existentes**: 
   - El filtrado automático ignora silenciosamente campos que no existen
   - Usa filtrado personalizado si necesitas manejar errores explícitamente

## Solución de Problemas

### El autocomplete no muestra resultados

1. Verifica que el modelo esté registrado con una vista CRUD
2. Verifica que `search_fields` esté definido en la vista CRUD
3. Revisa la consola del navegador para errores de red
4. Verifica el formato del modelo: `'app_label.ModelName'`

### Los filtros no se aplican

1. Verifica que el campo forward existe en el modelo
2. Usa la consola de desarrollo para ver los parámetros enviados
3. Agrega logging en `filter_autocomplete_queryset`:

```python
@staticmethod
def filter_autocomplete_queryset(qs, forward_filters, search_term):
    print(f"Filtros recibidos: {forward_filters}")
    print(f"Término de búsqueda: {search_term}")
    # ... tu lógica
```

### El campo dependiente no se actualiza

Asegúrate de que el widget DAL esté correctamente inicializado:
- Los scripts de DAL deben cargarse después de jQuery
- Verifica que `{{ form.media }}` esté en el template

## Ejemplos Completos

### Caso de Uso: Sistema de Inventario

```python
# models.py
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

class Proveedor(models.Model):
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)

class Producto(models.Model):
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

# views.py
class ProductoView(ModelCRUDView):
    model = Producto
    search_fields = ['codigo', 'nombre']
    list_display = ['codigo', 'nombre', 'categoria', 'precio', 'stock']
    
    @staticmethod
    def filter_autocomplete_queryset(qs, forward_filters, search_term):
        # Filtrar por categoría
        if 'categoria_id' in forward_filters:
            qs = qs.filter(categoria_id=forward_filters['categoria_id'])
        
        # Filtrar por proveedor
        if 'proveedor_id' in forward_filters:
            qs = qs.filter(proveedor_id=forward_filters['proveedor_id'])
        
        # Solo productos con stock disponible
        if forward_filters.get('con_stock'):
            qs = qs.filter(stock__gt=0)
        
        return qs.filter(activo=True).select_related('categoria', 'proveedor')

# forms.py
class CompraForm(ModelBaseForm):
    categoria = forms.ModelChoiceField(
        label="Categoría",
        queryset=Categoria.objects.filter(activo=True),
        required=False,
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('inventario.Categoria', 'model'),),
        )
    )
    
    proveedor = forms.ModelChoiceField(
        label="Proveedor",
        queryset=Proveedor.objects.filter(activo=True),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(forward.Const('inventario.Proveedor', 'model'),),
        )
    )
    
    producto = forms.ModelChoiceField(
        label="Producto",
        queryset=Producto.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='core:model_autocomplete',
            forward=(
                forward.Const('inventario.Producto', 'model'),
                forward.Field('categoria', 'categoria_id'),
                forward.Field('proveedor', 'proveedor_id'),
                forward.Const(True, 'con_stock'),
            ),
            attrs={'data-html': True},
        )
    )
    
    cantidad = forms.IntegerField(min_value=1)
    
    class Meta:
        model = Compra
        fields = ['categoria', 'proveedor', 'producto', 'cantidad']
```

## Referencias

- [Django Autocomplete Light Documentation](https://django-autocomplete-light.readthedocs.io/)
- [Select2 Documentation](https://select2.org/)
