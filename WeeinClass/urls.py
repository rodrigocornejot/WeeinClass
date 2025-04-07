"""
URL configuration for WeeinClass project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from cursos.views import mi_login_view  # o desde donde hayas definido la vista
from django.shortcuts import redirect

# Vista rápida para la página principal
def home(request):
    # Redirige a la vista de menú principal, pero solo si el usuario ya está autenticado
    if request.user.is_authenticated:
        # Verifica si es administrador o profesor y redirige en consecuencia
        if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
            return redirect('menu_admin')
        elif request.user.groups.filter(name='Profesores').exists():
            return redirect('vista_calendario')
    return redirect('login')  # Si no está autenticado, redirige al login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', mi_login_view, name='login'),
    path('accounts/', include('django.contrib.auth.urls')), # Esto incluye las rutas de login, logout, etc.

    path('cursos/', include('cursos.urls')),
    path('', home, name='home'),  # Página principal
]


