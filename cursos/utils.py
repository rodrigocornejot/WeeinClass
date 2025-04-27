from datetime import timedelta
import calendar

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

def crear_asistencias_para_matricula(matricula):
    from .models import Asistencia
    dias_a_numeros = {nombre: i for i, nombre in enumerate(calendar.day_name)}
    dias_clase = matricula.dias  # Usamos los días seleccionados desde la matrícula
    dias_seleccionados = [dias_a_numeros[d.capitalize()] for d in dias_clase]

    fecha = matricula.fecha_inicio
    asistencias_creadas = 0
    limite = 3 if matricula.modalidad == "full_day" else 6

    while asistencias_creadas < limite:
        if fecha.weekday() in dias_seleccionados:
            Asistencia.objects.create(
                fecha=fecha,
                alumno=matricula.alumno,
                curso=matricula.curso,
                presente=False  # inicial por defecto
            )
            asistencias_creadas += 1
        fecha += timedelta(days=1)
