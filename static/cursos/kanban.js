function actualizarEstado(tareaId, nuevoEstado) {
    fetch(`${window.actualizarTareaBase}${tareaId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({ estado: nuevoEstado })
    })
    .then(response => {
        if (response.ok) {
            throw new Error("No se pudo actualizar la tarea.");
        }
        response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            console.log('Estado actualizado');
                // Aquí podrías mover el elemento al nuevo estado visualmente
            location.reload(); // Esto recarga la página (opcional)
        }
    });
}

// Utilidad para obtener el token CSRF si no estás usando {{ csrf_token }} directamente en JS
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : '';
}

