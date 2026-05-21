"""
URL configuration for core project.
Configurado para el Sistema de Analítica - UCC Pasto
"""
from django.contrib import admin
from django.urls import path
from analytics import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('anova/', views.anova_view, name='anova'),
    path('chatbot/', views.chatbot_page, name='chatbot'),
    path('api/chat/', views.chat_api, name='chat_api'),
]
