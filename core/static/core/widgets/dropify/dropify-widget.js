/**
 * Custom Dropify Widget JavaScript
 * Inicializa todos los widgets Dropify en la página
 */

(function() {
    'use strict';

    /**
     * Inicializa un campo Dropify específico
     * @param {HTMLElement} element - El elemento input[type="file"]
     */
    function initializeDropifyField(element) {
        if (!element || !element.classList.contains('dropify-widget')) {
            return;
        }

        // Obtener configuración del elemento
        const config = {
            messages: {
                default: element.dataset.msgDefault || 'Arrastra aquí el archivo o haz clic para seleccionarlo',
                replace: element.dataset.msgReplace || 'Arrastra aquí el archivo o haz clic para reemplazarlo',
                remove: element.dataset.msgRemove || 'Eliminar',
                error: element.dataset.msgError || '¡Uy! Algo salió mal.'
            },
            allowedFileExtensions: element.dataset.allowedExtensions ? 
                element.dataset.allowedExtensions.split(',').map(ext => ext.trim()) : 
                ['webp', 'png', 'jpg', 'jpeg'],
            height: parseInt(element.dataset.height) || 200,
            defaultFile: element.dataset.defaultFile || null
        };

        // Configuración del template personalizado
        const customTpl = {
            wrap: '<div class="dropify-wrapper dropify-widget-wrapper"></div>',
            loader: '<div class="dropify-loader"></div>',
            message: '<div class="dropify-message"><span class="file-icon"></span><p>' + config.messages.default + '</p></div>',
            preview: '<div class="dropify-preview"><span class="dropify-render"></span><div class="dropify-infos"><div class="dropify-infos-inner"><p class="dropify-infos-message">' + config.messages.replace + '</p></div></div></div>',
            filename: '<p class="dropify-filename"><span class="file-icon"></span> <span class="dropify-filename-inner"></span></p>',
            clearButton: '<button type="button" class="dropify-clear">' + config.messages.remove + '</button>',
            errorLine: '<p class="dropify-error">' + config.messages.error + '</p>',
            errorsContainer: '<div class="dropify-errors-container"><ul></ul></div>'
        };

        // Inicializar Dropify
        try {
            $(element).dropify({
                messages: config.messages,
                allowedFileExtensions: config.allowedExtensions,
                defaultFile: config.defaultFile,
                height: config.height,
                tpl: customTpl
            });

            // Eventos personalizados para manejar la eliminación
            $(element).on('dropify.afterClear', function(event, element) {
                console.log('Archivo eliminado para el campo:', element.name);
                // Marcar la casilla de eliminación cuando se elimina el archivo
                const clearCheckbox = document.getElementById(element.id + '-clear');
                if (clearCheckbox) {
                    clearCheckbox.checked = true;
                }
            });

            $(element).on('dropify.fileReady', function(event, element) {
                console.log('Archivo seleccionado para el campo:', element.name);
                // Desmarcar la casilla de eliminación cuando se selecciona un nuevo archivo
                const clearCheckbox = document.getElementById(element.id + '-clear');
                if (clearCheckbox) {
                    clearCheckbox.checked = false;
                }
            });

            // Sincronizar el checkbox de Django con Dropify
            const clearCheckbox = document.getElementById(element.id + '-clear');
            if (clearCheckbox) {
                clearCheckbox.addEventListener('change', function() {
                    if (this.checked) {
                        // Si se marca el checkbox, limpiar Dropify
                        $(element).data('dropify').resetPreview();
                        $(element).data('dropify').clearElement();
                    }
                });
            }

            $(element).on('dropify.error', function(event, element, error) {
                console.error('Error en Dropify:', error);
            });

        } catch (error) {
            console.error('Error al inicializar Dropify:', error);
        }
    }

    /**
     * Inicializa todos los campos Dropify en la página
     */
    function initializeAllDropifyFields() {
        // Verificar que jQuery y Dropify estén disponibles
        if (typeof $ === 'undefined' || !$.fn.dropify) {
            console.warn('jQuery o Dropify no están disponibles aún, reintentando...');
            return false;
        }

        // Encontrar todos los campos dropify que no han sido inicializados
        const dropifyFields = document.querySelectorAll('.dropify-widget:not(.dropify-initialized)');
        
        dropifyFields.forEach(function(field) {
            initializeDropifyField(field);
            // Marcar como inicializado para evitar duplicados
            field.classList.add('dropify-initialized');
        });

        return dropifyFields.length > 0;
    }

    /**
     * Función para reintentar la inicialización
     */
    function retryInitialization() {
        let attempts = 0;
        const maxAttempts = 50; // 5 segundos máximo (50 * 100ms)

        const interval = setInterval(function() {
            attempts++;
            
            if (initializeAllDropifyFields() || attempts >= maxAttempts) {
                clearInterval(interval);
                if (attempts >= maxAttempts) {
                    console.warn('No se pudo inicializar Dropify después de varios intentos');
                }
            }
        }, 100);
    }

    /**
     * Inicialización cuando el DOM está listo
     */
    function initializeOnReady() {
        if (!initializeAllDropifyFields()) {
            retryInitialization();
        }
    }

    // Observer para campos añadidos dinámicamente
    function setupMutationObserver() {
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver(function(mutations) {
                let shouldReinit = false;
                
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // Verificar si el nodo añadido contiene campos dropify
                                if (node.classList && node.classList.contains('dropify-widget')) {
                                    shouldReinit = true;
                                } else if (node.querySelector && node.querySelector('.dropify-widget')) {
                                    shouldReinit = true;
                                }
                            }
                        });
                    }
                });
                
                if (shouldReinit) {
                    setTimeout(initializeAllDropifyFields, 100);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }

    // Múltiples puntos de inicialización para máxima compatibilidad
    
    // 1. Si el DOM ya está listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeOnReady);
    } else {
        initializeOnReady();
    }

    // 2. Cuando la ventana esté completamente cargada
    window.addEventListener('load', initializeAllDropifyFields);

    // 3. Setup del observer para elementos dinámicos
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupMutationObserver);
    } else {
        setupMutationObserver();
    }

    // 4. Exponer función global para inicialización manual
    window.initializeDropifyWidget = initializeDropifyField;
    window.initializeAllDropifyWidgets = initializeAllDropifyFields;

})();
