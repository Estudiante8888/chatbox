// Variables globales
let programaEnEdicion = null;

// Inicialización cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    configurarEventos();
});

function configurarEventos() {
    // Configurar envío del formulario
    const form = document.getElementById('programaForm');
    form.addEventListener('submit', manejarSubmit);
    
    // Configurar botón actualizar
    document.getElementById('btnActualizar').addEventListener('click', actualizarPrograma);
    
    // Configurar botón cancelar
    document.getElementById('btnCancelar').addEventListener('click', cancelarEdicion);
    
    // Configurar modal de eliminación
    document.getElementById('btnConfirmarEliminar').addEventListener('click', confirmarEliminacion);
}

function manejarSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    formData.append('action', 'agregar');
    
    fetch('/programas', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarAlerta('success', data.message);
            limpiarFormulario();
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            mostrarAlerta('danger', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('danger', 'Error de conexión');
    });
}

function cargarPrograma(id) {
    fetch(`/obtener_programa/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Cargar datos en el formulario
            document.getElementById('codcarrera').value = data.programa.codcarrera;
            document.getElementById('descarrera').value = data.programa.descarrera;
            
            // Cambiar estado de botones
            document.getElementById('codcarrera').readOnly = true;
            document.getElementById('btnAgregar').disabled = true;
            document.getElementById('btnActualizar').disabled = false;
            document.getElementById('btnCancelar').style.display = 'block';
            
            // Guardar ID del programa en edición
            programaEnEdicion = id;
            
            // Resaltar fila en la tabla
            resaltarFila(id);
            
            mostrarAlerta('info', 'Programa cargado para edición');
        } else {
            mostrarAlerta('danger', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('danger', 'Error al cargar el programa');
    });
}

function actualizarPrograma() {
    if (!programaEnEdicion) return;
    
    const formData = new FormData();
    formData.append('codcarrera', document.getElementById('codcarrera').value);
    formData.append('descarrera', document.getElementById('descarrera').value);
    formData.append('action', 'actualizar');
    
    fetch('/programas', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarAlerta('success', data.message);
            cancelarEdicion();
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            mostrarAlerta('danger', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('danger', 'Error al actualizar');
    });
}

function cancelarEdicion() {
    // Limpiar formulario
    limpiarFormulario();
    
    // Restaurar estado de botones
    document.getElementById('codcarrera').readOnly = false;
    document.getElementById('btnAgregar').disabled = false;
    document.getElementById('btnActualizar').disabled = true;
    document.getElementById('btnCancelar').style.display = 'none';
    
    // Limpiar programa en edición
    programaEnEdicion = null;
    
    // Quitar resaltado de filas
    quitarResaltadoFilas();
}

function eliminarPrograma(id) {
    programaEnEdicion = id;
    const modal = new bootstrap.Modal(document.getElementById('modalEliminar'));
    modal.show();
}

function confirmarEliminacion() {
    if (!programaEnEdicion) return;
    
    fetch(`/eliminar/${programaEnEdicion}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEliminar'));
        modal.hide();
        
        if (data.success) {
            mostrarAlerta('success', data.message);
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            mostrarAlerta('danger', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('danger', 'Error al eliminar');
    })
    .finally(() => {
        programaEnEdicion = null;
    });
}

function limpiarFormulario() {
    document.getElementById('programaForm').reset();
}

function mostrarAlerta(tipo, mensaje) {
    const alertContainer = document.getElementById('alertContainer');
    const alertHTML = `
        <div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.innerHTML = alertHTML;
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
        const alert = alertContainer.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

function resaltarFila(id) {
    // Quitar resaltado previo
    quitarResaltadoFilas();
    
    // Resaltar fila actual
    const tabla = document.getElementById('tablaProgramas');
    if (tabla) {
        const filas = tabla.querySelectorAll('tbody tr');
        filas.forEach(fila => {
            const idFila = fila.querySelector('td:first-child strong').textContent;
            if (idFila == id) {
                fila.classList.add('table-warning');
            }
        });
    }
}

function quitarResaltadoFilas() {
    const tabla = document.getElementById('tablaProgramas');
    if (tabla) {
        const filas = tabla.querySelectorAll('tbody tr');
        filas.forEach(fila => {
            fila.classList.remove('table-warning');
        });
    }
}

// Función para filtrar tabla (opcional - mejora adicional)
function filtrarTabla(termino) {
    const tabla = document.getElementById('tablaProgramas');
    if (!tabla) return;
    
    const filas = tabla.querySelectorAll('tbody tr');
    let contadorVisibles = 0;
    
    filas.forEach(fila => {
        const texto = fila.textContent.toLowerCase();
        const coincide = texto.includes(termino.toLowerCase());
        fila.style.display = coincide ? '' : 'none';
        if (coincide) contadorVisibles++;
    });
    
    // Actualizar contador
    document.getElementById('totalProgramas').textContent = `Mostrando: ${contadorVisibles}`;
}