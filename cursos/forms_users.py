from django import forms
from django.contrib.auth.models import User

class CrearUsuarioForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

    ROL_CHOICES = (
        ("Administradores", "Admin"),
        ("Asesoras", "Asesora"),
        ("Profesores", "Profesor"),
    )
    rol = forms.ChoiceField(choices=ROL_CHOICES, label="Rol")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return u

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned
