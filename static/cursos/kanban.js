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
