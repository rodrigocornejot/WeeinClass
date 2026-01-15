from django import forms
from django.db.models import Q
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.fields import ArrayField
from .models import DAY_CHOICES
from .models import Curso, Nota, Alumno, Matricula, Tarea
from django.forms.widgets import DateInput, TimeInput


class CursoForm(forms.ModelForm):
    # Hacemos que el campo nombre sea un CharField para ingresar el nombre del curso manualmente
    nuevo_curso = forms.CharField(
        max_length=100,
        required=False,
        label="Nuevo Curso",
        widget=forms.TextInput(attrs={'placeholder': 'Escribe un nuevo curso'})
    )
    # Usamos el widget DateInput para mostrar el calendario
    fecha = forms.DateField(widget=DateInput(attrs={'type': 'date'}), required=True)

    # Usamos el widget TimeInput para mostrar un reloj para la hora
    horario = forms.TimeField(widget=TimeInput(attrs={'type': 'time'}), required=True)

    class Meta:
        model = Curso
        fields = ['nombre', 'fecha', 'horario', 'duracion', 'profesor']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cursos_existentes = Curso.objects.values_list('nombre', 'nombre')
        self.fields['nombre'] = forms.ChoiceField(
            choices=[('', 'Selecciona un curso')] + list(cursos_existentes),
            required=False,
        )
    def clean(self):
        cleaned_data = super().clean()
        nombre_existente = cleaned_data.get('nombre')  # Esto es lo que el usuario escribe o selecciona
        nuevo_nombre = cleaned_data.get('nuevo_curso')
        # Si no se ingresa un nombre ni un curso nuevo, mostrar error
        if not nombre_existente and not nuevo_nombre:
            raise forms.ValidationError("Debes escribir el nombre de un curso")

        return cleaned_data

DAY_CHOICES = [
    ('lunes', 'Lunes'),
    ('martes', 'Martes'),
    ('miercoles', 'Miércoles'),
    ('jueves', 'Jueves'),
    ('viernes', 'Viernes'),
    ('sabado', 'Sábado'),
    ('domingo', 'Domingo'),
]

class MatriculaForm(forms.ModelForm):
    fechas_personalizadas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Ej: 2026-01-15,2026-01-20,2026-02-10'
        })
    )

    class Meta:
        model = Matricula
        fields = '__all__'

    dias = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Matricula
        fields = [
            'curso',
            'modalidad',
            'tipo_horario',
            'fecha_inicio',
            'costo_curso',
            'primer_pago',
            'porcentaje',
            'dias',
        ]

        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        tipo = cleaned_data.get('tipo_horario')
        dias = cleaned_data.get('dias')

        # 🔥 FULL Y EXTENDIDA EXIGEN DÍAS
        if tipo in ['full', 'extendida'] and not dias:
            raise forms.ValidationError(
                "Debes ingresar al menos un día de estudio."
            )

        return cleaned_data

class MatriculaAdminForm(forms.ModelForm):
    class Meta:
        model = Matricula
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # En lugar de: choices=self.fields['dias_estudio'].choices
        self.fields['dias_estudio'].widget = forms.CheckboxSelectMultiple(choices=DAY_CHOICES
)

class NotaForm(forms.ModelForm):
    alumno = forms.ModelChoiceField(queryset=Alumno.objects.all())

    class Meta:
        model = Nota
        fields = ['alumno','matricula', 'nota']
        widgets = {
            'alumno': forms.Select(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'nota': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ['nombre', 'correo', 'telefono', 'dni', 'grado_academico', 'carrera', 'trabajo', 'referencia',
            'edad', 'sexo', 'distrito', 'departamento', 'pais', 'uso_imagen'
        ]

        widgets = {
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'uso_imagen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = '__all__'
