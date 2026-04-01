import os 
import django

# Inicializar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WeeinClass.settings")
django.setup()

from cursos.models import Matricula, Clase, AsistenciaUnidad

for matricula in Matricula.objects.all():

    clases = Clase.objects.filter(
        matriculas=matricula
    ).order_by("fecha")

    asistencias = AsistenciaUnidad.objects.filter(
        matricula=matricula
    ).order_by("unidad__numero")

    for clase, asistencia in zip(clases, asistencias):
        asistencia.clase = clase
        asistencia.save()

print("SESIONES CONECTADAS")