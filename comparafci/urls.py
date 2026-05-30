
from django.contrib import admin
from django.urls import path

from comparafci.views import (
    mackinlays,
    cafci_mm,
    cafci_rendimiento,
    cafci_todos,
)

from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mackinlays/', mackinlays, name='mackinlays'),
    path('cafci-mm/', cafci_mm, name='cafci_mm'),
    path('cafci-rendimiento/<int:fondo>/<int:clase>/', cafci_rendimiento, name='cafci_rendimiento'),
    path('cafci-todos/', cafci_todos, name='cafci_todos'),
]
