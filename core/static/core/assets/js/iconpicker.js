const jsonPath = '/static/core/icons/icons.json';
let iconsPerPage = 54;
let allIcons = []; // { iconClass, name, search }
let filteredIcons = [];
let currentPage = 1;
let iconsLoaded = false;
let currentInputName = null;

const iconListContainer = document.getElementById('icon-list');
const iconSearchInput = document.getElementById('iconSearch');
const prevPageButton = document.getElementById('prevPage');
const nextPageButton = document.getElementById('nextPage');
const paginationInfo = document.getElementById('paginationInfo');
const resultsCount = document.getElementById('resultsCount');
const perPageSelect = document.getElementById('perPage');
const clearSearchBtn = document.getElementById('clearSearch');
const iconSpinner = document.getElementById('iconSpinner');
const noResultsDiv = document.getElementById('noResults');

let currentQueryTokens = [];

// Normaliza texto: quita tildes y pasa a minúsculas
function normalizeText(str) {
    if (!str) return '';
    try {
        return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
    } catch (e) {
        // Fallback para navegadores que no soporten \p{Diacritic}
        return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    }
}

// Mapa simple de sinónimos en español hacia términos presentes en los nombres de iconos
const spanishSynonyms = {
    'flecha': ['arrow', 'chevron'],
    'flechas': ['arrow', 'chevron'],
    'casa': ['home'],
    'inicio': ['home'],
    'usuario': ['user', 'person'],
    'usuarios': ['user', 'person'],
    'persona': ['user', 'person'],
    'personas': ['user', 'person'],
    'correo': ['envelope', 'mail', 'email'],
    'email': ['envelope', 'mail'],
    'camara': ['camera', 'photo', 'image'],
    'buscar': ['search', 'magnifying'],
    'lupa': ['search', 'magnifying'],
    'carpeta': ['folder'],
    'carpeta abierta': ['folder-open'],
    'carpeta cerrada': ['folder-closed'],
    'ajustes': ['cog', 'gear', 'settings'],
    'configuracion': ['cog', 'gear', 'settings'],
    'descargar': ['download'],
    'subir': ['upload'],
    'flechaarriba': ['arrow-up'],
    'flechaabajo': ['arrow-down']
};

// Función para cargar y procesar el archivo JSON
function loadIcons() {
    if (iconsLoaded) return; // Evitar cargar nuevamente si ya se cargaron
    showSpinner(true);

    fetch(jsonPath)
        .then(response => response.json())
        .then(data => {
            // Convertir los iconos a una lista estructurada con campo 'search' para búsquedas
            Object.entries(data).forEach(([iconName, details]) => {
                const styles = details.styles || [];
                // Construir un texto de búsqueda a partir del nombre (también con guiones convertidos
                // a espacios) y posibles detalles
                let searchable = iconName + ' ' + iconName.replace(/-/g, ' ');
                if (details && details.label) searchable += ' ' + details.label;
                if (details && details.search) searchable += ' ' + details.search;
                // Normalizar: eliminar tildes y pasar a minúsculas
                const normalized = normalizeText(searchable);

                styles.forEach(style => {
                    const iconClass = `fa-${style} fa-${iconName}`;
                    allIcons.push({ iconClass, name: iconName, search: normalized });
                });
            });
            filteredIcons = allIcons.slice(); // Inicialmente todos los iconos están disponibles
            iconsLoaded = true; // Marcar como cargados
            showSpinner(false);
            renderIcons(); // Renderizar la primera página
        })
        .catch(error => console.error('Error al cargar los iconos:', error));
}

function showSpinner(show) {
    if (!iconSpinner) return;
    iconSpinner.classList.toggle('d-none', !show);
}

// Renderizar iconos en la página actual
function renderIcons() {
    // leer per-page dinámico
    try { iconsPerPage = parseInt(perPageSelect.value, 10) || iconsPerPage; } catch(e) {}
    const startIndex = (currentPage - 1) * iconsPerPage;
    const endIndex = startIndex + iconsPerPage;
    const iconsToShow = filteredIcons.slice(startIndex, endIndex);
    iconListContainer.innerHTML = ''; // Limpiar contenido previo
    if (iconsToShow.length === 0) {
        noResultsDiv.classList.remove('d-none');
    } else {
        noResultsDiv.classList.add('d-none');
    }

    iconsToShow.forEach(iconObj => {
        const iconClass = iconObj.iconClass;
        const iconNameRaw = iconObj.name.replace(/^\d+\-?/, '');
        // Resaltar si hay query
        let displayName = iconNameRaw;
        if (currentQueryTokens.length) {
            // si alguno de los tokens aparece en la versión normalizada, marcamos el nombre
            const norm = normalizeText(iconNameRaw);
            const anyMatch = currentQueryTokens.some(t => norm.includes(t));
            if (anyMatch) {
                displayName = `<mark>${iconNameRaw}</mark>`;
            }
        }

        const iconDiv = document.createElement('div');
        iconDiv.className = 'col-2 text-center mb-3';
        iconDiv.innerHTML = `
            <i class="${iconClass} fa-2x" tabindex="0" style="cursor: pointer;" data-icon-class="${iconClass}" role="button" aria-label="${iconNameRaw}"></i>
            <div class="icon-name" style="font-size: 0.7rem; color: #555;">${displayName}</div>
        `;
        const iconEl = iconDiv.querySelector('i');
        iconEl.addEventListener('click', () => selectIcon(iconClass));
        iconEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') selectIcon(iconClass); });
        iconListContainer.appendChild(iconDiv);
    });

    // Actualizar controles de paginación
    paginationInfo.textContent = `Página ${currentPage} de ${Math.max(1, Math.ceil(filteredIcons.length / iconsPerPage))}`;
    prevPageButton.disabled = currentPage === 1;
    nextPageButton.disabled = currentPage === Math.ceil(filteredIcons.length / iconsPerPage);
    if (resultsCount) resultsCount.textContent = `${filteredIcons.length} resultados`;
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
        const raw = iconSearchInput.value || '';
        const query = normalizeText(raw);
        const tokens = query.split(/\s+/).filter(Boolean);
        currentQueryTokens = tokens.slice();

        // Expand tokens with spanish synonyms
        const expandedTokens = [];
        tokens.forEach(t => {
            expandedTokens.push(t);
            const syns = spanishSynonyms[t];
            if (syns && syns.length) expandedTokens.push(...syns);
        });

        // Filtrar: por cada token original, aceptar si el icono contiene el token
        // o cualquiera de sus sinónimos (OR entre sinónimos, AND entre tokens)
        filteredIcons = allIcons.filter(icon => {
            return tokens.every(tok => {
                const syns = spanishSynonyms[tok] || [];
                const options = [tok, ...syns];
                return options.some(opt => icon.search.includes(opt));
            });
        });
        currentPage = 1; // Reiniciar a la primera página de resultados
        renderIcons();
    });

    // Clear search
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            iconSearchInput.value = '';
            currentQueryTokens = [];
            filteredIcons = allIcons.slice();
            currentPage = 1;
            renderIcons();
            iconSearchInput.focus();
        });
    }

    // per-page change
    if (perPageSelect) {
        perPageSelect.addEventListener('change', () => {
            currentPage = 1;
            renderIcons();
        });
    }

    // Funciones de cambio de página
    prevPageButton.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            renderIcons();
        }
    });

    nextPageButton.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage < Math.ceil(filteredIcons.length / iconsPerPage)) {
            currentPage++;
            renderIcons();
        }
    });

    document.querySelectorAll('.iconpicker-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentInputName = this.getAttribute('data-icon-input');
            const modalEl = document.getElementById('iconModal');
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
            // Focus search when open
            modalEl.addEventListener('shown.bs.modal', function handler() {
                setTimeout(() => { if (iconSearchInput) iconSearchInput.focus(); }, 50);
                modalEl.removeEventListener('shown.bs.modal', handler);
            });
        });
    });

    // Detectar cuando se abre el modal
    const iconModal = document.getElementById('iconModal');
    iconModal.addEventListener('shown.bs.modal', loadIcons); // Cargar iconos al abrir el modal
});

