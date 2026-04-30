"""
URL configuration for core project.
Configurado para el Sistema de Analítica - UCC Pasto
"""
from django.contrib import admin
from django.urls import path
from analytics import views  # Importamos las vistas de tu app de análisis

urlpatterns = [
    path('admin/', admin.site.urls),
    # Esta línea hace que la página principal (vacía) cargue tu web elegante
    path('', views.home, name='home'), 
]