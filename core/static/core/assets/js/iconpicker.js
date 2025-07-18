const jsonPath = '/static/core/icons/icons.json';
const iconsPerPage = 54;
let allIcons = [];
let filteredIcons = [];
let currentPage = 1;
let iconsLoaded = false;
let currentInputName = null;

const iconListContainer = document.getElementById('icon-list');
const iconSearchInput = document.getElementById('iconSearch');
const prevPageButton = document.getElementById('prevPage');
const nextPageButton = document.getElementById('nextPage');
const paginationInfo = document.getElementById('paginationInfo');

// Función para cargar y procesar el archivo JSON
function loadIcons() {
    if (iconsLoaded) return; // Evitar cargar nuevamente si ya se cargaron

    fetch(jsonPath)
        .then(response => response.json())
        .then(data => {
            // Convertir los iconos a una lista
            Object.entries(data).forEach(([iconName, details]) => {
                const styles = details.styles || [];
                styles.forEach(style => {
                    allIcons.push(`fa-${style} fa-${iconName}`);
                });
            });
            filteredIcons = allIcons; // Inicialmente todos los iconos están disponibles
            iconsLoaded = true; // Marcar como cargados
            renderIcons(); // Renderizar la primera página
        })
        .catch(error => console.error('Error al cargar los iconos:', error));
}

// Renderizar iconos en la página actual
function renderIcons() {
    const startIndex = (currentPage - 1) * iconsPerPage;
    const endIndex = startIndex + iconsPerPage;
    const iconsToShow = filteredIcons.slice(startIndex, endIndex);

    iconListContainer.innerHTML = ''; // Limpiar contenido previo
    iconsToShow.forEach(iconClass => {
        const iconName = iconClass.split(' ')[1].replace('fa-', ''); // Obtener el nombre del icono
        const iconDiv = document.createElement('div');
        iconDiv.className = 'col-2 text-center mb-3';
        iconDiv.innerHTML = `
            <i class="${iconClass} fa-2x" style="cursor: pointer;" data-icon-class="${iconClass}"></i>
            <div class="icon-name" style="font-size: 0.7rem; color: #555;">${iconName}</div>
        `;
        iconDiv.querySelector('i').addEventListener('click', () => selectIcon(iconClass));
        iconListContainer.appendChild(iconDiv);
    });

    // Actualizar controles de paginación
    paginationInfo.textContent = `Página ${currentPage} de ${Math.ceil(filteredIcons.length / iconsPerPage)}`;
    prevPageButton.disabled = currentPage === 1;
    nextPageButton.disabled = currentPage === Math.ceil(filteredIcons.length / iconsPerPage);
}

// Seleccionar un icono
function selectIcon(iconClass) {
    if (!currentInputName) return;
    const input = document.querySelector(`[data-icon-input='${currentInputName}']`);
    const preview = document.getElementById(`icon-preview-${currentInputName}`);
    if (input) input.value = iconClass;
    if (preview) preview.innerHTML = `<i class="${iconClass}"></i>`;
    const modal = bootstrap.Modal.getInstance(document.getElementById('iconModal'));
    modal.hide();
}

document.addEventListener('DOMContentLoaded', () => {
    // Buscar iconos por nombre
    iconSearchInput.addEventListener('input', () => {
        const query = iconSearchInput.value.toLowerCase();
        filteredIcons = allIcons.filter(icon => icon.includes(query));
        currentPage = 1; // Reiniciar a la primera página de resultados
        renderIcons();
    });

    // Funciones de cambio de página
    prevPageButton.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderIcons();
        }
    });

    nextPageButton.addEventListener('click', () => {
        if (currentPage < Math.ceil(filteredIcons.length / iconsPerPage)) {
            currentPage++;
            renderIcons();
        }
    });

    document.querySelectorAll('.iconpicker-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentInputName = this.getAttribute('data-icon-input');
            const modal = new bootstrap.Modal(document.getElementById('iconModal'));
            modal.show();
        });
    });

    // Detectar cuando se abre el modal
    const iconModal = document.getElementById('iconModal');
    iconModal.addEventListener('shown.bs.modal', loadIcons); // Cargar iconos al abrir el modal
});

