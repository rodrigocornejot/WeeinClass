from django.contrib import admin

# Register your models here.

from .models import Curso, Alumno, Area
from .models import Matricula
from .forms import MatriculaAdminForm

admin.site.register(Curso)
admin.site.register(Area)

@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('saldo_pendiente', 'alumno', 'curso', 'fecha_inscripcion', 'modalidad')
    search_fields = ('nombre_alumno', 'curso__alumno__nombre')
    form = MatriculaAdminForm

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni', 'telefono', 'correo', 'sexo', 'uso_imagen')
    search_fields = ('nombre', 'dni', 'correo')
