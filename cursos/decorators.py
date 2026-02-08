from django.contrib.auth.decorators import user_passes_test

def en_grupo(*group_names):
    def check(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=group_names).exists()
    return user_passes_test(check)

solo_admin = en_grupo("Administradores")
solo_asesora = en_grupo("Asesoras", "Administradores")
solo_profesor = en_grupo("Profesores", "Administradores")
asesora_o_profesor = en_grupo("Asesoras", "Profesores", "Administradores")
