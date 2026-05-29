from django.urls import path
from . import views

urlpatterns = [
    path('', views.simulacion_renta, name='simulacion_renta'),
    path('calcular/', views.calcular, name='simulacion_calcular'),
]
