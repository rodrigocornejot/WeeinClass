import json
import openpyxl
import traceback
from rest_framework.generics import ListAPIView
from rest_framework import viewsets
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alumno, Curso, Asistencia, Nota, Matricula, Clase
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from .forms import CursoForm, MatriculaAdminForm, MatriculaForm, NotaForm
from django.db.models import Count, Avg, Q
from .forms import AsistenciaForm, AlumnoForm
from datetime import date, timedelta, datetime
from django.contrib.auth.forms import AuthenticationForm
from openpyxl.utils import get_column_letter
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .utils import obtener_datos_dashboard
from .serializers import MatriculaSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from django.views import View

CURSO_COLORES = {
    'VARIADORES DE FRECUENCIA': '#33FF57',
    'REDES INDUSTRIALES': '#5733FF',
    'PLC NIVEL 1': '#FF5733',
    'PLC NIVEL 2': '#FFFF00',
    'INSTRUMENTACION INDUSTRIAL': '#3357FF',
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
                    "title": f"{alumno} - {curso}",
                    "start": (fecha_inicio + timedelta(weeks=i)).strftime("%Y-%m-%d"),
                    "color": color
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
                        "title": f"{alumno} - {curso}",
                        "start": fecha_actual.strftime("%Y-%m-%d"),
                        "color": color,
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

def mi_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirigir según rol
            if user.is_superuser or user.groups.filter(name='Administradores').exists():
                return redirect("menu_admin")
            elif user.groups.filter(name='Profesores').exists():
                return redirect("vista_calendario")
            else:
                return redirect("home")
        else:
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
@user_passes_test(es_admin)

def menu_admin(request):
    return render(request, 'cursos/menu_admin.html')


from django.shortcuts import render, redirect
from .forms import CursoForm
from .models import Curso


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
    matriculas = Matricula.objects.select_related("alumno", "curso").all()
    #matriculas = Matricula.objects.exclude(id__isnull=True)
    data = [
        {
            "id": m.id,
            "alumno": m.alumno.nombre,
            "curso": m.curso.nombre,
            "modalidad": m.get_modalidad_display(),
            "turno": m.get_turno_display(),
            "dias_estudio": m.dias_estudio,
            "saldo_pendiente": float(m.saldo_pendiente),
        }
        for m in matriculas
    ]
    return JsonResponse(data, safe=False)


def registrar_asistencia(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            asistencias = data.get("asistencias", [])

            for asistencia in asistencias:
                alumno = Alumno.objects.filter(id=asistencia["alumno_id"]).first()
                curso = Curso.objects.filter(id=asistencia["curso_id"]).first()
                if not alumno or not curso:
                    return JsonResponse({"success": False, "error": "Alumno o curso no encontrado"})

                matricula = Matricula.objects.filter(alumno=alumno, curso=curso).first()
                if not matricula:
                    return JsonResponse({"success": False, "error": "Matricula no encontrado"})

                Asistencia.objects.create(
                    fecha=asistencia["fecha"],
                    alumno=alumno,
                    curso=curso,
                    presente=asistencia["presente"]
                )

            return JsonResponse({"success": True})

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"success": False, "error": str(e)})

    # Manejo de solicitudes GET
    fecha_str = request.GET.get("fecha")
    fecha = date.fromisoformat(fecha_str) if fecha_str else date.today()

    print(f"\nFecha seleccionada: {fecha}")

    total_matriculas = Matricula.objects.count()
    print(f"Total de matriculas en la BD: {total_matriculas}")

    matriculas = Matricula.objects.filter(
        Q(modalidad="extendida", fecha_inicio__lte=fecha, fecha_inicio__gte=fecha - timedelta(weeks=6)) |
        Q(modalidad="full_day", fecha_inicio__lte=fecha, fecha_inicio__gte=fecha - timedelta(weeks=3))
    )

    print(f"Matrículas activas encontradas: {matriculas.count()}")

    for m in matriculas:
        print(f"Alumno: {m.alumno.nombre}, Curso: {m.curso.nombre}, Modalidad: ({m.modalidad}) - Fecha Inicio: {m.fecha_inicio}")

    # Obtener los alumnos que deben estar en esa fecha
    cursos_matriculados = matriculas.values_list("curso", flat=True)
    alumnos = Alumno.objects.filter(id__in=matriculas.values_list("alumno", flat=True))

    print(f"Alumnos encontrados: {alumnos.count()}")

    return render(request, "cursos/registrar_asistencia.html", {"alumnos": alumnos, "fecha": fecha})

def lista_asistencia(request):
    asistencias = Asistencia.objects.all().order_by('-fecha')
    return render(request, 'cursos/lista_asistencia.html', {'asistencias': asistencias})

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

            # Crear clases en la BD
            for fecha_clase in fechas_clases:
                Clase.objects.create(
                    curso=matricula.curso,
                    fecha=fecha_clase
                )
                print(f"Clase creada para {fecha_clase}")

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

    total_asistencias = Asistencia.objects.count()
    asistencias_presentes = Asistencia.objects.filter(presente=True).count()
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

def eliminar_matricula(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    matricula.delete()
    return redirect('lista_matriculas.html')  # Reemplaza con la URL correcta

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

def lista_matriculas(request):
    matriculas = Matricula.objects.all()

    import ast
    for m in matriculas:
        try:
            dias_lista = ast.literal_eval(m.dias_estudio)
            m.dias_estudio = ", ".join(dias_lista)
        except:
            pass

    return render(request, 'cursos/lista_matriculas.html', {'matriculas': matriculas})
