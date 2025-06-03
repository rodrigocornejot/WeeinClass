import json
import openpyxl
import traceback
import calendar

from django.core.paginator import Paginator
from rest_framework.generics import ListAPIView
from rest_framework import viewsets
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Alumno, Curso, Nota, Matricula, Clase, Tarea, Area, Evento, UnidadCurso, AsistenciaUnidad
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from .forms import CursoForm, MatriculaAdminForm, MatriculaForm, NotaForm
from django.db.models import Count, Avg, Q
from .forms import AlumnoForm
from datetime import date, timedelta, datetime
from django.contrib.auth.forms import AuthenticationForm
from openpyxl.utils import get_column_letter
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.utils import timezone, dateparse
from .utils import obtener_datos_dashboard
from .serializers import MatriculaSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from django.views import View
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import crear_asistencias_para_matricula  # Importar la función
import ast
from collections import defaultdict

CURSO_COLORES = {
    'VARIADORES DE FRECUENCIA': '#33FF57',
    'REDES INDUSTRIALES': '#b328ca',
    'PLC NIVEL 1': '#FF5733',
    'PLC NIVEL 2': '#FFFF00',
    'INSTRUMENTACION INDUSTRIAL': '#28CAAD',
    'PLC LOGO! V8': '#285ECA'
}

DIAS_SEMANA = {
    0: 'lunes',
    1: 'martes',
    2: 'miercoles',
    3: 'jueves',
    4: 'viernes',
    5: 'sabado',
    6: 'domingo'
}

MODALIDAD_CHOICES = (
    ('extendida', 'Extendida'),
    ('full_day', 'Full Day'),
)

MODALIDAD_CONFIG = {
    'full_day': {
        'num_weeks': 3,
        'days_of_week': ['domingo'],
        'hora_inicio': '09:00',
        'hora_fin': '18:00',
    },
    'intensivo': {
        'num_weeks': 3,
        'days_of_week': ['lunes','miercoles','viernes'],
        'hora_inicio': '09:00',
        'hora_fin': '13:00',
    },
    'extendida': {
        'num_weeks': 6,
        'days_of_week': ['sabado'],
        'hora_inicio': '09:00',
        'hora_fin': '13:00',
    },
}

def calendario_matriculas(request):
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")

    print(f"🔍 Petición recibida: start={start}, end={end}")

    if not start or not end:
        return JsonResponse([], safe=False)

    start_date = datetime.fromisoformat(start[:10])
    end_date = datetime.fromisoformat(end[:10])

    matriculas = Matricula.objects.filter(fecha_inicio__range=(start_date, end_date))

    eventos = []

    for matricula in matriculas:
        alumno = matricula.alumno.nombre
        curso = matricula.curso.nombre
        modalidad = matricula.modalidad
        fecha_inicio = matricula.fecha_inicio
        color = CURSO_COLORES.get(curso, "#007bff")  # Color por defecto si no se encuentra el curso

        print(f"Matrícula: {alumno} - {curso} ({modalidad})")
        print(f"📌 Días (JSONField): {matricula.dias}")
        print(f"📌 Días de estudio (CharField): {matricula.dias_estudio}")

        # 🔹 FULL DAY: Genera 3 clases, una por semana
        if modalidad == "full_day":
            for i in range(3):
                eventos.append({
                    "id": matricula.id,
                    "title": f"{alumno} - {curso}",
                    "start": (fecha_inicio + timedelta(weeks=i)).strftime("%Y-%m-%d"),
                    "color": color,
                    "textColor": "black",
                    "extendedProps": {
                        "curso_id" : matricula.curso.id,
                        "dia": (fecha_inicio + timedelta(weeks=i)).strftime("%Y-%m-%d"),
                        "matricula_id": matricula.id
                    }
                })

        # 🔹 EXTENDIDA: Usar días_estudio o dias si están vacíos
        elif modalidad == "extendida":
            dias_elegidos = []

            # 🟢 1️⃣ Intentamos usar `dias` si tiene valores
            if matricula.dias:
                dias_elegidos = matricula.dias  # Suponiendo que es una lista de strings

            # 🟠 2️⃣ Si `dias` está vacío, intentamos usar `dias_estudio`
            elif matricula.dias_estudio:
                dias_elegidos = [dia.strip().lower() for dia in matricula.dias_estudio.split(',')]

            # 🔴 3️⃣ Si sigue vacío, mostramos error
            if not dias_elegidos:
                print(f"⚠️ ERROR: {alumno} en {curso} no tiene días válidos.")
                continue

            # 🔹 Convertimos los días a índices de la semana
            dias_indices = [idx for idx, nombre in DIAS_SEMANA.items() if nombre in dias_elegidos]

            print(f"📌 Días seleccionados: {dias_elegidos}")
            print(f"📌 Días en índices: {dias_indices}")

            if not dias_indices:
                print(f"⚠️ ERROR: {alumno} en {curso} tiene días inválidos.")
                continue

            fecha_actual = fecha_inicio
            clases_generadas = 0

            while clases_generadas < 6:
                if fecha_actual.weekday() in dias_indices:
                    eventos.append({
                        "id": matricula.id,
                        "title": f"{alumno} - {curso}",
                        "start": fecha_actual.strftime("%Y-%m-%d"),
                        "color": color,
                        "textColor": "black",
                        "extendedProps": {
                            "curso_id": matricula.curso.id,  # O el identificador del curso
                            "dia": fecha_actual.strftime("%Y-%m-%d"),  # O el día correspondiente
                            "matricula_id": matricula.id  # Identificador de matrícula
                        }

                    })
                    clases_generadas += 1
                fecha_actual += timedelta(days=1)

        else:
            print(f"⚠️ Modalidad desconocida '{modalidad}' para {alumno} en {curso}.")

    print("Eventos enviados a FullCalendar:", eventos)

    return JsonResponse(eventos, safe=False)

# Formulario de login (puedes usar el AuthenticationForm de Django, pero aquí un ejemplo sencillo)
class LoginForm(forms.Form):
    username = forms.CharField(label="Nombre de usuario")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

@csrf_protect
def mi_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            print("Usuario autenticado:", user.username)
            print("Grupos:", list(user.groups.values_list("name", flat=True)))

            # Redirigir según rol
            if user.is_superuser or user.groups.filter(name='Administradores').exists():
                print("Redirigiendo a: menu_admin")
                return redirect("menu_admin")
            elif user.groups.filter(name='Profesores').exists():
                print("Redirigiendo a: menu_admin (profesor)")
                return redirect("menu_admin")
            elif user.groups.filter(name='Marketing').exists():
                print("Redirigiendo a: menu_admin (marketing)")
                return redirect("menu_admin")
            else:
                print("Redirigiendo a: home")
                return redirect("home")
        else:
            print("Formulario invalido")
            print(form.errors)
            return render(request, "registration/login.html", {"form": form})
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})

def lista_alumnos(request):
    alumnos = Alumno.objects.all()
    return render(request, 'cursos/lista_alumnos.html', {'alumnos': alumnos})

def es_profesor(user):
    return user.is_superuser or user.groups.filter(name='Profesores').exists()

@login_required
@user_passes_test(es_profesor)
def vista_calendario(request):
    cursos = Curso.objects.all()

    # Crear una lista con los nombres de los cursos y sus colores
    cursos_colores = [(curso.nombre, CURSO_COLORES.get(curso.nombre, '#000000')) for curso in cursos]

    # Pasar la lista de cursos con sus colores al contexto de la plantilla
    context = {
        'cursos_colores': cursos_colores,
    }
    return render(request, 'cursos/calendario.html')

def es_admin(user):
    return user.is_superuser or user.groups.filter(name='Administradores').exists()

@login_required
def menu_admin(request):
    grupo_usuario = request.user.groups.first()

    if grupo_usuario:
        if grupo_usuario.name == 'Profesores':
            tareas = Tarea.objects.filter(area_asignada__nombre='Profesores')
        elif grupo_usuario.name == 'Marketing':
            pendientes = Tarea.objects.filter(area_asignada__nombre='Marketing')
        else:
            tareas = Tarea.objects.all()

    return render(request, 'menu_admin.html', {
        'tareas': tareas,
        'es_profesor': grupo_usuario.name == 'Profesores' if grupo_usuario else False,
        'es_marketing': grupo_usuario.name == 'Marketing' if grupo_usuario else False,
    })
    return render(request, 'cursos/menu_admin.html', context)

def crear_curso(request):
    if request.method == 'POST':
        print("Datos recibidos en POST:", request.POST)

        form = CursoForm(request.POST)
        if form.is_valid():

            nombre = form.cleaned_data.get('nombre') or request.POST.get('nuevo_curso')
            fecha = form.cleaned_data.get('fecha')
            horario = form.cleaned_data.get('horario')
            duracion = form.cleaned_data.get('duracion')
            profesor = form.cleaned_data.get('profesor')

            if not nombre or not fecha or not horario or not duracion or not profesor:
                print("Error: Faltan datos obligatorios para el curso")
                return render(request, 'cursos/crear_curso.html', {'form': form})

            curso_existente = Curso.objects.filter(nombre=nombre, fecha=fecha).first()

            if curso_existente:
                print("El curso ya existe:", curso_existente)
                return redirect('lista_cursos')

            # Crear el curso si no existe
            curso = Curso.objects.create(
                nombre=nombre,
                fecha=fecha,
                horario=horario,
                duracion=duracion,
                profesor=profesor
            )
            print("Curso creado:", curso)
            return redirect('lista_cursos')
        else:
            print("Errores en el formulario:", form.errors)
    else:
        form = CursoForm()

    return render(request, 'cursos/crear_curso.html', {'form': form})


@login_required
def lista_cursos(request):
    cursos = Curso.objects.all()
    matriculas = Matricula.objects.all()
    return render(request, 'cursos/lista_cursos.html', {'cursos': cursos})

def lista_matriculas(request):
    # Obtener todas las matrículas
    matriculas_qs = Matricula.objects.all()

    # Paginación
    paginator = Paginator(matriculas_qs, 10)  # Mostrar 10 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Obtener todos los cursos para el filtro
    cursos = Curso.objects.all()

    # Pasar los datos a la plantilla
    return render(request, 'cursos/lista_matriculas.html', {
        'matriculas': page_obj,
        'cursos': cursos
    })


def registrar_asistencia_unidad(request):
    matriculas = Matricula.objects.filter(estado='activa')
    unidades = UnidadCurso.objects.all()

    # Organizar las unidades por curso
    unidades_por_curso = {}
    for unidad in unidades:
        curso = unidad.curso
        if curso not in unidades_por_curso:
            unidades_por_curso[curso] = []
        unidades_por_curso[curso].append(unidad)

    # Crear el diccionario de asistencias
    asistencias_dict = {}

    for asistencia in AsistenciaUnidad.objects.all():
        matricula_id = asistencia.matricula.id
        unidad_id = asistencia.unidad.id

        if matricula_id not in asistencias_dict:
            asistencias_dict[matricula_id] = {}

        asistencias_dict[matricula_id][unidad_id] = asistencia.completado

    if request.method == 'POST':
        for matricula in matriculas:
            for unidad in unidades:
                key = f"asistencia_{matricula.id}_{unidad.id}"
                completado = key in request.POST
                asistencia, created = AsistenciaUnidad.objects.get_or_create(
                    matricula=matricula,
                    unidad=unidad,
                    defaults={'completado': completado}
                )
                if not created:
                    asistencia.completado = completado
                    asistencia.save()
        return redirect('registrar_asistencia_unidad')

    return render(request, 'cursos/registrar_asistencia_unidad.html', {
        'matriculas': matriculas,
        'unidades_por_curso': unidades_por_curso,  # Aquí se pasa el diccionario
        'asistencias_dict': asistencias_dict,
    })

def lista_asistencia(request):
    asistencias = AsistenciaUnidad.objects.select_related(
        'matricula__alumno', 'matricula__curso', 'unidad'
    ).order_by('matricula__curso__nombre', 'matricula__alumno__nombre', 'unidad__numero')
    return render(request, 'cursos/lista_asistencia.html', {'asistencias': asistencias})

def ver_asistencia_unidad(request, curso_id):
    # Lógica para obtener las asistencias por unidad
    # Ejemplo:
    asistencias = AsistenciaUnidad.objects.filter(curso_id=curso_id)
    unidades = UnidadCurso.objects.filter(curso_id=curso_id).order_by('id')

    return render(request, 'cursos/ver_asistencia_unidad.html', {
        'asistencias': asistencias,
        'unidades': unidades
    })

def guardar_asistencias(request, curso_id):
    if request.method == 'POST':
        unidades = UnidadCurso.objects.filter(curso_id=curso_id)
        matriculas = Matricula.objects.filter(curso_id=curso_id)

        for matricula in matriculas:
            for unidad in unidades:
                checkbox_name = f'asistencia_{matricula.id}_{unidad.id}'
                completado = checkbox_name in request.POST

                asistencia, created = AsistenciaUnidad.objects.get_or_create(
                    matricula=matricula,
                    unidad=unidad,
                    defaults={'completado': completado}
                )

                if not created:
                    asistencia.completado = completado
                    asistencia.save()

        return redirect('registrar_asistencia_unidad', curso_id=curso_id)

def registrar_nota(request):
    alumnos = Alumno.objects.all()
    context = {'alumnos': alumnos}
    if request.method == 'POST':
        form = NotaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_notas')
    else:
        alumnos = Alumno.objects.filter(matricula__asistencia=True).distinct()
        form = NotaForm()

    return render(request, 'cursos/registrar_nota.html', {'form': form, 'alumnos': alumnos})

def lista_notas(request):
    alumno_id = request.GET.get("alumno_id")  # O request.POST.get("alumno_id") según el caso

    if alumno_id:
        try:
            alumno_id = int(alumno_id)
            notas = Nota.objects.filter(matricula__alumno=alumno_id)
        except ValueError:
            notas = Nota.objects.none()  # Si no es un número válido, devuelve lista vacía
    else:
        notas = Nota.objects.all()  # Opcional: Mostrar todas las notas si no hay filtro

    return render(request, 'cursos/lista_notas.html', {'notas': notas})

def detalle_matricula(request, matricula_id, fecha):
    try:
        matricula = Matricula.objects.get(id=matricula_id)
        print(f"Matricula encontrada: {matricula}")
        print(f"Alumno asociado: {matricula.alumno}")

        data = {
            "matricula_id": matricula.id,
            "nombre": matricula.alumno.nombre,
            "turno": matricula.turno,
            "saldo": matricula.saldo_pendiente,
        }
        return JsonResponse(data, safe=False)

    except Matricula.DoesNotExist:
        return JsonResponse({"error": "Matricula no existe"}, status=404)
    except Exception as e:
        print(f"Error al procesar la matrícula {matricula_id} para la fecha {fecha}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def registrar_matricula(request):
    if request.method == 'POST':
        print("Se recibió una solicitud POST")
        print("Contenido de request.POST:", request.POST)
        form = MatriculaForm(request.POST)

        if form.is_valid():
            print("El formulario es válido")
            matricula = form.save(commit=False)  # No guarda aún

            # Modalidad y fecha de inicio
            modalidad = matricula.modalidad.lower()
            fecha_inicio = matricula.fecha_inicio

            print(f"Modalidad: {modalidad}")
            print(f"Fecha de inicio: {fecha_inicio}")

            if not fecha_inicio:
                return HttpResponseBadRequest("Fecha de inicio inválida")

            # Obtener días elegidos desde el formulario
            dias_seleccionados = request.POST.getlist("dias_estudio")
            print("Días seleccionados:", dias_seleccionados)

            if not dias_seleccionados:
                return render(request, 'error.html', {'mensaje': 'Debe seleccionar al menos un día de estudio'})

            # Guardar los días en JSONField
            matricula.dias = dias_seleccionados
            matricula.save()

            dias_a_numeros = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5,
                            "domingo": 6}
            # Generar fechas de clases según modalidad
            fechas_clases = []

            if modalidad == "full_day":
                fechas_clases = [fecha_inicio + timedelta(weeks=i) for i in range(3)]

            elif modalidad == "extendida":
                if not dias_seleccionados:
                    return render(request, 'error.html',
                                  {'mensaje': 'Debe seleccionar días para la modalidad extendida'})

                for i in range(2):
                    for dia in dias_seleccionados:
                        dia = dia.lower()
                        print(f"Procesando dia: {dia}")

                        if dia not in dias_a_numeros:
                            print(f"⚠️ ERROR: Día inválido recibido: {dia}")
                            continue

                        num_dia = dias_a_numeros[dia]
                        fecha_clase = fecha_inicio + timedelta(days=(i * 7) + num_dia)
                        print(f"Clase creada para {fecha_clase.strftime('%Y-%m-%d')}")
                        fechas_clases.append(fecha_clase)
                        print("Fechas generadas:", fechas_clases)

            else:
                return render(request, 'error.html', {'mensaje': 'Modalidad inválida'})

            # Crear clases en la BD y sincronizar las asistencias
            for fecha_clase in fechas_clases:
                clase = Clase.objects.create(
                    curso=matricula.curso,
                    fecha=fecha_clase
                )
                print(f"Clase creada para {fecha_clase}")

            unidades = UnidadCurso.objects.filter(curso=matricula.curso).order_by('numero')
            if not unidades.exists():
                print("⚠️ Este curso no tiene unidades registradas.")
            else:
                for unidad in unidades:
                    AsistenciaUnidad.objects.create(
                        matricula=matricula,
                        unidad=unidad,
                        tema_realizado="",  # Vacío al inicio
                        realizado=False
                    )
                    print(f"Unidad {unidad.numero} registrada para la matrícula")

            return redirect('lista_matriculas')

    else:
        form = MatriculaForm()

    return render(request, 'cursos/registrar_matricula.html', {'form': form})

def obtener_datos_dashboard(curso_id=None):
    cursos_qs = Curso.objects.all()
    if curso_id:
        cursos_qs = cursos_qs.filter(id=curso_id)

    alumnos_por_curso = cursos_qs.annotate(
        total_alumnos=Count('matricula')
    ).values('nombre', 'total_alumnos')

    promedio_notas = Nota.objects.filter(matricula__curso__in=cursos_qs).values(
        'matricula__curso__nombre'
    ).annotate(promedio=Avg('nota'))

    total_asistencias = AsistenciaUnidad.objects.count()
    asistencias_presentes = AsistenciaUnidad.objects.filter(completado=True).count()
    porcentaje_asistencia = (asistencias_presentes / total_asistencias * 100) if total_asistencias else 0

    return {
        'alumnos_por_curso': list(alumnos_por_curso),
        'promedio_notas': list(promedio_notas),
        'porcentaje_asistencia': porcentaje_asistencia,
    }

def export_dashboard_excel(request):
    # Creamos un workbook y una hoja de cálculo
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Dashboard"

    # Definimos encabezados
    headers = ["Curso", "Total Alumnos", "Promedio de Notas"]
    ws.append(headers)

    # Consulta de datos: alumnos por curso y promedio de notas
    alumnos_por_curso = Curso.objects.annotate(total_alumnos=Count('alumnos')).values_list('nombre', 'total_alumnos')
    promedio_notas_qs = Nota.objects.values('curso__nombre').annotate(promedio=Avg('calificacion'))
    notas_dict = {n['curso__nombre']: n['promedio'] for n in promedio_notas_qs}

    # Rellenamos la hoja con los datos
    for curso in alumnos_por_curso:
        nombre, total_alumnos = curso
        promedio = notas_dict.get(nombre, 0)
        ws.append([nombre, total_alumnos, promedio])

    # Ajustamos el ancho de las columnas
    for i, column in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = 20

    # Preparamos la respuesta HTTP con el archivo Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="dashboard.xlsx"'
    wb.save(response)
    return response

def dashboard(request):
    context = obtener_datos_dashboard(request.GET.get('curso'))
    return render(request, 'cursos/dashboard.html', context)

def registrar_alumnos(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        correo = request.POST.get('correo')
        telefono = request.POST.get('telefono')

        # Verifica que los campos estén presentes
        if nombre and correo and telefono:
            Alumno.objects.create(
                nombre=nombre,
                correo=correo,
                telefono=telefono
            )
            return redirect('lista_alumnos')  # o donde quieras redirigir

    return render(request, 'cursos/registrar_alumnos.html')

def kanban(request):
    ahora = timezone.now()
    user = request.user

    # Obtener área según grupo
    if user.groups.filter(name='Marketing').exists():
        area_name = 'Marketing'
    elif user.groups.filter(name='Profesores').exists():
        area_name = 'Profesores'
    else:
        area_name = None

    # Tareas pendientes y no vencidas
    tareas_pendientes = Tarea.objects.filter(completado=False, fecha_vencimiento__gte=ahora)
    # Tareas vencidas y no completadas
    tareas_vencidas = Tarea.objects.filter(completado=False, fecha_vencimiento__lt=ahora)
    # Tareas completadas
    tareas_completadas = Tarea.objects.filter(completado=True)

    if area_name:
        tareas_pendientes = tareas_pendientes.filter(area_asignada__nombre=area_name)
        tareas_vencidas = tareas_vencidas.filter(area_asignada__nombre=area_name)
        tareas_completadas = tareas_completadas.filter(area_asignada__nombre=area_name)

    return render(request, 'cursos/kanban.html', {
        'tareas_pendientes': tareas_pendientes,
        'tareas_vencidas': tareas_vencidas,
        'tareas_completadas': tareas_completadas,
    })

@login_required
def reprogramar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)

    if request.method == 'POST':
        nueva_fecha = request.POST.get('fecha_vencimiento')
        tarea.fecha_vencimiento = timezone.make_aware(
            datetime.strptime(nueva_fecha, '%Y-%m-%d'),
            timezone.get_current_timezone()
        )

        # Si la nueva fecha es futura, quitar la marca de vencida
        if tarea.fecha_vencimiento > timezone.now():
            tarea.vencida = False
        tarea.save()
        return redirect('tareas_vencidas')

    return render(request, 'cursos/reprogramar_tarea.html', {'tarea': tarea})

@login_required
def actualizar_tareas_vencidas(request):
    ahora = timezone.now()
    Tarea.objects.filter(fecha_vencimiento__lt=ahora, vencida=False).update(vencida=True)
    return redirect('kanban')

@login_required
def tareas_vencidas(request):
    if request.user.groups.filter(name='Marketing').exists():
        tareas = Tarea.objects.filter(vencida=True, area_asignada__nombre='Marketing')
    elif request.user.groups.filter(name='Profesores').exists():
        tareas = Tarea.objects.filter(vencida=True, area_asignada__nombre='Profesores')
    else:
        tareas = Tarea.objects.filter(vencida=True)

    return render(request, 'cursos/tareas_vencidas.html', {'tareas': tareas})

def crear_tarea(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        prioridad = request.POST.get('prioridad')
        tiempo_estimado = request.POST.get('tiempo_estimado')
        fecha_vencimiento = request.POST.get('fecha_vencimiento')
        area_asignada = request.POST.get('area_asignada')

        fecha_vencimiento = timezone.make_aware(datetime.strptime(fecha_vencimiento, '%Y-%m-%d'), timezone.get_current_timezone())


        tarea = Tarea.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            tiempo_estimado=tiempo_estimado,
            fecha_vencimiento=fecha_vencimiento,
            area_asignada=Area.objects.get(id=area_asignada)
        )
        return redirect('kanban')
    areas = Area.objects.all()
    return render(request, 'cursos/crear_tarea.html', {'areas': areas})

@csrf_exempt
def actualizar_estado_tarea(request, tarea_id):
    try:
        tarea = Tarea.objects.get(id=tarea_id)
        data = json.loads(request.body)
        tarea_estado = data.get('estado')
        tarea.estado = tarea_estado

        tarea.completado = (tarea_estado == 'Completado')

        tarea.save()
        return JsonResponse({'status': 'success'})
    except Tarea.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'tarea no encontrada'}, status=404)

@login_required
def exportar_tareas_completadas(request):
    tareas = Tarea.objects.filter(estado='completada', vencida=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tareas Completadas"

    headers = ["Título", "Descripción", "Fecha Vencimiento", "Área"]
    ws.append(headers)

    for tarea in tareas:
        ws.append([
            tarea.titulo,
            tarea.descripcion,
            tarea.fecha_vencimiento.strftime("%Y-%m-%d %H:%M"),
            tarea.area_asignada.nombre
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=tareas_completadas.xlsx'
    wb.save(response)
    return response

@login_required
def tareas_completadas(request):
    ahora = timezone.now()
    if request.user.groups.filter(name='Marketing').exists():
        tareas = Tarea.objects.filter(
            completado=True,
            fecha_vencimiento__lt=ahora,
            area_asignada__nombre='Marketing'
        )
    elif request.user.groups.filter(name='Profesores').exists():
        tareas = Tarea.objects.filter(
            completado=True,
            fecha_vencimiento__lt=ahora,
            area_asignada__nombre='Profesores'
        )
    else:
        tareas = Tarea.objects.filter(completado=True, fecha_vencimiento__lt=ahora)

    return render(request, 'cursos/tareas_completadas.html', {'tareas': tareas})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='Administradores').exists())
def kanban_admin(request):
    # lógica para ver todas las tareas
    return render(request, "kanban/kanban_admin.html")

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Profesores').exists())
def kanban_profesor(request):
    # lógica para ver solo tareas del área de profesores
    return render(request, "kanban/kanban_profesor.html")

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Marketing').exists())
def kanban_marketing(request):
    # lógica para ver solo tareas del área de marketing
    return render(request, "kanban/kanban_marketing.html")

@login_required
def menu_admin(request):
    es_admin = request.user.groups.filter(name='Administradores').exists() or request.user.is_superuser
    es_profesor = request.user.groups.filter(name='Profesores').exists()
    es_marketing = request.user.groups.filter(name='Marketing').exists()

    return render(request, 'cursos/menu_admin.html', {
        'es_admin': es_admin,
        'es_profesor': es_profesor,
        'es_marketing': es_marketing,
    })

@csrf_exempt
def actualizar_fecha_evento(request, matricula_id):
    print(f"Recibida solicitud para actualizar matricula ID: {matricula_id}")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Datos recibidos: {data}")
            nueva_fecha_str = data.get('nueva_fecha')

            if not nueva_fecha_str:
                return JsonResponse({'status': 'error', 'message': 'Fecha no proporcionada'}, status=400)

            if 'T' in nueva_fecha_str:
                nueva_fecha = nueva_fecha_str.split('T')[0]

            nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%d').date()
            matricula = Matricula.objects.get(id=matricula_id)
            fecha_original = matricula.fecha_inicio
            matricula.fecha_inicio = nueva_fecha
            matricula.save()

            return JsonResponse({
                'status': 'success',
                'new_fecha': nueva_fecha_str,
                'original_fecha' : str(fecha_original),
            })

        except Matricula.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Matrícula no encontrada'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Error al procesar JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


def eventos_json(request):
    eventos = Evento.objects.all()
    data = []

    for evento in eventos:
        data.append({
            'id': evento.matricula.id,
            'title': f"{evento.curso.nombre} - {evento.alumno.nombre}",
            'start': evento.fecha.isoformat(),
        })

    return JsonResponse(data, safe=False)

def editar_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    if request.method == "POST":
        form = AlumnoForm(request.POST, instance=alumno)
        if form.is_valid():
            form.save()
            return redirect('lista_alumnos')
    else:
        form = AlumnoForm(instance=alumno)
    return render(request, "cursos/editar_alumno.html", {"form": form})

def eliminar_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    alumno.delete()
    return redirect('lista_alumnos')

def editar_matricula(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    if request.method == "POST":
        form = MatriculaForm(request.POST, instance=matricula)
        if form.is_valid():
            form.save()
            return redirect('lista_matriculas')
    else:
        form = MatriculaForm(instance=matricula)
    return render(request, "cursos/editar_matricula.html", {"form": form})

def eliminar_matricula(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    matricula.delete()
    return redirect('lista_matriculas')

