from datetime import timedelta


def obtener_datos_dashboard(curso_id):
    # Simulación de datos, reemplázalo con tu lógica real
    return {
        "curso": curso_id,
        "asistencias": 10,  # Número de asistencias
        "notas_promedio": 15.5,  # Promedio de notas
    }

def generar_fechas(inicio, modalidad):
    if not inicio or not modalidad:
        return []  # Retorna lista vacía si la fecha de inicio no está definida

    modalidad = modalidad.strip().lower()
    print(f"Generando fechas para: {inicio} con modalidad {modalidad}")  # Debugging

    fechas = []
    print(f"Generando fechas para la modalidad: {modalidad} con fecha inicio: {inicio}")

    if modalidad == "Full Day":
        for i in range(3):
            fechas.append((inicio + timedelta(weeks=i)).strftime("%Y-%m-%d"))
            print(f"Fecha generada (Full Day): {fechas[-1]}")

    elif modalidad == "Extendida":
        for i in range(6):
            fechas.append((inicio + timedelta(days=i * 2)).strftime("%Y-%m-%d"))
            print(f"Fecha generada (Extendida): {fechas[-1]}")

    print(f"Fechas generadas: {fechas}")
    return fechas

