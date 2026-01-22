from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from django.http import HttpResponse
from django.contrib.auth.models import User

from .views import (
    # Administración
    menu_admin, dashboard, obtener_datos_dashboard, export_dashboard_excel,

    # Cursos
    crear_curso, lista_cursos,

    # Alumnos
    registrar_alumnos, lista_alumnos,

    # Matrículas
    calendario_matriculas, lista_matriculas, registrar_matricula,
    detalle_matricula,

    # Asistencia y notas
    ver_asistencia_unidad, lista_asistencia, registrar_nota, lista_notas,

    # Calendario
    vista_calendario,

    eliminar_matricula, editar_alumno, eliminar_alumno, editar_matricula,

    kanban, crear_tarea, actualizar_estado_tarea, mi_login_view, actualizar_fecha_clase,

    eventos_json, actualizar_tareas_vencidas, tareas_vencidas, registrar_asistencia_unidad,

    tareas_completadas, reprogramar_tarea, exportar_tareas_completadas, pagina_pagos, pagar_cuota, egresados, generar_certificado
)

def crear_usuario_admin(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser('admin', 'admin@weein.com', 'admin')
        return HttpResponse("✅ Superusuario creado.")
    return HttpResponse("⚠️ Ya existe un superusuario.")

urlpatterns = [
    path('crear-admin/', crear_usuario_admin),
    path('accounts/login/', mi_login_view, name='login'),  # ← REGISTRA TU LOGIN AQUÍ
    # Administración
    path('menu-admin/', menu_admin, name='menu_admin'),
    path('dashboard/', dashboard, name='dashboard'),

    path('export-dashboard-excel/', export_dashboard_excel, name='export_dashboard_excel'),

    # Cursos
    path('crear_curso/', crear_curso, name='crear_curso'),
    path('lista_cursos/', lista_cursos, name='lista_cursos'),

    # Alumnos
    path('registrar_alumnos/', registrar_alumnos, name='registrar_alumnos'),
    path('lista_alumnos/', lista_alumnos, name='lista_alumnos'),

    # Matrículas
    path('calendario_matriculas/', calendario_matriculas, name='calendario_matriculas'),
    path('lista_matriculas/', lista_matriculas, name='lista_matriculas'),
    path('registrar_matricula/', registrar_matricula, name='registrar_matricula'),
    path('detalle_matricula/<int:matricula_id>/<str:fecha>/', detalle_matricula, name='detalle_matricula'),
    
    # Asistencia y Notas
    path('registrar_asistencia_unidad/', registrar_asistencia_unidad, name='registrar_asistencia_unidad'),
    path('ver_asistencia_unidad/', ver_asistencia_unidad, name='ver_asistencia_unidad'),
    path('lista_asistencia/', lista_asistencia, name='lista_asistencia'),
    path('registrar_nota/', registrar_nota, name='registrar_nota'),
    path('lista_notas/', lista_notas, name='lista_notas'),

    # Calendario
    path('ver_calendario/', vista_calendario, name='vista_calendario'),
    path('api/calendario/', calendario_matriculas, name='calendario'),
    path('lista-matriculas/', lista_matriculas, name='lista_matriculas'),

    path('kanban/', kanban, name='kanban'),
    path('crear_tarea/', crear_tarea, name='crear_tarea'),
    path('tareas/completadas/exportar/', exportar_tareas_completadas, name='exportar_tareas_completadas'),

    path('tarea/<int:tarea_id>/reprogramar/', reprogramar_tarea, name='reprogramar_tarea'),
    path('tareas_completadas/', tareas_completadas, name='tareas_completadas'),
    path('actualizar_estado_tarea/<int:tarea_id>/', actualizar_estado_tarea, name='actualizar_estado_tarea'),
    path('actualizar_fecha_clase/<int:clase_id>/', actualizar_fecha_clase, name='actualizar_fecha_clase'),
    path('eventos/json/', eventos_json, name='eventos_json'),
    path('editar_alumno/<int:alumno_id>/', editar_alumno, name='editar_alumno'),
    path('eliminar_alumno/<int:alumno_id>/', eliminar_alumno, name='eliminar_alumno'),
    path('editar_matricula/<int:matricula_id>/', editar_matricula, name='editar_matricula'),
    path('eliminar_matricula/<int:matricula_id>/', eliminar_matricula, name='eliminar_matricula'),
    path('tareas_vencidas/', tareas_vencidas, name='tareas_vencidas'),
    path('actualizar_vencidas/', actualizar_tareas_vencidas, name='actualizar_tareas_vencidas'),

    path('pagos/', pagina_pagos, name='pagina_pagos'),
    path('pagar-cuota/<int:cuota_id>/', pagar_cuota, name='pagar_cuota'),

    path('egresados/', egresados, name='egresados'),
    path(
    "generar-certificado/<int:matricula_id>/",
    generar_certificado,
    name="generar_certificado"
),
]
