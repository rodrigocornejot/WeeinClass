function actualizarEstado(tareaId, nuevoEstado) {
    const urlBase = "{% url 'actualizar_estado_tarea' 0 %}".replace('/0/', '');
    fetch(`${urlBase}/{tareaId}/`, {
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

// Utilidad para obtener el token CSRF si no estás usando {{ csrf_token }} directamente en JS
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : '';
}

