from rest_framework import serializers
from .models import Matricula  # Asegúrate de que tienes el modelo Matricula

class MatriculaSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.CharField(source='alumno.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)

    class Meta:
        model = Matricula
        fields = ['id', 'alumno_nombre', 'curso_nombre', 'modalidad', 'turno', 'dias_estudio', 'saldo_pendiente']
