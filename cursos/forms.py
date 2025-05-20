from django import forms
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

MODALIDAD_CHOICES = [
    ('extendida', 'Extendida'),
    ('full_day', 'Full Day')
]

class MatriculaForm(forms.ModelForm):

    modalidad = forms.ChoiceField(
        choices=MODALIDAD_CHOICES,
        error_messages={'invalid_choice': 'Modalidad invalida'}
    )

    dias_estudio = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Matricula
        fields = [
            'alumno', 'curso', 'modalidad',
            'turno', 'dias_estudio', 'saldo_pendiente',
            'fecha_inicio', 'numero_semanas'
        ]

        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

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
        fields = ['nombre', 'correo', 'telefono']

class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = '__all__'
