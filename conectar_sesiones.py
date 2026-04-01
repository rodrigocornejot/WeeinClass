import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WeeinClass.settings")
django.setup()

from cursos.models import Clase, AsistenciaUnidad

for clase in Clase.objects.all():

    for matricula in clase.matriculas.all():

        asistencias = AsistenciaUnidad.objects.filter(
            matricula=matricula,
            clase__isnull=True
        )

        for asistencia in asistencias:
            asistencia.clase = clase
            asistencia.save()

print("SESIONES CONECTADAS CORRECTAMENTE")