from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


# =========================================================
# Helpers
# =========================================================

def _tiene_grupo(user, *nombres):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=nombres).exists()


# =========================================================
# Decorator (REDIRECT) -> para páginas normales
# =========================================================

def en_grupo_redirect(*group_names, redirect_to="menu_admin", msg=None):
    """
    Permite acceso si pertenece a alguno de los grupos indicados.
    Si no tiene permisos: muestra mensaje y redirige (por defecto a menu_admin).
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if _tiene_grupo(request.user, *group_names):
                return view_func(request, *args, **kwargs)

            messages.error(request, msg or "No tienes permisos para acceder a esta página.")
            return redirect(redirect_to)
        return _wrapped
    return decorator


# =========================================================
# Decorator (403) -> para AJAX/API (mejor que redirect)
# =========================================================

def en_grupo_403(*group_names):
    """
    Permite acceso si pertenece a alguno de los grupos indicados.
    Si no tiene permisos: devuelve 403.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if _tiene_grupo(request.user, *group_names):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos.")
        return _wrapped
    return decorator


# =========================================================
# GRUPOS "canon" de tu proyecto (tolerantes a variantes)
# =========================================================

GRUPO_ADMIN = ("Administradores", "Admin")
GRUPO_ASESORA = ("Asesora", "Asesoras", "Recepcion", "Recepción")
GRUPO_PROFESOR = ("Profesor", "Profesores")
GRUPO_MARKETING = ("Marketing",)


# =========================================================
# DECORATORS LISTOS PARA USAR (REDIRECT)
# =========================================================

solo_admin = en_grupo_redirect(*GRUPO_ADMIN)

solo_asesora = en_grupo_redirect(*GRUPO_ADMIN, *GRUPO_ASESORA)

solo_profesor = en_grupo_redirect(*GRUPO_ADMIN, *GRUPO_PROFESOR)

asesora_o_profesor = en_grupo_redirect(*GRUPO_ADMIN, *GRUPO_ASESORA, *GRUPO_PROFESOR)

# opcional útil
admin_o_marketing = en_grupo_redirect(*GRUPO_ADMIN, *GRUPO_MARKETING)

admin_o_asesora_o_marketing = en_grupo_redirect(*GRUPO_ADMIN, *GRUPO_ASESORA, *GRUPO_MARKETING)


# =========================================================
# DECORATOR FLEXIBLE (REDIRECT) por roles
# =========================================================

def roles_requeridos(*roles, redirect_to="menu_admin"):
    """
    Permite acceso si el usuario pertenece a alguno de los grupos indicados.
    Ejemplo:
        @roles_requeridos("Administradores", "Asesora")
    """
    return en_grupo_redirect(*roles, redirect_to=redirect_to)

def en_grupo_403(*group_names):
    """
    Igual que en_grupo pero en vez de redirigir, devuelve 403 Forbidden.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
        return _wrapped
    return decorator