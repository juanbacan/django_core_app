async function fetchRequest(url, params, csrftoken=csrf_token) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(params),
        credentials: 'same-origin',
    });

    if (resp.status !== 200) {
        return {
            result: false,
            mensaje: 'Error al realizar la petición'
        }
    }
    const data = await resp.json();
    return data;
}

function fetchRequest2(options) {
    return new Promise((resolve, reject) => {
        let url = options.url;
        headers = {
            'Content-Type': 'application/json', 
            'X-CSRFToken': csrf_token,
            'X-Requested-With': 'XMLHttpRequest'
        };
        if (options.headers) headers = Object.assign(headers, options.headers);
        let init = { method: options.method || 'GET', headers: headers };
        
        if (options.data) {
            if (init.method === 'GET') {
                url += '?' + new URLSearchParams(options.data).toString();
            } else {
                init.body = JSON.stringify(options.data);
                init.headers['Content-Type'] = 'application/json';
            }
        }
        if (options.timeout) init.timeout = options.timeout;

        fetch(url, init)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => Promise.reject(data));
                }
                return response.json();
            })
            .then(data => {
                if (options.success) {
                    options.success(data);
                } else {
                    resolve(data);
                }
            })
            .catch(error => {
                if (options.error) {
                    options.error(error);
                } else {
                    reject(error);
                }
            });
        });
}


// Main *****************************************
function ready(callback){
    // in case the document is already rendered
    if (document.readyState!='loading') callback();
    // modern browsers
    else if (document.addEventListener) document.addEventListener('DOMContentLoaded', callback);
    // IE <= 8
    else document.attachEvent('onreadystatechange', function(){
        if (document.readyState=='complete') callback();
    });
}

function bloqueoInterfaz() {
    // console.log("Bloqueando Interfaz");
    document.getElementById( 'loading-static' ).style.display = 'flex';
}
function desbloqueoInterfaz() {
    // console.log("Desbloqueando Interfaz");
    document.getElementById( 'loading-static' ).style.display = 'none';
}

function showErrorMessage(mensaje="Ha ocurrido un error inesperado en el servidor", titulo="Error") {
    document.getElementById('error-title').innerHTML = titulo;
    document.getElementById('error-message').innerHTML = mensaje;
    document.getElementById( 'error-static' ).style.display = 'flex';
}

function hideErrorMessage() {
    document.getElementById( 'error-static' ).style.display = 'none';
}


async function handleResponse(resp, data, modalName = 'modalEdicion') {
    if (!resp.ok) {
        desbloqueoInterfaz();
        return;
    }

    const parser = new DOMParser();
    const doc = parser.parseFromString(data, 'text/html');

    const headStyles = Array.from(doc.head.querySelectorAll('style, link[rel="stylesheet"]'));
    headStyles.forEach(styleTag => {
        const clone = styleTag.cloneNode(true);
        clone.classList.add('dynamic-style');  // Para identificar y limpiar luego
        document.head.appendChild(clone);
    });

    const allScripts = Array.from(doc.querySelectorAll('script'));
    const forwardConfScripts = allScripts.filter(s => s.type === 'text/dal-forward-conf');
    const normalScripts = allScripts.filter(s => s.type !== 'text/dal-forward-conf');

    normalScripts.forEach(script => script.remove());

    const modalEdicion = document.getElementById(modalName);
    modalEdicion.innerHTML = doc.body.innerHTML;

    const myModal = new bootstrap.Modal(modalEdicion);
    myModal.show();

    if (window.initDalSelect2InModal) {
        modalEdicion.addEventListener('shown.bs.modal', () => {
            window.initDalSelect2InModal(modalEdicion);
        }, { once: true });
    }

    function agregarScript(src, container, esExterno = true, contenido = '') {
        if (esExterno && document.querySelector(`script[src="${src}"]`)) return;
        const newScript = document.createElement('script');
        newScript.classList.add('dynamic-script'); // Para limpiar luego
        if (esExterno) {
            newScript.src = src;
        } else {
            newScript.innerHTML = contenido;
        }
        container.appendChild(newScript);
    }

    normalScripts.forEach(script => {
        if (script.src) {
            try {
                agregarScript(script.src, document.body, true);
            } catch (error) {
                console.error('Error al cargar el script externo', error, script.outerHTML);
            }
        } else {
            try {
                agregarScript(null, modalEdicion, false, script.textContent);
            } catch (error) {
                console.error('Error al cargar el script inline', error, script.outerHTML);
            }
        }
    });

    modalEdicion.addEventListener('hidden.bs.modal', () => {
        // 1) Destruir Select2 si hay jQuery y el plugin está disponible
        var $ = (window.django && django.jQuery) ? django.jQuery : window.jQuery;
        if ($ && $.fn && $.fn.select2) {
            try {   
                $(modalEdicion).find('.select2-hidden-accessible').select2('destroy');
            } catch (e) { /* no-op */ }
        }
        // 2) Limpiar scripts/estilos dinámicos
        const dynamicScripts = document.querySelectorAll('.dynamic-script');
        dynamicScripts.forEach(script => script.remove());
        const dynamicStyles = document.querySelectorAll('.dynamic-style');
        dynamicStyles.forEach(style => style.remove());
        modalEdicion.innerHTML = '';
    }, { once: true });
}

function resetFormModals() {
    // Elimina todos los event listeners previos para evitar duplicados
    const modals = document.getElementsByClassName('formmodal');
    for (let i = 0; i < modals.length; i++) {
        const modal = modals[i];
        // Clona el elemento para eliminar los event listeners existentes
        const newModal = modal.cloneNode(true);
        modal.parentNode.replaceChild(newModal, modal);
    }

    // Agrega los nuevos event listeners
    const updatedModals = document.getElementsByClassName('formmodal');
    for (let i = 0; i < updatedModals.length; i++) {
        updatedModals[i].addEventListener('click', async function(e) {
            try {
                e.preventDefault();
                const nhref = updatedModals[i].getAttribute('nhref');
                if (!nhref) return;
                bloqueoInterfaz();
                const resp = await fetch(nhref, {
                    method: 'GET',  // Especifica el método si no es POST
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'  // Para manejar cookies en sesiones autenticadas
                });
                if (!resp.ok) {
                    desbloqueoInterfaz();
                    // Manejo de errores del servidor (400, 500, etc.)
                    if (resp.status === 500) {
                        const errorData = await resp.json();
                        showErrorMessage(errorData.mensaje || 'Error interno del servidor. Por favor, inténtelo más tarde.');
                    } else if (resp.status >= 400) {
                        showErrorMessage('Error interno del servidor. Por favor, inténtelo más tarde.');
                    } else {
                        showErrorMessage(`Error inesperado (${resp.status}).`);
                    }
                }

                const data = await resp.text();
                const modal = document.querySelector('.modal.show');
                if (modal) {
                    const modalBS = bootstrap.Modal.getInstance(modal);
                    modalBS.hide();
                }
                handleResponse(resp, data);
                desbloqueoInterfaz();
            } catch {
                console.log('Error al cargar el formulario');
                desbloqueoInterfaz();
            }
        });
    }
}

resetFormModals();

document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("mainForm");
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            submitModalForm1('mainForm');
        });
    }
});

const submitModalForm1 = async (formid = 'modalForm1', showError = true) => {
    const form = document.getElementById(formid);
    form.classList.add('was-validated');

    if (!form.checkValidity()) return;

    if (typeof beforeSubmitModalForm1 === 'function') {
        desbloqueoInterfaz();
        const continuar = await beforeSubmitModalForm1(form);
        if (!continuar) {
            form.classList.remove('was-validated');
            return;
        }
    }

    bloqueoInterfaz();

    try {
        const submitButton = event.submitter; // Captura el botón que disparó el envío
        const formData = new FormData(form); // Crear los datos del formulario

        if (submitButton && submitButton.name) {
            formData.append(submitButton.name, submitButton.value); // Agregar manualmente el botón submit
        }
        const resp = await fetch(form.getAttribute('action'), {
            method: 'POST',
            body: formData,
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        });

        // Manejo de errores del servidor (400, 500, etc.)
        if (!resp.ok) {
            desbloqueoInterfaz();
            if (resp.status === 400) {
                const errorData = await resp.json();
                if (errorData.forms) {
                    // Del formulario borra todos los elementos con clase field-error-message
                    form.querySelectorAll('.field-error-message').forEach(message => message.remove());
                    // Recorre los errores y los agrega al formulario
                    for (const [field, errors] of Object.entries(errorData.forms)) {
                        const fieldElement = form.querySelector(`[name="${field}"]`);
                        if (fieldElement) {
                            const parent = fieldElement.parentElement;
                            const divError = document.createElement('div');
                            divError.className = 'field-error-message text-danger';
                            if (parent) {
                                errors.forEach(error => {
                                    const message = document.createElement('small');
                                    message.className = 'text-danger fw-bold';
                                    message.innerText = '* ' + error;
                                    divError.appendChild(message);
                                });
                                parent.appendChild(divError);
                            }
                        }
                    }
                    form.classList.remove('was-validated');
                }
                if (showError) showErrorMessage(errorData.mensaje || 'Error de validación en el formulario');
            } else if (resp.status >= 500) {
                const errorData = await resp.json();
                if (showError) showErrorMessage(errorData.mensaje || 'Error interno del servidor. Por favor, inténtelo más tarde.');
            } else {
                if (showError) showErrorMessage(`Error inesperado (${resp.status}).`);
            }
            return;
        }

        const data = await resp.json();

        if (data.result === "ok") {
            if (data.popup) {
                // Llama a la función en la ventana opener para actualizar el select
                if (window.opener && typeof window.opener.dismissAddPopup === "function") {
                    window.opener.dismissAddPopup(data.pk, data.repr, data.field_id);
                }
                // Cierra este popup
                window.close();
                return;
            }

            if (data.redirected) {
                try {
                    const currentUrl = window.location.href;
                    if (currentUrl === data.url) {
                        location.reload();
                    } else {
                        location.href = data.url;
                    }
                } catch {
                    window.location.replace(data.url);
                }
            } else {
                const myModal = bootstrap.Modal.getInstance(document.getElementById('modalEdicion'));
                if (myModal) myModal.hide();
                desbloqueoInterfaz();
                return data;
            }
        } else if (data.result === "error") {
            if (data.form) {
                try {
                    const contentModalForm = document.getElementById('form-render-modal');
                    contentModalForm.innerHTML = data.form;
                    // Vuelve a inicializar los select2 de DAL dentro del modal abierto
                    if (window.initDalSelect2InModal) {
                        const modal = document.getElementById('modalEdicion');
                        window.initDalSelect2InModal(modal);
                    }

                    form.classList.remove('was-validated');
                } catch {
                    console.log('No se pudo actualizar el formulario');
                }
            }
            desbloqueoInterfaz();
            if (showError) showErrorMessage(data.mensaje || 'Ha ocurrido un error inesperado en el servidor');
            return data;
        }
    } catch (error) {
        // Manejo de excepciones (error de red u otros)
        desbloqueoInterfaz();
        if (showError) {
            const mensaje = 'Error de red o servidor no disponible. Por favor, inténtelo más tarde.\n\n' +
                            (error?.message ? `Detalles técnicos: ${error.message}` : '');
            showErrorMessage(mensaje);
        }
        console.error('Error inesperado:', error);
    }
};

// Inicializar Select2 en modales
// Esta función se llama automáticamente al cargar el modal o al abrir un modal existente
window.initDalSelect2InModal = function (modalElOrSelector) {
    // 1) No jQuery => no hacer nada
    var hasDjQuery = (window.django && django.jQuery);
    var $ = hasDjQuery ? django.jQuery : window.jQuery;
    if (!$) return;

    // 2) Scope: el modal que pasas; si no pasas, usa el modal visible
    var $scope = modalElOrSelector ? $(modalElOrSelector) :
               ($('.modal.show').length ? $('.modal.show') : $(document.body));

    var $modal = $scope.hasClass('modal') ? $scope : $scope.closest('.modal');
    var $dp = $modal.length ? $modal : $(document.body);

    $scope.find('[data-autocomplete-light-function="select2"]').each(function () {
        var $el = $(this);

        // dropdownParent: modal más cercano; si no hay, body
        if ($modal.length && $modal.attr('id') && !$el.attr('data-dropdown-parent')) {
            $el.attr('data-dropdown-parent', '#' + $modal.attr('id'));
        }

        if ($el.hasClass('select2-hidden-accessible')) {
            try { $el.select2('close'); } catch(e) {}
            try { $el.select2('destroy'); } catch(e) {}
        }

        // Evitar re‑inicializar
        //if ($el.hasClass('select2-hidden-accessible')) return;

        // Placeholder: data-placeholder > separator > placeholder > default
        var ph = $el.attr('data-placeholder') ||
                $el.attr('separator') ||
                $el.attr('placeholder') ||
                'Seleccione una opción';

        // Asegurar opciones vía data-* para DAL
        if (!$el.attr('data-placeholder')) $el.attr('data-placeholder', ph);
        if (!$el.attr('data-allow-clear')) $el.attr('data-allow-clear', 'true');

        // 3) Inicializar con DAL si está disponible
        var initialized = false;
        if (typeof window.__dal__initialize === 'function') {
            window.__dal__initialize(this);
            initialized = $el.hasClass('select2-hidden-accessible');
        } else if (window.yl && yl.functions && typeof yl.functions.select2 === 'function') {
            yl.functions.select2($, this); // fallback DAL
            initialized = $el.hasClass('select2-hidden-accessible');
        }

        // 4) Si DAL no lo dejó inicializado, se realiza manualmente (si existe Select2)
        if (!initialized && $.fn && $.fn.select2) {
            $el.select2({
                placeholder: ph,
                allowClear: true,
                language: 'es',
                dropdownParent: $dp.length ? $dp : $(document.body)
            });
        }
        // 5) Asegurar que el input de búsqueda tenga el foco al abrir
        $el.off('select2:open.autofocus')
        .on('select2:open.autofocus', function () {
            setTimeout(function () {
            var input = document.querySelector('.select2-container--open .select2-search__field');
            if (input) input.focus();
            }, 0);
        });
    });
};

// Bloquear la interfaz al enviar un formulario
// Get all form
const forms = document.getElementsByTagName('form');
for (let i = 0; i < forms.length; i++) {
    forms[i].addEventListener('submit', function(e) {
        bloqueoInterfaz();
    })
}


ready(function(){
    // Inicializar tooltips de Bootstrap 5
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
});


