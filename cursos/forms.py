from django import forms
from django.db.models import Q
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.fields import ArrayField
from .models import DAY_CHOICES
from .models import Curso, Nota, Alumno, Matricula, Tarea, ServicioExtra, CategoriaServicio, VentaServicio, Pago
from django.forms.widgets import DateInput, TimeInput
from .models import Curso, CURSO_CHOICES 
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
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
    # ✅ nuevo: checkbox para activar personalización
    personalizar_fechas = forms.BooleanField(required=False, initial=False)

    # ✅ ya no necesitamos fechas_personalizadas texto
    # los inputs sesion_1..sesion_6 se leen directo desde request.POST

    dias = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Matricula
        fields = [
            'curso',
            'modalidad',       # full / extendida
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
        cleaned = super().clean()

        modalidad = (cleaned.get("modalidad") or "").strip().lower()
        dias = cleaned.get("dias") or []
        personalizar = cleaned.get("personalizar_fechas") is True

        # ✅ si no personaliza, extendida necesita días
        if not personalizar and modalidad == "extendida" and not dias:
            raise forms.ValidationError("Debes ingresar al menos un día de estudio para Extendida.")

        # ✅ full day NO necesita días cuando es automático (porque es 1 clase por semana)
        # pero si quieres que full day SI pida días, lo hacemos en la vista cuando personalizar=false (opcional)

        return cleaned

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

ROLES = (
    ("Admin", "Admin"),
    ("Asesora", "Asesora"),
    ("Profesor", "Profesor"),
    ("Marketing", "Marketing"),
)

class UsuarioCreateForm(UserCreationForm):
    first_name = forms.CharField(required=False, label="Nombres")
    last_name = forms.CharField(required=False, label="Apellidos")
    email = forms.EmailField(required=False, label="Correo")
    rol = forms.ChoiceField(choices=ROLES, label="Rol")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            self._asignar_grupo(user)
        return user

    def _asignar_grupo(self, user: User):
        rol = self.cleaned_data.get("rol")
        if not rol:
            return
        # asegura el grupo
        g, _ = Group.objects.get_or_create(name=rol)
        user.groups.clear()
        user.groups.add(g)
        user.save()


class UsuarioUpdateForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=ROLES, label="Rol")
    password1 = forms.CharField(
        required=False, label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        required=False, label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # rol actual
        if self.instance and self.instance.pk:
            g = self.instance.groups.first()
            if g:
                self.fields["rol"].initial = g.name

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if (p1 or p2) and (p1 != p2):
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        # password opcional
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)

        if commit:
            user.save()
            # asignar rol
            rol = self.cleaned_data.get("rol")
            g, _ = Group.objects.get_or_create(name=rol)
            user.groups.clear()
            user.groups.add(g)
            user.save()
        return user