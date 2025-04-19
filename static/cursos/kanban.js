window.actualizarEstado = function(tareaId, nuevoEstado) {
    fetch(`${window.actualizarTareaBase}${tareaId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken
        },
        body: JSON.stringify({ estado: nuevoEstado })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("No se pudo actualizar la tarea.");
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            console.log('Estado actualizado');
            location.reload();
        }
    })
    .catch(error => {
        console.error("Error al actualizar la tarea:", error);
    });
};
