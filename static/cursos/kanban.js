function actualizarEstado(tareaId, nuevoEstado) {
    fetch(`/cursos/actualizar_estado_tarea/${tareaId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({ estado: nuevoEstado })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Estado actualizado');
                // Aquí podrías mover el elemento al nuevo estado visualmente
            location.reload(); // Esto recarga la página (opcional)
        }
    });
}

function delegarTarea(tareaId) {
    const areaSeleccionada = document.getElementById('delegar_a').value;

    fetch(`/cursos/delegar_tarea/${tareaId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ delegar_a: areaSeleccionada })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert("Error al delegar la tarea");
        }
    });
}

// Utilidad para obtener el token CSRF si no estás usando {{ csrf_token }} directamente en JS
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : '';
}

