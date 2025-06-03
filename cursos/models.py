from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from cursos.utils import generar_fechas
from datetime import datetime

CURSO_CHOICES = (
    ('PLC NIVEL 1', 'PLC NIVEL 1'),
    ('PLC NIVEL 2', 'PLC NIVEL 2'),
    ('INSTRUMENTACION INDUSTRIAL', 'INSTRUMENTACION INDUSTRIAL'),
    ('VARIADORES DE FRECUENCIA', 'VARIADORES DE FRECUENCIA'),
    ('PLC LOGO! V8', 'PLC LOGO! V8'),
    ('REDES INDUSTRIALES', 'REDES INDUSTRIALES'),
)

DAY_CHOICES = (
    ('lunes', 'Lunes'),
    ('martes', 'Martes'),
    ('miercoles', 'Miércoles'),
    ('jueves', 'Jueves'),
    ('viernes', 'Viernes'),
    ('sabado', 'Sábado'),
    ('domingo', 'Domingo'),
)

MODALIDAD_CHOICES = (
    ('extendida', 'Extendida'),
    ('full_day', 'Full Day'),
)

TURNO_CHOICES = (
    ('mañana', 'Mañana'),
    ('tarde', 'Tarde'),
)

ESTADO_MATRICULA_CHOICES = (
    ('activa', 'Activa'),
    ('finalizada', 'Finalizada'),
    ('cancelada', 'Cancelada'),
)

class Curso(models.Model):
    nombre = models.CharField(max_length=255, choices=CURSO_CHOICES)
    fecha = models.DateField()
    fecha_inicio = models.DateField(default=timezone.now)
    horario = models.TimeField()
    duracion = models.IntegerField(help_text="Duración en horas")
    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return dict(CURSO_CHOICES).get(self.nombre, self.nombre)

class Alumno(models.Model):
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=25)
    correo = models.EmailField(unique=True)

    def __str__(self):
        return self.nombre

class DiaEstudio(models.Model):
    dia = models.CharField(max_length=20, choices=DAY_CHOICES)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return f"{self.get_dia_display()} - {self.curso.nombre}"

class Matricula(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_CHOICES)
    dias_estudio = models.CharField(max_length=100, blank=True)
    dias = models.JSONField(default=list)  # Para almacenar una lista de días
    saldo_pendiente = models.DecimalField(max_digits=8, decimal_places=2)
    fecha_inscripcion = models.DateField(auto_now_add=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    numero_semanas = models.IntegerField()
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_MATRICULA_CHOICES, default='activa')
    fechas = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        if isinstance(self.fecha_inicio, str):
            self.fecha_inicio = datetime.strptime(self.fecha_inicio, "%Y-%m-%d").date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alumno.nombre} - {self.curso.nombre} ({self.modalidad})"

    def clean(self):
        if not self.dias and not self.dias_estudio:
            raise ValidationError("Debes ingresar al menos un día de estudio.")

class Clase(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    fecha = models.DateField(default=now)
    horario = models.TimeField(default="08:00:00")
    matriculas = models.ManyToManyField(Matricula, blank=True)

    def __str__(self):
        return f"Clase de {self.curso.nombre} - {self.fecha} {self.horario}"

class Nota(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE)
    nota = models.FloatField(default=0)
    comentarios = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.matricula.alumno.nombre} - {self.matricula.curso.nombre}: {self.nota}"

class Evento(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    fecha = models.DateField()

    def __str__(self):
        return f"{self.curso.nombre} - {self.alumno.nombre} ({self.fecha})"


class Area(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Tarea(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
    ]
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]

    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='baja')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    tiempo_estimado = models.PositiveIntegerField(help_text="Tiempo en minutos para completar la tarea")
    area_asignada = models.ForeignKey(Area, related_name='tareas', on_delete=models.CASCADE)
    tarea_compartida = models.ManyToManyField(Area, related_name='tareas_compartidas', blank=True)
    tarea_delegada = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    vencida = models.BooleanField(default=False)
    completado = models.BooleanField(default=False)

    def __str__(self):
        return self.titulo

class UnidadCurso(models.Model):
    curso = models.ForeignKey('Curso', on_delete=models.CASCADE, related_name='unidades')
    numero = models.PositiveIntegerField()
    nombre_tema = models.CharField(max_length=255)

    class Meta:
        unique_together = ('curso', 'numero')
        ordering = ['numero']

    def __str__(self):
        return f"{self.curso.nombre} - Unidad {self.numero}"

class AsistenciaUnidad(models.Model):
    matricula = models.ForeignKey('Matricula', on_delete=models.CASCADE, related_name='asistencias')
    unidad = models.ForeignKey('UnidadCurso', on_delete=models.CASCADE)
    completado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('matricula', 'unidad')
