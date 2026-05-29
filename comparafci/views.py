from django.shortcuts import render
from django.http import JsonResponse
import requests


def mackinlays(request):
    return render(request, "mackinlays/index.html")


def cafci_mm(request):
    url = "https://estadisticas.cafci.org.ar/v2/fondos-mercado-de-dinero.json"

    r = requests.get(url, timeout=30)

    return JsonResponse(r.json(), safe=False)

