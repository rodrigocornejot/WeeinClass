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
from .models import Alumno, Curso, Nota, Matricula, Clase, Tarea, Area, Evento, UnidadCurso, AsistenciaUnidad, Pago, Cuota, Egresado
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from .forms import CursoForm, MatriculaAdminForm, MatriculaForm, NotaForm, Pago
from django.db.models import Count, Avg, Q, Sum
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
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.db import transaction
from cursos.models import Certificado
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.timezone import now
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from cursos.utils import emitir_certificado_si_corresponde, verificar_y_generar_certificado, puede_generar_certificado
from django.template.loader import render_to_string
import os

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
    clases = (
        Clase.objects
        .select_related('curso')
        .prefetch_related('matriculas__alumno')
        .order_by('fecha')
    )

    eventos = []

    for clase in clases:
        color = CURSO_COLORES.get(clase.curso.nombre, '#0d6efd')

        if clase.matriculas.exists():
            for matricula in clase.matriculas.all():
                eventos.append({
                    "id": clase.id,
                    "title": f"{matricula.alumno.nombre} - {clase.curso.nombre}",
                    "start": clase.fecha.strftime('%Y-%m-%d'),
                    "color": color,
                    "textColor": "black",

                    # 🔥 AQUÍ VA EL EXTENDED PROPS
                    "extendedProps": {
                        "matricula_id": matricula.id,
                        "curso": clase.curso.nombre,
                        "alumno": matricula.alumno.nombre,
                        "tipo_horario": matricula.get_tipo_horario_display(),
                        "clase_id": clase.id,
                    }
                })
        else:
            eventos.append({
                "id": clase.id,
                "title": clase.curso.nombre,
                "start": clase.fecha.strftime('%Y-%m-%d'),
                "color": color,
                "textColor": "black",
                "extendedProps": {
                    "clase_id": clase.id
                }
            })

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

def es_profesor_o_recepcion(user):
    # Ajusta los nombres de grupos si los tuyos son distintos
    return (
        user.is_superuser or 
        user.groups.filter(name__in=['Profesores', 'Recepcion']).exists()
    )

def lista_alumnos(request):
    alumnos = Alumno.objects.all()
    return render(request, 'cursos/lista_alumnos.html', {
        'alumnos': alumnos    
    })

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

@user_passes_test(es_profesor_o_recepcion)
@login_required
def registrar_asistencia_unidad(request):
    cursos = Curso.objects.all().order_by("nombre")

    curso_id = request.GET.get("curso") or request.POST.get("curso")
    fecha_str = request.GET.get("fecha") or request.POST.get("fecha")

    curso_seleccionado = None
    fecha_seleccionada = None
    clase = None

    alumnos_unidades = []
    unidades = []

    # ---- Parse fecha ----
    if fecha_str:
        try:
            fecha_seleccionada = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                fecha_seleccionada = datetime.strptime(fecha_str, "%d/%m/%Y").date()
            except ValueError:
                fecha_seleccionada = None

    if curso_id:
        curso_seleccionado = Curso.objects.filter(id=curso_id).first()

    if curso_seleccionado and fecha_seleccionada:
        # ✅ obligar a que exista clase ese día
        clase = Clase.objects.filter(
            curso=curso_seleccionado,
            fecha=fecha_seleccionada
        ).first()

        if clase:
            matriculas = clase.matriculas.select_related("alumno", "curso").distinct()

            # ✅ unidades reales (5 o 6) + nombre_tema correcto
            unidades = asegurar_unidades_curso(curso_seleccionado)

            # Si no hay unidades configuradas, avisamos
            if not unidades:
                messages.warning(
                    request,
                    f"⚠ El curso '{curso_seleccionado.nombre}' no tiene módulos configurados."
                )

            # ---- POST: guardar ----
            if request.method == "POST" and request.POST.get("guardar_asistencias"):
                with transaction.atomic():
                    for matricula in matriculas:
                        for unidad in unidades:
                            campo = f"asistencia_{matricula.id}_{unidad.id}"
                            presente = request.POST.get(campo) == "on"

                            asistencia = AsistenciaUnidad.objects.filter(
                                matricula=matricula,
                                unidad=unidad
                            ).order_by("fecha").first()

                            if presente:
                                if not asistencia:
                                    AsistenciaUnidad.objects.create(
                                        matricula=matricula,
                                        unidad=unidad,
                                        fecha=fecha_seleccionada,
                                        completado=True
                                    )
                                else:
                                    # ya está completado antes → NO crear duplicado
                                    if not asistencia.completado:
                                        asistencia.completado = True
                                        if not asistencia.fecha:
                                            asistencia.fecha = fecha_seleccionada
                                        asistencia.save(update_fields=["completado", "fecha"])
                            else:
                                # ✅ Opcional recomendado: NO borrar módulos ya completados en días anteriores
                                # Solo borrar si fue marcado hoy (para correcciones del mismo día)
                                if asistencia and asistencia.fecha == fecha_seleccionada:
                                    asistencia.delete()

                messages.success(request, "✅ Asistencias guardadas correctamente.")

                for matricula in matriculas:
                    verificar_y_generar_certificado(matricula)

                return redirect(
                    f"/cursos/registrar_asistencia_unidad/?curso={curso_seleccionado.id}&fecha={fecha_seleccionada}"
                )

            # ---- GET: construir tabla ----
            for matricula in matriculas:
                unidades_info = []
                for unidad in unidades:
                    asistencia_global = AsistenciaUnidad.objects.filter(
                        matricula=matricula,
                        unidad=unidad,
                        completado=True
                    ).order_by("fecha").first()

                    marcado_global = asistencia_global is not None
                    marcado_hoy = marcado_global and asistencia_global.fecha == fecha_seleccionada

                    unidades_info.append({
                        "unidad_id": unidad.id,
                        "numero": unidad.numero,
                        "nombre_tema": unidad.nombre_tema,  # ✅ SIEMPRE nombre_tema
                        "completado": marcado_global,     # ✅ ya está completado (cualquier fecha)
                        "marcado_hoy": marcado_hoy,       # ✅ se completó justo hoy
                        "fecha_completado": asistencia_global.fecha if asistencia_global else None,
                    })

                alumnos_unidades.append({
                    "matricula": matricula,
                    "unidades": unidades_info
                })

    context = {
        "cursos": cursos,
        "curso_seleccionado": curso_seleccionado,
        "fecha_seleccionada": fecha_seleccionada,
        "clase": clase,
        "alumnos_unidades": alumnos_unidades,
        "unidades": unidades,
    }
    return render(request, "cursos/registrar_asistencia_unidad.html", context)

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
        matricula = Matricula.objects.select_related(
            'alumno', 'curso'
        ).get(id=matricula_id)

        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()

        return JsonResponse({
            "nombre": matricula.alumno.nombre,
            "curso": matricula.curso.nombre,
            "turno": matricula.get_tipo_horario_display(),
            "saldo": float(matricula.saldo_pendiente),
            "fecha": fecha_dt.strftime("%d/%m/%Y"),
        })

    except Matricula.DoesNotExist:
        return JsonResponse({"error": "Matrícula no encontrada"}, status=404)

    except Exception as e:
        print("❌ Error:", e)
        return JsonResponse({"error": "Error interno"}, status=500)

def asegurar_unidades_curso(curso: Curso):
    """ 
    Crea/asegura las unidades reales del curso (5 o 6) con su nombre_tema correcto.
    Si ya existen, solo las retorna ordenadas.
    """
    existentes = list(UnidadCurso.objects.filter(curso=curso).order_by("numero"))
    if existentes:
        return existentes

    # ✅ CONFIG REAL (según lo que me mandaste)
    # OJO: las llaves deben coincidir con Curso.nombre EXACTO en tu BD.
    MAPA_MODULOS = {
        "INSTRUMENTACION INDUSTRIAL": [
            "INTRODUCCION", "TEMPERATURA", "PRESION", "NIVEL", "CAUDAL", "VALVULAS"
        ],
        "PLC NIVEL 1": [
            "SESION 1", "SESION 2", "SESION 3", "SESION 4", "SESION 5", "SESION 6"
        ],
        "PLC NIVEL 2": [
            "SESION 1", "SESION 2", "SESION 3", "SESION 4", "SESION 5", "SESION 6"
        ],
        "REDES INDUSTRIALES": [
            "DP", "RTU", "TCP", "PN", "ETH/IP"
        ],
        "VARIADORES DE FRECUENCIA": [
            "SINAMICS", "DELTA", "SCHNEIDER", "ABB", "DANFOSS", "POWERFLEX"
        ],
        "AUTOMATIZACION PARA EL ARRANQUE DE MOTORES ELECTRICOS CON PLC LOGO V8!": [
            "SESION 1", "SESION 2", "SESION 3", "SESION 4", "SESION 5"
        ],
        "PLC LOGO! V8": [
            "SESION 1", "SESION 2", "SESION 3", "SESION 4", "SESION 5"
        ],
    }
    
    nombre_normalizado = (curso.nombre or "").strip()

    temas = MAPA_MODULOS.get(nombre_normalizado, [])

    # Si por algún motivo el curso no está en el mapa, NO forzamos 6.
    # Creamos 0 y te obligará a registrar módulos en BD primero (mejor que inventar).
    if not temas:
        return []

    unidades = []
    for i, tema in enumerate(temas, start=1):
        unidad = UnidadCurso.objects.create(
            curso=curso,
            numero=i,
            nombre_tema=tema
        )
        unidades.append(unidad)

    return unidades

@login_required
def registrar_matricula(request):
    alumno = None
    dni = request.GET.get('dni') or request.POST.get('dni', '')

    if dni:
        alumno = Alumno.objects.filter(dni=dni).first()

    if request.method == 'POST':
        form = MatriculaForm(request.POST)

        if not alumno:
            form.add_error(None, 'No existe un alumno con ese DNI')

        if form.is_valid() and alumno:
            matricula = form.save(commit=False)
            matricula.alumno = alumno

            # ==============================
            # 🔵 CÁLCULOS FINANCIEROS
            # ==============================
            precio_base = Decimal(matricula.costo_curso or 0)
            descuento_pct = Decimal(matricula.porcentaje or 0)
            anticipo = Decimal(matricula.primer_pago or 0)

            descuento_monto = (precio_base * descuento_pct / Decimal('100')).quantize(Decimal('0.01'))
            precio_final = (precio_base - descuento_monto).quantize(Decimal('0.01'))

            matricula.precio_final = precio_final
            matricula.saldo_pendiente = (precio_final - anticipo).quantize(Decimal('0.01'))

            matricula.save()
            form.save_m2m()

            # ==============================
            # 🟣 CREAR CUOTAS (2) SI NO EXISTEN
            # ==============================
            saldo = matricula.saldo_pendiente

            if saldo > 0 and not Cuota.objects.filter(matricula=matricula).exists():
                monto_cuota = (saldo / Decimal('2')).quantize(Decimal('0.01'))
                fecha_base = matricula.fecha_inicio or datetime.today().date()

                Cuota.objects.create(
                    matricula=matricula,
                    numero=1,
                    monto=monto_cuota,
                    monto_pagado=Decimal('0.00'),
                    fecha_vencimiento=fecha_base + timedelta(days=15),
                    pagado=False,
                )

                Cuota.objects.create(
                    matricula=matricula,
                    numero=2,
                    monto=monto_cuota,
                    monto_pagado=Decimal('0.00'),
                    fecha_vencimiento=fecha_base + timedelta(days=30),
                    pagado=False,
                )

            # ==============================
            # 🟢 GENERAR FECHAS DE CLASES SEGÚN MÓDULOS (5 o 6)
            # ==============================
            fecha_inicio = matricula.fecha_inicio
            dias = form.cleaned_data.get('dias')  # lista de strings: ['lunes', 'miercoles', ...]
            fechas_personalizadas = form.cleaned_data.get('fechas_personalizadas')

            # ✅ Traer módulos reales del curso (5 o 6)
            unidades = asegurar_unidades_curso(matricula.curso)  # debe devolver lista ordenada
            total_unidades = len(unidades)

            if total_unidades == 0:
                # fallback por si no tienes unidades cargadas
                total_unidades = 6

            fechas = []

            # ==============================
            # 🟢 HORARIO PERSONALIZADO
            # ==============================
            if fechas_personalizadas:
                try:
                    # ejemplo: "2026-01-15, 2026-01-20, 2026-02-10"
                    for f in fechas_personalizadas.split(','):
                        fechas.append(datetime.strptime(f.strip(), '%Y-%m-%d').date())
                except ValueError:
                    form.add_error(
                        'fechas_personalizadas',
                        'Formato incorrecto. Usa YYYY-MM-DD separados por coma.'
                    )
                    return render(request, 'cursos/registrar_matricula.html', {
                        'form': form,
                        'alumno': alumno,
                        'dni': dni
                    })

                # ✅ quitar duplicados y ordenar
                fechas = sorted(set(fechas))

                # ✅ si mandan más fechas que módulos, solo toma las primeras N
                fechas = fechas[:total_unidades]

            # ==============================
            # 🔵 HORARIO NORMAL (FULL / EXTENDIDA)
            # ==============================
            else:
                if not dias:
                    form.add_error('dias', 'Debe seleccionar al menos un día')
                    return render(request, 'cursos/registrar_matricula.html', {
                        'form': form,
                        'alumno': alumno,
                        'dni': dni
                    })

                if not fecha_inicio:
                    form.add_error('fecha_inicio', 'Debe ingresar una fecha de inicio.')
                    return render(request, 'cursos/registrar_matricula.html', {
                        'form': form,
                        'alumno': alumno,
                        'dni': dni
                    })

                dias_map = {
                    'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
                    'viernes': 4, 'sabado': 5, 'domingo': 6
                }

                # Ordenar días por weekday para construir fechas en orden real
                dias_ordenados = sorted(dias, key=lambda d: dias_map[d])

                # ✅ Crear EXACTAMENTE N fechas (N = módulos del curso)
                fecha_cursor = fecha_inicio
                while len(fechas) < total_unidades:
                    for dia in dias_ordenados:
                        if len(fechas) >= total_unidades:
                            break

                        dia_num = dias_map[dia]
                        offset = (dia_num - fecha_cursor.weekday()) % 7
                        fecha_clase = fecha_cursor + timedelta(days=offset)

                        if fecha_clase not in fechas:
                            fechas.append(fecha_clase)

                    # avanzar una semana
                    fecha_cursor = fecha_cursor + timedelta(days=7)

                fechas = sorted(fechas)

            # ==============================
            # 🟠 CREAR CLASES + ASISTENCIAS POR MÓDULO
            # ==============================
            # ✅ seguridad: si por alguna razón unidades está vacío, no romper
            if not unidades:
                unidades = list(UnidadCurso.objects.filter(curso=matricula.curso).order_by('numero'))
            # Recalcular total_unidades real
            total_unidades = min(len(unidades), len(fechas))

            for idx in range(total_unidades):
                fecha = fechas[idx]
                unidad = unidades[idx]  # módulo correspondiente (1 con 1ra fecha, etc.)

                # ✅ No duplicar clases por fecha/curso
                clase, _ = Clase.objects.get_or_create(
                    curso=matricula.curso,
                    fecha=fecha
                )
                clase.matriculas.add(matricula)

                # ✅ Crear asistencia ligada a esa clase y a ese módulo
                AsistenciaUnidad.objects.get_or_create(
                    matricula=matricula,
                    unidad=unidad,
                    clase=clase,
                    defaults={"completado": False}
                )

            messages.success(request, "✅ Matrícula registrada, clases y asistencias creadas correctamente.")
            return redirect('vista_calendario')

        else:
            print("❌ FORM INVALIDO")
            print(form.errors)

    else:
        form = MatriculaForm(initial={
            'dni': dni,
            'alumno_nombre': alumno.nombre if alumno else ''
        })

    return render(request, 'cursos/registrar_matricula.html', {
        'form': form,
        'alumno': alumno,
        'dni': dni
    })

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
        nombre=request.POST.get('nombre')
        dni=request.POST.get('dni')
        telefono=request.POST.get('telefono')
        correo=request.POST.get('correo')

        grado_academico=request.POST.get('grado_academico')
        carrera=request.POST.get('carrera')
        trabajo=request.POST.get('trabajo')
        referencia=request.POST.get('referencia')

        edad_raw = request.POST.get('edad')
        edad = int(edad_raw) if edad_raw else None

        sexo=request.POST.get('sexo')

        distrito=request.POST.get('distrito')
        departamento=request.POST.get('departamento')
        pais=request.POST.get('pais')

        uso_imagen=request.POST.get('uso_imagen') == 'on'
        
        # VALIDACIÓN DE CORREO ÚNICO
        if correo and Alumno.objects.filter(correo=correo).exists():
            return render(request, 'cursos/registrar_alumnos.html', {
                'error': 'El correo ya está registrado'
            })

        if dni and Alumno.objects.filter(dni=dni).exists():
            return render(request, 'cursos/registrar_alumnos.html', {
                'error': 'El DNI ya está registrado'
            })
        
        Alumno.objects.create(
            nombre=nombre,
            dni=dni,
            correo=correo,
            telefono=telefono,
            edad=edad,
            sexo=sexo,
            grado_academico=grado_academico,
            carrera=carrera,
            trabajo=trabajo,
            referencia=referencia,
            pais=pais,
            departamento=departamento,
            distrito=distrito,
            uso_imagen=uso_imagen
        )

        messages.success(request, '✅ Alumno registrado correctamente')
        return redirect('lista_alumnos')

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
def actualizar_fecha_clase(request, clase_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        nueva_fecha = datetime.strptime(
            data['nueva_fecha'],
            '%Y-%m-%d'
        ).date()

        clase = Clase.objects.get(id=clase_id)
        clase.fecha = nueva_fecha
        clase.save()

        return JsonResponse({'status': 'success'})
    
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

@login_required
def pagina_pagos(request):
    dni = (request.GET.get("dni") or "").strip()
    matricula_id = (request.GET.get("matricula_id") or "").strip()

    alumno = None
    matriculas = []
    matricula = None
    cuotas = []
    total_pagado_cuotas = Decimal("0.00")

    if dni:
        alumno = Alumno.objects.filter(dni=dni).first()

        if alumno:
            matriculas = Matricula.objects.filter(alumno=alumno).order_by("-fecha_inscripcion", "-id")

            if matriculas.exists():
                # 1) usar la seleccionada
                if matricula_id:
                    matricula = matriculas.filter(id=matricula_id).first()

                # 2) si no hay seleccionada, tomar la primera
                if not matricula:
                    matricula = matriculas.first()

                # ✅ asegurar cuotas para la matrícula seleccionada
                asegurar_cuotas(matricula)

                # cuotas reales
                cuotas = Cuota.objects.filter(matricula=matricula).order_by("numero", "id")

                # total pagado en cuotas
                total_pagado_cuotas = cuotas.aggregate(total=Sum("monto_pagado"))["total"] or Decimal("0.00")

                # recalcular saldo pendiente coherente
                precio_final = getattr(matricula, "precio_final", None)
                if precio_final is None:
                    precio_final = matricula.costo_curso

                anticipo = matricula.primer_pago or Decimal("0.00")
                nuevo_saldo = precio_final - anticipo - total_pagado_cuotas
                if nuevo_saldo < 0:
                    nuevo_saldo = Decimal("0.00")

                if matricula.saldo_pendiente != nuevo_saldo:
                    matricula.saldo_pendiente = nuevo_saldo
                    matricula.save(update_fields=["saldo_pendiente"])

    return render(request, "cursos/pagos.html", {
        "dni": dni,
        "alumno": alumno,
        "matriculas": matriculas,
        "matricula": matricula,
        "matricula_id": str(matricula.id) if matricula else "",
        "cuotas": cuotas,
        "total_pagado_cuotas": total_pagado_cuotas,
    })

def crear_cuotas(matricula):
    saldo = matricula.precio_final - matricula.primer_pago

    if saldo <= 0:
        return

    monto_cuota = saldo / Decimal('2')

    # Cuota 1 (15 días después)
    Cuota.objects.create(
        matricula=matricula,
        numero=1,
        monto=monto_cuota,
        fecha_vencimiento=matricula.fecha_inicio + timedelta(days=15),
        pagado=False
    )

    # Cuota 2 (30 días después)
    Cuota.objects.create(
        matricula=matricula,
        numero=2,
        monto=monto_cuota,
        fecha_vencimiento=matricula.fecha_inicio + timedelta(days=30),
        pagado=False
    )

@login_required
def pagar_cuota(request, cuota_id):
    if request.method != "POST":
        return redirect("pagina_pagos")

    cuota = get_object_or_404(Cuota, id=cuota_id)

    dni = (request.POST.get("dni") or "").strip()
    matricula_id = (request.POST.get("matricula_id") or "").strip()

    monto_str = (request.POST.get("monto") or "").strip()
    if not monto_str:
        messages.error(request, "Ingresa un monto.")
        return redirect(f"/cursos/pagos/?dni={dni}&matricula_id={matricula_id}")

    try:
        monto = Decimal(monto_str)
    except:
        messages.error(request, "Monto inválido.")
        return redirect(f"/cursos/pagos/?dni={dni}&matricula_id={matricula_id}")

    if monto <= 0:
        messages.error(request, "El monto debe ser mayor a 0.")
        return redirect(f"/cursos/pagos/?dni={dni}&matricula_id={matricula_id}")

    saldo_cuota = (cuota.monto - (cuota.monto_pagado or Decimal("0.00")))
    if monto > saldo_cuota:
        monto = saldo_cuota  # no permitir pagar más de lo que falta

    # ✅ registra el pago (ajusta campos según tu modelo Pago real)
    Pago.objects.create(
        matricula=cuota.matricula,
        monto=monto,
        concepto=f"cuota_{cuota.numero}",
    )

    # ✅ actualizar cuota
    cuota.monto_pagado = (cuota.monto_pagado or Decimal("0.00")) + monto
    if cuota.monto_pagado >= cuota.monto:
        cuota.pagado = True
    cuota.save()

    # ✅ RECALCULAR saldo pendiente de la matrícula
    from django.db.models import Sum

    matricula = cuota.matricula
    total_pagado = (
        Pago.objects
        .filter(matricula=matricula)
        .aggregate(s=Sum("monto"))["s"]
        or Decimal("0.00")
    )

    matricula.saldo_pendiente = matricula.costo_curso - total_pagado
    matricula.save(update_fields=["saldo_pendiente"])


    ruta_cert = verificar_y_generar_certificado(matricula)

    if ruta_cert:
        # Si tienes un campo para guardar el certificado en Matricula, guarda aquí:
        # cuota.matricula.certificado_pdf = ruta_cert
        # cuota.matricula.save(update_fields=["certificado_pdf"])
        messages.success(request, "✅ Pago completo y asistencias completas: Certificado generado.")
        # ✅ redirigir manteniendo matrícula seleccionada
    return redirect(f"/cursos/pagos/?dni={dni}&matricula_id={cuota.matricula.id}")

def egresados(request):
    todas = Matricula.objects.select_related("alumno", "curso")
    matriculas = [m for m in todas if puede_generar_certificado(m)]

    certificados = Certificado.objects.filter(matricula__in=matriculas)
    cert_map = {c.matricula_id: c for c in certificados}

    for m in matriculas:
        m.certificado = cert_map.get(m.id)

    return render(request, "cursos/egresados.html", {"matriculas": matriculas})

def asegurar_cuotas(matricula: Matricula):
    """
    Crea Cuota 1 y Cuota 2 si la matrícula no tiene cuotas.
    """
    existe = Cuota.objects.filter(matricula=matricula).exists()
    if existe:
        return

    # Precio final (si no existe, usa costo_curso)
    precio_final = getattr(matricula, "precio_final", None)
    if precio_final is None:
        precio_final = matricula.costo_curso

    anticipo = matricula.primer_pago or Decimal("0.00")
    saldo = precio_final - anticipo
    if saldo <= 0:
        return

    monto_cuota = (saldo / Decimal("2")).quantize(Decimal("0.01"))

    fecha_base = matricula.fecha_inicio or matricula.fecha_inscripcion
    Cuota.objects.create(
        matricula=matricula,
        numero=1,
        monto=monto_cuota,
        monto_pagado=Decimal("0.00"),
        pagado=False,
        fecha_vencimiento=fecha_base + timedelta(days=15),
    )
    Cuota.objects.create(
        matricula=matricula,
        numero=2,
        monto=monto_cuota,
        monto_pagado=Decimal("0.00"),
        pagado=False,
        fecha_vencimiento=fecha_base + timedelta(days=30),
    )
def wrap_center(text, font_name, font_size, max_width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def generar_certificado(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    cert, _ = Certificado.objects.get_or_create(matricula=matricula)

    regen = request.GET.get("regen") == "1"

    # ✅ 1) Si piden regen: borrar el PDF guardado (si existe)
    if regen and cert.archivo_pdf:
        cert.archivo_pdf.delete(save=False)
        cert.archivo_pdf = None
        cert.save()

    # ✅ 2) Si hay archivo en BD: verificar que exista físicamente
    if cert.archivo_pdf and cert.archivo_pdf.name:
        try:
            ruta = cert.archivo_pdf.path
        except Exception:
            ruta = None

        # Si no existe en disco, limpiar el campo para regenerar
        if (not ruta) or (not os.path.exists(ruta)):
            cert.archivo_pdf = None
            cert.save()
        else:
            # Existe y está OK
            return redirect(cert.archivo_pdf.url)

    # ✅ 3) Código (si no existe)
    if not cert.codigo:
        cert.codigo = f"CW-{now().strftime('%d%m%Y')}-{matricula.id:02d}"
        cert.save()

    # ✅ 4) rutas a imágenes
    fondo = os.path.join(settings.BASE_DIR, "static", "certificados", "fondo.png")
    logo  = os.path.join(settings.BASE_DIR, "static", "certificados", "logo.png")
    firma = os.path.join(settings.BASE_DIR, "static", "certificados", "firma.png")

    # ✅ 5) generar PDF
    buffer = BytesIO()
    w, h = landscape(A4)
    p = canvas.Canvas(buffer, pagesize=(w, h))

    M = 70
    CX = w / 2

    p.drawImage(ImageReader(fondo), 0, 0, width=w, height=h, mask="auto")

    logo_w, logo_h = 200, 60
    p.drawImage(ImageReader(logo), CX - (logo_w/2), h - 120, width=logo_w, height=logo_h, mask="auto")

    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(CX, h - 165, "CENTRO DE CAPACITACIONES WEEIN")

    p.setFont("Helvetica-Bold", 11)
    p.drawCentredString(CX, h - 205, "CERTIFICADO OTORGADO A:")

    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(CX, h - 255, matricula.alumno.nombre)

    p.setLineWidth(1)
    p.line(M + 120, h - 270, w - (M + 120), h - 270)

    # TEXTO centrado (usa tu wrap_center)
    max_text_width = w - 2*(M + 50)
    texto1 = "Por haber participado y aprobado satisfactoriamente el curso de"
    texto2 = f"{matricula.curso.nombre}."

    y = h - 330

    p.setFont("Helvetica", 12)
    for ln in wrap_center(texto1, "Helvetica", 12, max_text_width):
        p.drawCentredString(CX, y, ln)
        y -= 16

    p.setFont("Helvetica-Bold", 12)
    for ln in wrap_center(texto2, "Helvetica-Bold", 12, max_text_width):
        p.drawCentredString(CX, y, ln)
        y -= 16

    p.setFont("Helvetica", 12)
    p.drawString(M + 60, 150, f"Lima, {now().strftime('%d de %B del %Y')}")

    firma_w, firma_h = 190, 90
    firma_x = w - M - firma_w
    firma_y = 85
    p.drawImage(ImageReader(firma), firma_x, firma_y, width=firma_w, height=firma_h, mask="auto")

    tx = w - M
    p.setFont("Helvetica-Bold", 10)
    p.drawRightString(tx, firma_y - 5, "ING. YORDAN SMITH TORRES")
    p.drawRightString(tx, firma_y - 18, "TRUJILLO")
    p.setFont("Helvetica", 10)
    p.drawRightString(tx, firma_y - 32, "Gerente General")

    p.setFont("Helvetica", 10)
    p.drawString(M, 35, f"CERTIFICADO - {cert.codigo}")

    p.showPage()
    p.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    cert.archivo_pdf.save(f"cert_{cert.codigo}.pdf", ContentFile(pdf_bytes), save=True)

    return redirect(cert.archivo_pdf.url)