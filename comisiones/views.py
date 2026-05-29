from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q, DecimalField, Value
from django.db.models.functions import Coalesce, Cast


from django.db import connection
from .models import ComprobantesComisiones
import json
from .services.aseguradoras_service import importar_aseguradoras_excel
from .services.parametros_service import get_parametro

from django.db.models.functions import Cast
from django.db.models import IntegerField

import numpy as np
from django.http import HttpResponse
from io import BytesIO

from .models import ParametroSistema
from .models import Aseguradoras

import io
import base64




def ver_comprobantes(request):

    from .models import Aseguradoras
    from django.db.models import F

    anio = request.GET.get("anio")
    mes = request.GET.get("mes")

    if anio:
        anio = anio.replace(".", "")

    if mes:
        mes = mes.replace(".", "")

    # si no se indicó filtro, usar último período cargado
    if not anio and not mes:

        ultimo = ComprobantesComisiones.objects.order_by(
            "-periodo_anio", "-periodo_mes"
        ).values("periodo_anio", "periodo_mes").first()

        if ultimo:
            anio = ultimo["periodo_anio"]
            mes = ultimo["periodo_mes"]

    aseguradora = request.GET.get("aseguradora")
    numero = request.GET.get("numero")

    comprobantes = ComprobantesComisiones.objects.all()

    # ============================
    # 🔎 FILTROS
    # ============================

    if anio:
        comprobantes = comprobantes.filter(periodo_anio=anio)

    if mes:
        comprobantes = comprobantes.filter(periodo_mes=mes)

    if aseguradora:
        comprobantes = comprobantes.filter(
            aseguradora__id=aseguradora   # 🔥 IMPORTANTE: ahora es combo
        )

    if numero:
        comprobantes = comprobantes.filter(
            numero_comprobante__icontains=numero
        )

    # ============================
    # 💰 COBRADO DINÁMICO
    # ============================

    comprobantes = comprobantes.annotate(
        cobrado=Coalesce(
            Sum("cobranzascomisiones__importe"),
            Value(0),
            output_field=DecimalField()
        )
    )

    # ============================
    # 🔢 NUMERO COMO ENTERO
    # ============================

    comprobantes = comprobantes.annotate(
        numero_int=Cast("numero_comprobante", IntegerField())
    )
    comprobantes = comprobantes.annotate(
        subtotal=
            Coalesce(
                F("neto"),
                Value(0),
                output_field=DecimalField()
            )
            +
            Coalesce(
                F("no_gravado"),
                Value(0),
                output_field=DecimalField()
            )
            +
            Coalesce(
                F("exento"),
                Value(0),
                output_field=DecimalField()
            )
    )

    # ============================
    # 🔥 ORDEN POR COLUMNAS
    # ============================

    orden = request.GET.get("orden")
    dir = request.GET.get("dir", "asc")

    if orden:

        campo_map = {
            "aseguradora": "aseguradora__nombre",
            "periodo": "periodo_anio",
            "numero": "numero_int",
            "neto": "neto",
            "total": "total",
            "cobrado": "cobrado",
        }

        campo_db = campo_map.get(orden)

        if campo_db:

            if orden == "periodo":
                if dir == "desc":
                    comprobantes = comprobantes.order_by("-periodo_anio", "-periodo_mes")
                else:
                    comprobantes = comprobantes.order_by("periodo_anio", "periodo_mes")
            else:
                if dir == "desc":
                    campo_db = "-" + campo_db

                comprobantes = comprobantes.order_by(campo_db)

    else:
        comprobantes = comprobantes.order_by(
            "aseguradora__nombre",
            "periodo_anio",
            "periodo_mes",
            "numero_int"
        )

    # ============================
    # 📊 TOTALES (🔥 ESTO FALTABA)
    # ============================

    totales = {

        "sum_neto":
            sum(c.neto or 0 for c in comprobantes),

        "sum_no_gravado":
            sum(c.no_gravado or 0 for c in comprobantes),

        "sum_exento":
            sum(c.exento or 0 for c in comprobantes),

        "subtotal":
            sum(
                (c.neto or 0)
                + (c.no_gravado or 0)
                + (c.exento or 0)
                for c in comprobantes
            ),

        "sum_iva":
            sum(c.iva or 0 for c in comprobantes),

        "sum_total":
            sum(c.total or 0 for c in comprobantes),

        "sum_cobrado":
            sum(c.cobrado or 0 for c in comprobantes),
    }


    # ============================
    # 📊 GRAFICO ASEGURADORAS
    # ============================

    grafico_neto = (
        comprobantes
        .values("aseguradora__nombre")
        .annotate(

            subtotal_aseg =

                Coalesce(Sum("neto"), Value(0), output_field=DecimalField())

                +

                Coalesce(Sum("no_gravado"), Value(0), output_field=DecimalField())

                +

                Coalesce(Sum("exento"), Value(0), output_field=DecimalField())

        )
        .order_by("-subtotal_aseg")
    )



    grafico_cobrado = (
        comprobantes
        .values("aseguradora__nombre")
        .annotate(

            cobrado_aseg =

                Coalesce(
                    Sum("cobranzascomisiones__importe"),
                    Value(0),
                    output_field=DecimalField()
                )

        )
        .order_by("-cobrado_aseg")
    )

    labels_neto = [
        x["aseguradora__nombre"]
        for x in grafico_neto
    ]

    datos_neto = [
        float(x["subtotal_aseg"])
        for x in grafico_neto
    ]



    labels_cobrado = [
        x["aseguradora__nombre"]
        for x in grafico_cobrado
    ]

    datos_cobrado = [
        float(x["cobrado_aseg"])
        for x in grafico_cobrado
    ]

    # ============================
    # 🎯 RENDER FINAL
    # ============================

    return render(request, "ver_comprobantes.html", {
        "comprobantes": comprobantes,
        "totales": totales,
        "anio": anio,
        "mes": mes,
        "aseguradoras": Aseguradoras.objects.all(),
        "labels_neto": json.dumps(labels_neto),
        "datos_neto": json.dumps(datos_neto),
        "labels_cobrado": json.dumps(labels_cobrado),
        "datos_cobrado": json.dumps(datos_cobrado),

    })


# =====================================================
# 2️⃣ VER SALDOS POR PERIODO
# =====================================================
from django.db.models import F, DecimalField, Value
from django.db.models.functions import Coalesce
from .models import CobranzasComisiones

def ver_saldos(request):

    anio = request.GET.get("anio")

    try:
        anio = int(anio)
    except:
        anio = None

    comprobantes = ComprobantesComisiones.objects.all()

    if anio:
        comprobantes = comprobantes.filter(periodo_anio=anio)

    # ============================
    # AGRUPADO
    # ============================

    saldos = (
        comprobantes
        .values("periodo_anio", "periodo_mes")
        .annotate(

            cant_facturas=Count("id", filter=Q(tipo_comprobante="FACTURA"), distinct=True),
            cant_creditos=Count("id", filter=Q(tipo_comprobante="NOTA_CREDITO"), distinct=True),


            sum_neto=Coalesce(Sum("neto"), Value(0), output_field=DecimalField()),
            sum_no_gravado=Coalesce(Sum("no_gravado"), Value(0), output_field=DecimalField()),
            sum_exento=Coalesce(Sum("exento"), Value(0), output_field=DecimalField()),

            subtotal=(
                Coalesce(Sum("neto"), Value(0), output_field=DecimalField())
                +
                Coalesce(Sum("no_gravado"), Value(0), output_field=DecimalField())
                +
                Coalesce(Sum("exento"), Value(0), output_field=DecimalField())
            ),


            sum_iva=Coalesce(Sum("iva"), Value(0), output_field=DecimalField()),
            sum_total=Coalesce(Sum("total"), Value(0), output_field=DecimalField()),
            
        )
    )

    # ============================
    # 🔥 ORDEN (CLAVE)
    # ============================

    orden = request.GET.get("orden")
    dir = request.GET.get("dir", "asc")

    campo_map = {
        "periodo": ["periodo_anio", "periodo_mes"],
        "fact": "cant_facturas",
        "cred": "cant_creditos",
        "neto": "sum_neto",
        "total": "sum_total",
        "cobrado": "sum_cobrado",

    }

    if orden in campo_map:

        campo = campo_map[orden]

        if isinstance(campo, list):
            if dir == "desc":
                saldos = saldos.order_by("-periodo_anio", "-periodo_mes")
            else:
                saldos = saldos.order_by("periodo_anio", "periodo_mes")

        else:
            if dir == "desc":
                saldos = saldos.order_by(F(campo).desc(nulls_last=True))
            else:
                saldos = saldos.order_by(F(campo).asc(nulls_last=True))

    else:
        saldos = saldos.order_by("-periodo_anio", "-periodo_mes")

 
    from .models import CotizacionesDolar


    for s in saldos:

        dolar = CotizacionesDolar.objects.filter(
            periodo_anio=s["periodo_anio"],
            periodo_mes=s["periodo_mes"]
        ).first()

        if dolar and dolar.valor:

            s["ST_usd"] = s["subtotal"] / dolar.valor

        else:

            s["ST_usd"] = 0


        cobrado = CobranzasComisiones.objects.filter(
            comprobante__periodo_anio=s["periodo_anio"],
            comprobante__periodo_mes=s["periodo_mes"]
        ).aggregate(

            total=Coalesce(
                Sum("importe"),
                Value(0),
                output_field=DecimalField()
            )
        )

        s["sum_cobrado"] = cobrado["total"]


   # ============================
    # TOTALES
    # ============================

    totales = {

        "total_facturas":
            sum(s["cant_facturas"] for s in saldos),

        "total_creditos":
            sum(s["cant_creditos"] for s in saldos),

        "sum_neto":
            sum(s["sum_neto"] for s in saldos),

        "sum_no_gravado":
            sum(s["sum_no_gravado"] for s in saldos),

        "sum_exento":
            sum(s["sum_exento"] for s in saldos),

        "subtotal":
            sum(s["subtotal"] for s in saldos),

        "sum_iva":
            sum(s["sum_iva"] for s in saldos),

        "sum_total":
            sum(s["sum_total"] for s in saldos),

        "sum_cobrado":
            sum(s["sum_cobrado"] for s in saldos),

        "total_usd":
            sum(s["ST_usd"] for s in saldos),
                        
    }




    return render(request, "ver_saldos.html", {
        "saldos": saldos,
        "totales": totales,
        "anio": anio
    })
# =====================================================
# FUNCIÓN: tendencia lineal
# =====================================================
def calcular_tendencia_lineal(valores):

    n = len(valores)

    if n < 2:
        return valores

    x = list(range(n))

    sum_x = sum(x)
    sum_y = sum(valores)
    sum_xy = sum(x[i] * valores[i] for i in range(n))
    sum_x2 = sum(x[i] ** 2 for i in range(n))

    denominador = (n * sum_x2 - sum_x ** 2)

    if denominador == 0:
        return valores

    m = (n * sum_xy - sum_x * sum_y) / denominador
    b = (sum_y - m * sum_x) / n

    return [(m * i + b) for i in x]


# =====================================================
# GRAFICOS 01 (ANUAL / TRIMESTRAL / MENSUAL)
# =====================================================

def graficos01(request):

    import json
    from django.db import connection
    from django.shortcuts import render
    from .services.parametros_service import get_parametro
    from .models import Aseguradoras

    tipo = request.GET.get("tipo", "mensual")
    modo = request.GET.get("modo", "lineas")
    desglose = request.GET.get("desglose") == "1"

    # ==========================
    # QUERY BASE
    # ==========================

    with connection.cursor() as cursor:

        if tipo == "mensual":

            cursor.execute("""
                SELECT
                    c.periodo_anio,
                    c.periodo_mes,
                    a.nombre,
                    COALESCE(a.color,'#2c78be'),
                    SUM((c.neto+c.no_gravado+c.exento)/NULLIF(d.valor,0))
                FROM comprobantes_comisiones c
                JOIN aseguradoras a ON a.id=c.aseguradora_id
                JOIN cotizaciones_dolar d
                  ON d.periodo_anio=c.periodo_anio
                 AND d.periodo_mes=c.periodo_mes
                GROUP BY c.periodo_anio,c.periodo_mes,a.nombre,a.color
                ORDER BY c.periodo_anio,c.periodo_mes
            """)

        elif tipo == "trimestral":

            cursor.execute("""
                SELECT
                    c.periodo_anio,
                    ((c.periodo_mes-1)/3+1)::int,
                    a.nombre,
                    COALESCE(a.color,'#2c78be'),

                    SUM((c.neto+c.no_gravado+c.exento)/NULLIF(d.valor,0))
                    

                FROM comprobantes_comisiones c
                JOIN aseguradoras a ON a.id=c.aseguradora_id
                JOIN cotizaciones_dolar d
                  ON d.periodo_anio=c.periodo_anio
                 AND d.periodo_mes=c.periodo_mes

                GROUP BY
                    c.periodo_anio,
                    ((c.periodo_mes-1)/3+1),
                    a.nombre,
                    a.color

                ORDER BY
                    c.periodo_anio,
                    ((c.periodo_mes-1)/3+1)
            """)

        else:  # anual

            cursor.execute("""
                SELECT
                    c.periodo_anio,
                    1,
                    a.nombre,
                    COALESCE(a.color,'#2c78be'),
                    SUM((c.neto+c.no_gravado+c.exento)/NULLIF(d.valor,0))
                FROM comprobantes_comisiones c
                JOIN aseguradoras a ON a.id=c.aseguradora_id
                JOIN cotizaciones_dolar d
                  ON d.periodo_anio=c.periodo_anio
                 AND d.periodo_mes=c.periodo_mes
                GROUP BY c.periodo_anio,a.nombre,a.color
                ORDER BY c.periodo_anio
            """)

        rows = cursor.fetchall()

    if not rows:
        return render(request, "graficos01.html", {
            "labels": "[]",
            "datasets": "[]",
            "tipo": tipo,
            "modo": modo,
            "desglose": desglose,
            "anios_disponibles": [],
            "anios_seleccionados": []
        })

    # ==========================
    # AÑOS
    # ==========================

    anios_disponibles = sorted({r[0] for r in rows})
    anios_raw = request.GET.getlist("anio")

    if anios_raw:
        anios_seleccionados = [int(a) for a in anios_raw if str(a).isdigit()]
    else:
        cant = int(get_parametro("CANTIDAD_ANIOS_DEFAULT", 4))
        anios_seleccionados = anios_disponibles[-cant:]

    # ==========================
    # ORGANIZAR DATA
    # ==========================

    data = {}
    colores = {}

    for anio, periodo, aseg, color, total in rows:

        if anio not in anios_seleccionados:
            continue

        if tipo == "mensual":
            label = f"{anio}-{periodo:02d}"
        elif tipo == "trimestral":
            label = f"{anio}-T{periodo}"
        else:
            label = str(anio)

        if label not in data:
            data[label] = {}

        data[label][aseg] = float(total or 0)
        colores[aseg] = color

    labels = sorted(data.keys())

    # ==========================
    # DATASETS
    # ==========================

    datasets = []

    if desglose:

        for aseg, color in colores.items():

            valores = [data[label].get(aseg, 0) for label in labels]

            try:
                grupo = Aseguradoras.objects.get(nombre=aseg).grupo
            except:
                grupo = "Sin Grupo"

            datasets.append({
                "label": aseg,
                "grupo": grupo or "Sin Grupo",
                "data": valores,
                "borderColor": color,
                "backgroundColor": color,
                "tension": 0.25,
                "fill": False
            })

    else:

        valores = [sum(data[label].values()) for label in labels]

        # ==========================
        # TRIMESTRAL
        # ==========================
        if tipo == "trimestral":

            # 1️⃣ Facturación trimestral real
            datasets.append({
                "label": "Facturación trimestral USD",
                "data": valores,
                "borderColor": "#2c78be",
                "backgroundColor": "#2c78be",
                "tension": 0.25,
                "fill": False
            })

            # 2️⃣ Promedio mensual dentro del trimestre
            promedios = [v / 3 for v in valores]

            datasets.append({
                "label": "Promedio mensual trimestre",
                "data": promedios,
                "borderColor": "#c0392b",
                "backgroundColor": "#c0392b",
                "borderDash": [6,6],
                "tension": 0.25,
                "fill": False
            })

        # ==========================
        # MENSUAL / ANUAL
        # ==========================
        else:

            datasets.append({
                "label": "Facturación USD",
                "data": valores,
                "borderColor": "#2c78be",
                "backgroundColor": "#2c78be",
                "tension": 0.25,
                "fill": False
            })

    # ==========================
    # GRUPOS DESHABILITADOS
    # ==========================

    grupos_deshabilitados = []

    for i in range(1, 10):  # por si mañana agregás DESHABILITAR3,4,etc
        codigo = f"DESHABILITAR{i}"
        valor = get_parametro(codigo)
        if valor:
            grupos_deshabilitados.append(valor.strip())

    return render(request, "graficos01.html", {
        "labels": json.dumps(labels),
        "datasets": json.dumps(datasets),
        "tipo": tipo,
        "modo": modo,
        "desglose": desglose,
        "anios_disponibles": anios_disponibles,
        "anios_seleccionados": anios_seleccionados,
        "grupos_deshabilitados": json.dumps(grupos_deshabilitados)
    })



def graficos02(request):

    import io
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    from django.db import connection

    from .services.parametros_service import get_parametro

    # ===============================
    # Parámetros seguros
    # ===============================

    try:
        top_n = int(request.GET.get("top") or 5)
    except:
        top_n = 5

    try:
        tope = float(request.GET.get("tope") or 100)
    except:
        tope = 100.0


    # ===============================
    # QUERY
    # ===============================

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                c.periodo_anio,
                ((c.periodo_mes - 1) / 3 + 1)::int AS trimestre,
                a.nombre,
                COALESCE(a.color, '#3366cc') AS color,
                SUM((c.neto + c.no_gravado + c.exento) / d.valor) AS total_usd

            FROM comprobantes_comisiones c

            JOIN aseguradoras a
                ON a.id = c.aseguradora_id

            JOIN cotizaciones_dolar d
                ON c.periodo_anio = d.periodo_anio
                AND c.periodo_mes = d.periodo_mes

            GROUP BY
                c.periodo_anio,
                trimestre,
                a.nombre,
                a.color

            ORDER BY
                c.periodo_anio,
                trimestre;
        """)

        rows = cursor.fetchall()


    # ===============================
    # Sin datos
    # ===============================

    if not rows:

        return render(request, "graficos02.html", {
            "grafico": "",
            "top_n": top_n,
            "tope": tope,
            "anios_disponibles": [],
            "anios_seleccionados": []
        })


    # ===============================
    # Años disponibles
    # ===============================

    anios_disponibles = sorted(list({
        row[0] for row in rows
    }))


    # ===============================
    # Años seleccionados (GET o DEFAULT PARAMETRO)
    # ===============================

    anios_raw = request.GET.getlist("anio")

    if anios_raw:

        anios_seleccionados = []

        for a in anios_raw:
            try:
                anios_seleccionados.append(int(str(a).replace(".", "")))
            except:
                pass

    else:

        cantidad_default = int(get_parametro("CANTIDAD_ANIOS_DEFAULT", 5))

        cantidad_default = min(cantidad_default, len(anios_disponibles))

        anios_seleccionados = anios_disponibles[-cantidad_default:]


    # ===============================
    # Organizar datos (FILTRANDO AÑOS)
    # ===============================

    data = {}
    anio_por_periodo = {}
    color_map = {}

    for anio, trimestre, nombre, color, total in rows:

        if anio not in anios_seleccionados:
            continue

        periodo = f"{anio}-T{trimestre}"

        if periodo not in data:

            data[periodo] = {}
            anio_por_periodo[periodo] = anio

        data[periodo][nombre] = float(total)

        color_map[nombre] = color


    # ===============================
    # Si no hay datos luego del filtro
    # ===============================

    if not data:

        return render(request, "graficos02.html", {
            "grafico": "",
            "top_n": top_n,
            "tope": tope,
            "anios_disponibles": anios_disponibles,
            "anios_seleccionados": anios_seleccionados
        })


    periodos = sorted(data.keys())


    # ===============================
    # GRÁFICO
    # ===============================

    fig, ax = plt.subplots(figsize=(14,6))


    for idx, periodo in enumerate(periodos):

        trimestre_data = data[periodo]

        total_trimestre = sum(trimestre_data.values())

        participaciones = []

        for aseg, valor in trimestre_data.items():

            pct = (valor / total_trimestre) * 100 if total_trimestre > 0 else 0

            if pct <= tope:
                participaciones.append((aseg, valor, pct))

        participaciones.sort(key=lambda x: x[1], reverse=True)

        seleccionadas = participaciones[:top_n]

        bottom = 0

        for aseg, valor, pct in seleccionadas:

            color = color_map.get(aseg, "#3366cc")

            ax.bar(
                idx,
                valor,
                bottom=bottom,
                color=color
            )

            texto = aseg.title()

            if pct >= 0:
                texto += f"\n{pct:.0f}%"

            ax.text(
                idx,
                bottom + valor/2,
                texto,
                ha='center',
                va='center',
                color='white',
                fontsize=8,
                fontweight='bold'
            )

            bottom += valor


    # ===============================
    # Separadores de año
    # ===============================

    for i in range(1, len(periodos)):

        if anio_por_periodo[periodos[i]] != anio_por_periodo[periodos[i-1]]:

            ax.axvline(
                x=i-0.5,
                linestyle="--",
                linewidth=1,
                color="gray"
            )


    ax.set_xticks(range(len(periodos)))
    ax.set_xticklabels(periodos, rotation=45)

    ax.set_title(f"Facturación trimestral en USD - Top {top_n} ≤ {tope}%")

    formatter = FuncFormatter(lambda x, _: f"{x:,.0f}")
    ax.yaxis.set_major_formatter(formatter)

    plt.tight_layout()


    # ===============================
    # Convertir a imagen
    # ===============================

    buffer = io.BytesIO()

    plt.savefig(buffer, format='png')

    buffer.seek(0)

    grafico = base64.b64encode(buffer.getvalue()).decode('utf-8')

    buffer.close()

    plt.close()


    # ===============================
    # Render
    # ===============================

    return render(request, "graficos02.html", {

        "grafico": grafico,
        "top_n": top_n,
        "tope": tope,
        "anios_disponibles": anios_disponibles,
        "anios_seleccionados": anios_seleccionados

    })




def importar_aseguradoras_view(request):

    resultado = None

    if request.method == "POST":
        form = ImportarExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES["archivo"]
            resultado = importar_aseguradoras_excel(archivo)
    else:
        form = ImportarExcelForm()

    return render(request, "importaciones/form_importar.html", {
        "form": form,
        "resultado": resultado,
        "titulo": "Importar Aseguradoras"
    })




def actualizar_iva_aseguradora(request, id):

    if request.method == "POST":

        aseguradora = get_object_or_404(Aseguradoras, id=id)

        aseguradora.incluye_iva = request.POST.get("incluye_iva", "S")
        aseguradora.save()

    return redirect("aseguradoras")



def grafico_indice_mensual(request):

    import io
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter


    # ===============================
    # Años disponibles
    # ===============================
    anios_disponibles = list(
        ComprobantesComisiones.objects
        .values_list("periodo_anio", flat=True)
        .distinct()
        .order_by("periodo_anio")
    )

    from .services.parametros_service import get_parametro

    anios_raw = request.GET.getlist("anio")

    if anios_raw:

        anios_seleccionados = []

        for a in anios_raw:
            try:
                anios_seleccionados.append(int(str(a).replace(".", "")))
            except:
                pass

    else:

        cantidad_default = int(get_parametro("CANTIDAD_ANIOS_DEFAULT", 5))

        anios_seleccionados = anios_disponibles[-cantidad_default:]
        
        


        
    # ===============================
    # Año base dinámico desde parámetros
    # ===============================
    from .services.parametros_service import get_parametro

    anio_base_raw = request.GET.get("anio_base")

    if anio_base_raw:

        anio_base = int(str(anio_base_raw).replace(".", ""))

    else:

        anio_base_param = get_parametro("ANIO_BASE_INDICE")

        if anio_base_param is not None:

            anio_base = int(anio_base_param)

        else:

            anio_base = anios_disponibles[0]
                

    # ===============================
    # Query
    # ===============================
    placeholders = ",".join(["%s"] * len(anios_seleccionados))

    query = f"""
        SELECT
            c.periodo_anio,
            c.periodo_mes,
            SUM((c.neto + c.no_gravado + c.exento) / d.valor_promedio)
        FROM comprobantes_comisiones c
        JOIN (
            SELECT periodo_anio, periodo_mes, AVG(valor) AS valor_promedio
            FROM cotizaciones_dolar
            GROUP BY periodo_anio, periodo_mes
        ) d
        ON c.periodo_anio = d.periodo_anio
        AND c.periodo_mes = d.periodo_mes
        WHERE c.periodo_anio IN ({placeholders})
        GROUP BY c.periodo_anio, c.periodo_mes
        ORDER BY c.periodo_anio, c.periodo_mes;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, anios_seleccionados)
        rows = cursor.fetchall()

    if not rows:
        return render(request, "grafico_indice_mensual.html", {
            "grafico": "",
            "anios_disponibles": anios_disponibles,
            "anios_seleccionados": anios_seleccionados,
            "anio_base": anio_base
        })

    # ===============================
    # Organizar datos
    # ===============================
    data = {}

    for anio, mes, total in rows:
        if mes not in data:
            data[mes] = {}
        data[mes][anio] = float(total or 0)

    meses_ordenados = sorted(data.keys())

    anios = sorted({
        anio for anio_dict in data.values()
        for anio in anio_dict.keys()
    })

    # ===============================
    # Gráfico
    # ===============================
    fig, ax = plt.subplots(figsize=(14,6))

    x = np.arange(len(meses_ordenados))
    ancho = 0.25

    meses_nombre = ["Ene","Feb","Mar","Abr","May","Jun",
                    "Jul","Ago","Sep","Oct","Nov","Dic"]

    for i, anio in enumerate(anios):

        valores_usd = [
            data[mes].get(anio, 0)
            for mes in meses_ordenados
        ]

        posiciones = x + (i - len(anios)/2)*ancho + ancho/2

        ax.bar(posiciones, valores_usd, width=ancho, label=str(anio))

        # TEXTO
        for pos, mes, valor in zip(posiciones, meses_ordenados, valores_usd):

            base = data[mes].get(anio_base, 0)

            porcentaje = (valor / base) * 100 if base > 0 else 0

            if valor > 0:
                ax.text(
                    pos,
                    valor * 1.02,
                    f"USD {valor:,.0f}\n{porcentaje:.0f}%",
                    ha="center",
                    va="bottom",
                    fontsize=8
                )

    ax.set_xticks(x)
    ax.set_xticklabels([meses_nombre[m-1] for m in meses_ordenados])

    ax.set_ylabel("Facturación en USD")

    ax.set_title(f"Facturación Mensual en USD + % vs Base {anio_base}")

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=len(anios),
        frameon=False
    )

    formatter = FuncFormatter(lambda x, _: f"{x:,.0f}")
    ax.yaxis.set_major_formatter(formatter)

    plt.subplots_adjust(bottom=0.2)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render(request, "grafico_indice_mensual.html", {
        "grafico": grafico,
        "anios_disponibles": anios_disponibles,
        "anios_seleccionados": anios_seleccionados,
        "anio_base": anio_base
    })




def parametros_view(request):

    parametros = ParametroSistema.objects.all().order_by("codigo")

    return render(
        request,
        "parametros.html",
        {
            "parametros": parametros
        }
    )


def parametro_nuevo(request):

    if request.method == "POST":

        codigo = request.POST.get("codigo").strip().upper()
        valor = request.POST.get("valor")
        descripcion = request.POST.get("descripcion")

        ParametroSistema.objects.update_or_create(
            codigo=codigo,
            defaults={
                "valor": valor,
                "descripcion": descripcion
            }
        )

        return redirect("parametros")

    return render(request, "parametro_nuevo.html")



from django.shortcuts import render, redirect, get_object_or_404
from .models import ParametroSistema


# ============================
# LISTAR
# ============================

def parametros_view(request):

    parametros = ParametroSistema.objects.all().order_by("codigo")

    return render(request, "parametros.html", {
        "parametros": parametros
    })


# ============================
# NUEVO
# ============================

def parametro_nuevo_view(request):

    if request.method == "POST":

        codigo = request.POST.get("codigo").strip()
        valor = request.POST.get("valor").strip()
        descripcion = request.POST.get("descripcion").strip()

        ParametroSistema.objects.create(
            codigo=codigo,
            valor=valor,
            descripcion=descripcion
        )

        return redirect("parametros")

    return render(request, "parametro_form.html", {
        "modo": "nuevo"
    })


# ============================
# EDITAR
# ============================

def parametro_editar_view(request, id):

    parametro = get_object_or_404(ParametroSistema, id=id)

    if request.method == "POST":

        parametro.valor = request.POST.get("valor").strip()
        parametro.descripcion = request.POST.get("descripcion").strip()

        parametro.save()

        return redirect("parametros")

    return render(request, "parametro_form.html", {
        "modo": "editar",
        "parametro": parametro
    })


# ============================
# ELIMINAR
# ============================

def parametro_eliminar_view(request, id):

    parametro = get_object_or_404(ParametroSistema, id=id)

    parametro.delete()

    return redirect("parametros")







def graficos22(request):

    import json
    from django.db import connection
    from django.shortcuts import render

    # ===============================
    # Parámetros seguros
    # ===============================

    try:
        top_n = int(request.GET.get("top") or 5)
    except:
        top_n = 5

    try:
        tope = float(request.GET.get("tope") or 100)
    except:
        tope = 100.0


    # ===============================
    # QUERY
    # ===============================

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                c.periodo_anio,
                ((c.periodo_mes - 1) / 3 + 1)::int AS trimestre,
                a.nombre,
                COALESCE(a.color, '#3366cc') AS color,
                SUM((c.neto + c.no_gravado + c.exento) / d.valor) AS total_usd

            FROM comprobantes_comisiones c

            JOIN aseguradoras a ON a.id = c.aseguradora_id

            JOIN cotizaciones_dolar d
              ON c.periodo_anio = d.periodo_anio
             AND c.periodo_mes = d.periodo_mes

            GROUP BY
                c.periodo_anio,
                trimestre,
                a.nombre,
                a.color

            ORDER BY
                c.periodo_anio,
                trimestre;
        """)

        rows = cursor.fetchall()


    if not rows:

        return render(request, "graficos22.html", {
            "labels": "[]",
            "datasets": "[]",
            "totales": "[]",
            "top_n": top_n,
            "tope": tope,
            "anios_disponibles": [],
            "anios_seleccionados": []
        })


    # ===============================
    # Años disponibles
    # ===============================

    anios_disponibles = sorted(list({row[0] for row in rows}))


    # ===============================
    # Años seleccionados
    # default = últimos 4 años
    # ===============================

    anios_raw = request.GET.getlist("anio")

    if anios_raw:

        anios_seleccionados = []

        for a in anios_raw:
            try:
                anios_seleccionados.append(int(str(a)))
            except:
                pass

    else:

        anios_seleccionados = anios_disponibles[-4:]


    # ===============================
    # Organizar datos
    # ===============================

    data = {}
    color_map = {}

    for anio, trimestre, nombre, color, total in rows:

        if anio not in anios_seleccionados:
            continue

        periodo = f"{anio}-T{trimestre}"

        if periodo not in data:
            data[periodo] = {}

        data[periodo][nombre] = float(total)
        color_map[nombre] = color


    periodos = sorted(data.keys())


    # ===============================
    # Totales reales
    # ===============================

    totales_periodo = []

    for periodo in periodos:
        totales_periodo.append(sum(data.get(periodo, {}).values()))


    # ===============================
    # Datasets por posición
    # ===============================

    datasets = []

    for pos in range(top_n):

        datasets.append({
            "label": f"pos{pos}",
            "data": [],
            "backgroundColor": [],
            "labels": [],
            "stack": "stack1"
        })


    for periodo in periodos:

        trimestre_data = data.get(periodo, {})
        total_trimestre = sum(trimestre_data.values())

        participaciones = []

        for aseg, valor in trimestre_data.items():

            pct = (valor / total_trimestre) * 100 if total_trimestre else 0

            if pct <= tope:
                participaciones.append((aseg, valor, pct))

        participaciones.sort(key=lambda x: x[1], reverse=True)

        seleccionadas = participaciones[:top_n]


        for pos in range(top_n):

            if pos < len(seleccionadas):

                aseg, valor, pct = seleccionadas[pos]

                datasets[pos]["data"].append(valor)
                datasets[pos]["backgroundColor"].append(
                    color_map.get(aseg, "#3366cc")
                )
                datasets[pos]["labels"].append(aseg)

            else:

                datasets[pos]["data"].append(0)
                datasets[pos]["backgroundColor"].append("rgba(0,0,0,0)")
                datasets[pos]["labels"].append("")


    # ===============================
    # Render FINAL
    # ===============================

    return render(request, "graficos22.html", {

        "labels": json.dumps(periodos),
        "datasets": json.dumps(datasets),
        "totales": json.dumps(totales_periodo),

        "top_n": top_n,
        "tope": tope,

        "anios_disponibles": anios_disponibles,
        "anios_seleccionados": anios_seleccionados

    })




from django.shortcuts import render
from django.http import JsonResponse
import requests


def mackinlays(request):
    return render(request, "mackinlays/index.html")


def cafci_mm(request):
    url = "https://estadisticas.cafci.org.ar/v2/fondos-mercado-de-dinero.json"

    r = requests.get(url, timeout=30)

    return JsonResponse(r.json(), safe=False)

