# admin.py

from django.contrib import admin
from .models import FondosDisponibles

@admin.register(FondosDisponibles)
class FondosDisponiblesAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_administradora",
        "nombre_fondo",
        "id_fondo",
        "id_clase",
    )