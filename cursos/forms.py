from django import forms
from django.db.models import Q
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.fields import ArrayField
from .models import DAY_CHOICES
from .models import Curso, Nota, Alumno, Matricula, Tarea, ServicioExtra, CategoriaServicio, VentaServicio, Pago
from django.forms.widgets import DateInput, TimeInput
from .models import Curso, CURSO_CHOICES 

class CursoForm(forms.ModelForm):
    fecha = forms.DateField(widget=DateInput(attrs={'type': 'date'}), required=True)
    horario = forms.TimeField(widget=TimeInput(attrs={'type': 'time'}), required=True)

    class Meta:
        model = Curso
        fields = ['nombre', 'fecha', 'horario', 'duracion', 'profesor']

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

class PagoCuotaForm(forms.Form):
    monto = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=8)
    fecha_pago = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    metodo_pago = forms.ChoiceField(choices=Pago.METODO_PAGO_CHOICES)

class CategoriaServicioForm(forms.ModelForm):
    class Meta:
        model = CategoriaServicio
        fields = ["nombre", "activo"]

class ServicioForm(forms.ModelForm):
    class Meta:
        model = ServicioExtra
        fields = ["nombre", "precio", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Manual PLC Nivel 1"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class VentaServicioForm(forms.ModelForm):
    class Meta:
        model = VentaServicio
        fields = ["servicio", "cantidad", "metodo_pago", "fecha_pago_real"]