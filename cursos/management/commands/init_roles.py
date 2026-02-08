from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Crea los grupos base del sistema"

    def handle(self, *args, **kwargs):

        grupos = [
            "Administradores",
            "Asesoras",
            "Profesores",
        ]

        for nombre in grupos:
            Group.objects.get_or_create(name=nombre)

        self.stdout.write(self.style.SUCCESS("✅ Grupos creados correctamente"))
