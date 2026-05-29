from django.shortcuts import render
from django.http import JsonResponse
import json
import math


def simulacion_renta(request):
    """Vista principal — renderiza el template."""
    return render(request, 'simulacion/index.html')


def calcular(request):
    """
    API endpoint: recibe JSON con los parámetros de cada escenario
    y devuelve los resultados calculados.

    POST body:
    {
        "tasa_anual": 0.0475,
        "perfil": "Moderado",
        "escenarios": [
            {"capital": 85000, "anios": 1},
            {"capital": 45000, "anios": 3},
            {"capital": 41000, "anios": 15},
            {"capital": 41000, "anios": 20}
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    tasa_anual = float(data.get('tasa_anual', 0.0475))
    perfil = data.get('perfil', 'Moderado')
    escenarios_input = data.get('escenarios', [])

    resultados = []
    for esc in escenarios_input:
        capital = float(esc.get('capital', 0))
        anios = int(esc.get('anios', 1))
        res = _calcular_escenario(capital, anios, tasa_anual)
        resultados.append(res)

    return JsonResponse({
        'tasa_anual': tasa_anual,
        'perfil': perfil,
        'escenarios': resultados,
    })


# ─── Cálculos financieros ────────────────────────────────────────────────────

def _retiro_mensual(capital: float, anios: int, tasa_anual: float) -> float:
    """
    Fórmula de valor presente de anualidad:
        PMT = PV * r / (1 - (1+r)^-n)
    donde r = tasa mensual, n = cantidad de meses.
    """
    r = tasa_anual / 12
    n = anios * 12
    if r == 0:
        return capital / n if n > 0 else 0.0
    pmt = capital * r / (1 - (1 + r) ** -n)
    return pmt


def _tabla_anual(capital_inicial: float, retiro_anual: float,
                 tasa_anual: float, max_anios: int = 50) -> list:
    """
    Genera la tabla año a año replicando las fórmulas del Excel:
        Interés      = Capital * tasa_anual
        Capital_sig  = Capital + Interés - Retiro_anual
    """
    tabla = []
    capital = capital_inicial
    for anio in range(1, max_anios + 1):
        interes = capital * tasa_anual
        capital_fin = capital + interes - retiro_anual
        tabla.append({
            'anio': anio,
            'capital_inicio': round(capital, 2),
            'interes': round(interes, 2),
            'retiro_anual': round(retiro_anual, 2),
            'capital_fin': round(capital_fin, 2),
        })
        capital = capital_fin
        if capital <= 0:
            break
    return tabla


def _calcular_escenario(capital: float, anios: int,
                        tasa_anual: float) -> dict:
    """Calcula todos los valores de un escenario."""
    ret_mes = _retiro_mensual(capital, anios, tasa_anual)
    ret_anual = ret_mes * 12
    tabla = _tabla_anual(capital, ret_anual, tasa_anual, max_anios=max(anios + 5, 50))
    return {
        'capital': capital,
        'anios': anios,
        'retiro_mensual': round(ret_mes, 2),
        'retiro_anual': round(ret_anual, 2),
        'tabla': tabla,
    }
