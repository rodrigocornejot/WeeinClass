from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
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
    registrar_asistencia, lista_asistencia, registrar_nota, lista_notas,

    # Calendario
    vista_calendario,

    eliminar_matricula,

    kanban, crear_tarea, actualizar_estado_tarea, mi_login_view, actualizar_fecha_evento,

    eventos_json
)

urlpatterns = [
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
    path('registrar_asistencia/', registrar_asistencia, name='registrar_asistencia'),
    path('lista_asistencia/', lista_asistencia, name='lista_asistencia'),
    path('registrar_nota/', registrar_nota, name='registrar_nota'),
    path('lista_notas/', lista_notas, name='lista_notas'),

    # Calendario
    path('ver_calendario/', vista_calendario, name='vista_calendario'),
    path('api/calendario/', calendario_matriculas, name='calendario'),
    path('lista-matriculas/', lista_matriculas, name='lista_matriculas'),

    path('kanban/', kanban, name='kanban'),
    path('crear_tarea/', crear_tarea, name='crear_tarea'),
    path('actualizar_estado_tarea/<int:tarea_id>/', actualizar_estado_tarea, name='actualizar_estado_tarea'),
    path('actualizar_fecha_evento/<int:matricula_id>/', actualizar_fecha_evento, name='actualizar_fecha_evento'),
    path('eventos/json/', eventos_json, name='eventos_json'),
]
