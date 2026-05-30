# views.py
from django.shortcuts import render
from django.http import JsonResponse
import requests
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup


def mackinlays(request):
    return render(request, "mackinlays/index.html")


def cafci_mm(request):
    url = "https://estadisticas.cafci.org.ar/v2/fondos-mercado-de-dinero.json"
    r = requests.get(url, timeout=30)
    return JsonResponse(r.json(), safe=False)


def cafci_rendimiento(request, fondo, clase):
    url = f"https://estadisticas.cafci.org.ar/fondos/{fondo}?clase={clase}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        rendimientos = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 2:
                label = tds[0].get_text(strip=True)
                valor = tds[1].get_text(strip=True)
                valor_num = valor.replace("%", "").replace(",", ".").strip()
                try:
                    rendimientos[label] = float(valor_num)
                except ValueError:
                    rendimientos[label] = None

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        "fondo_id": fondo,
        "clase_id": clase,
        "rendimientos": rendimientos,
    })


def cafci_todos(request):
    mm_data = []
    try:
        r = requests.get(
            "https://estadisticas.cafci.org.ar/v2/fondos-mercado-de-dinero.json",
            timeout=30
        )
        mm_data = r.json()
    except Exception:
        pass

    fondos_t1_param = request.GET.get("fondos", "")
    fondos_t1 = []
    if fondos_t1_param:
        for par in fondos_t1_param.split(","):
            try:
                fondo_id, clase_id = par.strip().split("-")
                fondos_t1.append((int(fondo_id), int(clase_id)))
            except ValueError:
                pass

    hoy = date.today()
    periodos = {
        "dias_7":   hoy - timedelta(days=7),
        "mes_1":    hoy - timedelta(days=30),
        "meses_12": hoy - timedelta(days=365),
    }

    def fetch_fondo(fondo_id, clase_id):
        resultado = {"fondo_id": fondo_id, "clase_id": clase_id, "rendimientos": {}}
        for nombre, desde in periodos.items():
            url = (
                f"https://api.cafci.org.ar/fondo/{fondo_id}/clase/{clase_id}"
                f"/rendimiento/{desde.strftime('%Y-%m-%d')}/{hoy.strftime('%Y-%m-%d')}"
            )
            try:
                r = requests.get(url, timeout=15)
                data = r.json()
                resultado["rendimientos"][nombre] = data.get("data", {}).get("rendimiento")
            except Exception:
                resultado["rendimientos"][nombre] = None
        return resultado

    t1_results = []
    if fondos_t1:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_fondo, fondo_id, clase_id)
                for fondo_id, clase_id in fondos_t1
            ]
            t1_results = [f.result() for f in futures]

    return JsonResponse({
        "t0": mm_data,
        "t1": t1_results,
    })