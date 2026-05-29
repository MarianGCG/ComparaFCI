from django.contrib import admin
from django.urls import path, include


from comparafci.views import (
    mackinlays,
    cafci_mm,
)


from django.shortcuts import redirect
urlpatterns = [

    path('admin/', admin.site.urls),
    path('mackinlays/', mackinlays, name='mackinlays'),
    path('cafci-mm/', cafci_mm, name='cafci_mm'),

]
