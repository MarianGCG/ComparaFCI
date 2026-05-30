# models.py

from django.db import models

class FondosDisponibles(models.Model):
    nombre_administradora = models.CharField(max_length=100)
    nombre_fondo = models.CharField(max_length=200)
    id_fondo = models.IntegerField()
    id_clase = models.IntegerField()

    def __str__(self):
        return self.nombre_fondo
    
