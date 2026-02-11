from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from cursos.utils import generar_fechas
from datetime import datetime
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal

CURSO_CHOICES = (
    ("VDF", "VARIADORES DE FRECUENCIA"),
    ("REDES", "REDES INDUSTRIALES"),
    ("PLC1", "PLC NIVEL 1"),
    ("PLC2", "PLC NIVEL 2"),
    ("INST", "INSTRUMENTACION INDUSTRIAL"),
    ("ELEC_LOGO", "AUTOMATIZACION PARA EL ARRANQUE DE MOTORES ELECTRICOS CON PLC LOGO V8!"),
    ("LOGO", "AUTOMATIZACION INDUSTRIAL CON PLC LOGO V8!"),
)

MOTIVO_TRUNCO_CHOICES = (
    ("horarios", "Horarios"),
    ("economico", "Económico"),
    ("salud", "Salud"),
    ("viaje", "Viaje / Mudanza"),
    ("insatisfaccion", "Insatisfacción"),
    ("otro", "Otro"),
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
    ('truncado', 'Truncado'),
)

SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
]

TIPO_HORARIO_CHOICES = (
    ('full', 'Full Day (3 semanas)'),
    ('extendida', 'Extendida (6 semanas)'),
    ('personalizado', 'Personalizado'),
)

class Curso(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
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
        return self.get_nombre_display()

class Alumno(models.Model):
    nombre = models.CharField(max_length=255)
    dni = models.CharField(
        max_length=8, 
        unique=True,
        null=True,
        blank=True
    )
    telefono = models.CharField(max_length=25)
    correo = models.EmailField(unique=True)

    grado_academico = models.CharField(max_length=100, blank=True, null=True)
    carrera = models.CharField(max_length=150, blank=True, null=True)
    trabajo = models.CharField(max_length=150, blank=True, null=True)
    referencia = models.CharField(max_length=150, blank=True, null=True)

    edad = models.PositiveIntegerField(blank=True, null=True)
    sexo = models.CharField(
        max_length=1, 
        choices=SEXO_CHOICES,
        blank=True,
        null=True
    )

    distrito = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)
    pais = models.CharField(max_length=100, default='Perú')

    uso_imagen = models.BooleanField(default=False)

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
    modalidad = models.CharField(
        max_length=20, 
        choices=(('presencial', 'Presencial'), ('virtual', 'Virtual'))
    )

    tipo_horario = models.CharField(
        max_length=20,
        choices=TIPO_HORARIO_CHOICES
    )

    dias = models.JSONField(default=list, blank=True)  # Para almacenar una lista de días
    
    costo_curso = models.DecimalField(max_digits=8, decimal_places=2)
    primer_pago = models.DecimalField(max_digits=8, decimal_places=2)
    precio_final = models.DecimalField(max_digits=8, decimal_places=2)  # Precio acordado
    porcentaje = models.PositiveIntegerField()

    saldo_pendiente = models.DecimalField(max_digits=8, decimal_places=2)

    fecha_inicio = models.DateField(blank=True, null=True)
    fechas_personalizadas = models.JSONField(default=list, blank=True)

    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_MATRICULA_CHOICES, 
        default='activa'
    )

    fecha_inscripcion = models.DateField(auto_now_add=True)
    certificado_pdf = models.FileField(upload_to="certificados/", null=True, blank=True)
    registrada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matriculas_registradas"
    )
    fecha_baja = models.DateField(null=True, blank=True)
    motivo_trunco = models.CharField(max_length=30, choices=MOTIVO_TRUNCO_CHOICES, null=True, blank=True)
    razon_trunco = models.TextField(null=True, blank=True) 

    def save(self, *args, **kwargs):
    # Convertir fecha si viene como string
        if isinstance(self.fecha_inicio, str):
            self.fecha_inicio = datetime.strptime(self.fecha_inicio, "%Y-%m-%d").date()

        # 🔹 Calcular precio final SOLO si no existe
        if not self.precio_final:
            self.precio_final = self.costo_curso

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.alumno.nombre} - {self.curso.nombre} ({self.modalidad})"

    def clean(self):
        modalidad = (self.modalidad or "").lower()
        dias = self.dias or []
        personaliza = bool(self.fechas_personalizadas)

        # Solo exigir días si es extendida y NO personaliza
        if modalidad == "extendida" and not personaliza and not dias:
            raise ValidationError("Debes ingresar al menos un día de estudio.")

        
    def pagos_realizados(self):
        return self.pagos.aggregate(total=Sum('monto'))['total'] or 0

    def saldo(self):
        pagos = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        return self.costo_curso - self.primer_pago - pagos

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
    fecha = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("curso", "numero")
        ordering = ["numero"]

    @property
    def nombre(self):
        # Alias para compatibilidad (si en views/templates usas unidad.nombre)
        return self.nombre_tema

    def __str__(self):
        return f"{self.curso.nombre} - Unidad {self.numero}: {self.nombre_tema}"


class AsistenciaUnidad(models.Model):
    matricula = models.ForeignKey('Matricula', on_delete=models.CASCADE, related_name='asistencias')
    unidad = models.ForeignKey('UnidadCurso', on_delete=models.CASCADE)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, null=True, blank=True)
    completado = models.BooleanField(default=False)
    fecha = models.DateField(null=True, blank=True)  # 🔹 NUEVO

    def __str__(self):
        return f"{self.matricula.alumno.nombre} - {self.unidad} - {self.fecha}"
    
    class Meta:
        unique_together = ('matricula', 'unidad', 'fecha')

class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('plin', 'Plin'),
        ('yape', 'Yape'),
        ('izipay', 'Izipay'),
        ('interbank', 'Interbank'),
        ('culqi', 'Culqi'),
        ('efectivo', 'Efectivo'),
    ]
    alumno = models.ForeignKey(
        "Alumno",
        on_delete=models.CASCADE,
        related_name="pagos_extra",
        null=True,
        blank=True,
    )
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.CASCADE,
        related_name='pagos',
        null=True,
        blank=True,
    )
    cuota = models.ForeignKey('Cuota', on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos')

    monto = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    creado_en = models.DateTimeField(default=timezone.now)
    fecha_pago_real = models.DateField(null=True, blank=True)

    metodo_pago = models.CharField(
        max_length=30,
        choices=[
            ('plin', 'Plin'),
            ('yape', 'Yape'),
            ('izipay', 'Izipay'),
            ('interbank', 'Interbank'),
            ('culqi', 'Culqi'),
            ('efectivo', 'Efectivo'),
        ],
        null=True,
        blank=True
    )

    concepto = models.CharField(
        max_length=50,
        choices=[
            ('anticipo', 'Anticipo'),
            ('cuota_1', 'Cuota 1'),
            ('cuota_2', 'Cuota 2'),
            ('reprogramacion', 'Reprogramación'),
        ]
    )
    
    detalle = models.CharField(max_length=200, null=True, blank=True)

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    activo = models.BooleanField(
        default=True
    )

    def __str__(self):
        nombre = "—"
        if self.matricula_id:
            nombre = self.matricula.alumno.nombre
        elif self.alumno_id:
            nombre = self.alumno.nombre
        return f"{nombre} - {self.concepto} - S/ {self.monto}"

class Cuota(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.CASCADE,
        related_name='cuotas'
    )
    numero = models.PositiveIntegerField()
    monto = models.DecimalField(
        max_digits=8, 
        decimal_places=2)
    fecha_vencimiento = models.DateField()
    pagado = models.BooleanField(default=False)
    monto_pagado = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    @property
    def saldo_cuota(self):
        pagado = self.monto_pagado or Decimal('0.00')
        saldo = (self.monto or Decimal('0.00')) - pagado
        if saldo < 0:
            saldo = Decimal('0.00')
        return saldo
    
    @property
    def esta_pagada(self):
        return self.saldo_cuota <= Decimal('0.00')
    
    def __str__(self):
        return f"Cuota {self.numero} - {self.matricula.alumno.nombre}"

class Egresado(models.Model):
    matricula = models.OneToOneField(Matricula, on_delete=models.CASCADE, related_name='egresado')
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alumno.nombre} - {self.curso.nombre} (Egresado)"
    
class Certificado(models.Model):
    matricula = models.OneToOneField('Matricula', on_delete=models.CASCADE, related_name='certificado')
    codigo = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateField(default=timezone.now)
    archivo_pdf = models.FileField(upload_to='certificados/', null=True, blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.matricula.alumno.nombre} - {self.matricula.curso.nombre}"
    
class Reprogramacion(models.Model):
    SOLICITANTE_CHOICES = (
        ("WEEIN", "Weein"),
        ("ALUMNO", "Alumno"),
    )

    matricula = models.ForeignKey("Matricula", on_delete=models.CASCADE, related_name="reprogramaciones_hist")
    clase = models.ForeignKey("Clase", on_delete=models.CASCADE, related_name="reprogramaciones_hist")

    fecha_anterior = models.DateField()
    fecha_nueva = models.DateField()

    solicitante = models.CharField(max_length=10, choices=SOLICITANTE_CHOICES)
    # quién lo registró (usuario logueado)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # Control de cobro
    monto = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pagado = models.BooleanField(default=False)
    pagado_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.matricula_id} {self.solicitante} {self.fecha_anterior} -> {self.fecha_nueva}"

class CategoriaServicio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre


class ServicioExtra(models.Model):
    categoria = models.ForeignKey(
        CategoriaServicio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servicios"
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nombre} (S/ {self.precio})"


class VentaServicio(models.Model):
    alumno = models.ForeignKey("Alumno", on_delete=models.CASCADE, related_name="ventas_servicios")
    matricula = models.ForeignKey("Matricula", on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas_servicios")
    servicio = models.ForeignKey(ServicioExtra, on_delete=models.PROTECT, related_name="ventas")

    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    metodo_pago = models.CharField(
        max_length=30,
        choices=[
            ('plin', 'Plin'),
            ('yape', 'Yape'),
            ('izipay', 'Izipay'),
            ('interbank', 'Interbank'),
            ('culqi', 'Culqi'),
            ('efectivo', 'Efectivo'),
        ],
        null=True,
        blank=True
    )
    fecha_pago_real = models.DateField(null=True, blank=True)

    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.precio_unitario or self.precio_unitario <= 0:
            self.precio_unitario = self.servicio.precio
        self.total = (self.precio_unitario * self.cantidad)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alumno.nombre} - {self.servicio.nombre} - S/ {self.total}"
    
class EntregaKit(models.Model):
    matricula = models.OneToOneField(
        "Matricula",
        on_delete=models.CASCADE,
        related_name="kit"
    )

    manual_entregado = models.BooleanField(default=False)
    manual_entregado_en = models.DateTimeField(null=True, blank=True)

    video_enviado = models.BooleanField(default=False)
    video_enviado_en = models.DateTimeField(null=True, blank=True)

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    creado_en = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Kit - Matricula #{self.matricula_id}"