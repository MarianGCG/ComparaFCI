import pandas as pd
import re
from django.db.models import Q
from ..models import (
    Aseguradoras,
    ComprobantesComisiones,
    CobranzasComisiones
)


def limpiar_cuit(valor):
    if pd.isna(valor):
        return None
    return str(valor).replace("-", "").replace(".0", "").strip()


def limpiar_importe(valor):
    if pd.isna(valor):
        return 0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if texto == "":
        return 0

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", "")

    try:
        return float(texto)
    except:
        return 0


def importar_cobranzas_excel(archivo):

    # ===================================
    # 🔥 BORRAR COBRANZAS DEL PERIODO
    # ===================================

    nombre_archivo = archivo.name

    match = re.match(r"(\d{4})-(\d{2})", nombre_archivo)

    if match:

        anio = int(match.group(1))
        mes = int(match.group(2))

        CobranzasComisiones.objects.filter(
            comprobante__periodo_anio=anio,
            comprobante__periodo_mes=mes
        ).delete()


    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    insertadas = 0
    omitidas = 0
    no_encontradas = 0

    for _, row in df.iterrows():

        cuit = limpiar_cuit(row.get("cuit"))
        fecha = row.get("fecha_comprobante")
        tipo_comprobante = str(row.get("tipo_comprobante", "")).strip()
        tipo_factura = str(row.get("tipo_factura", "")).strip()
        numero = str(row.get("numero_comprobante", "")).replace(".0", "").strip()
        moneda = str(row.get("moneda", "$")).strip()
        importe = limpiar_importe(row.get("monto_pago"))

        if not cuit or not fecha or not numero:
            omitidas += 1
            continue

        fecha = pd.to_datetime(fecha).date()

        # 🔎 Buscar comprobante
        comprobante = ComprobantesComisiones.objects.filter(
            aseguradora__cuit=cuit,
            tipo_comprobante=tipo_comprobante,
            tipo_factura=tipo_factura,
            numero_comprobante=numero
        ).first()

        if not comprobante:
            no_encontradas += 1
            continue

        # 🔁 No duplicar (clave completa)
        existe = CobranzasComisiones.objects.filter(
            comprobante=comprobante,
            fecha_cobro=fecha,
            moneda=moneda,
            importe=importe
        ).exists()

        if existe:
            omitidas += 1
            continue

        # ➕ Crear cobranza
        CobranzasComisiones.objects.create(
            comprobante=comprobante,
            fecha_cobro=fecha,
            moneda=moneda,
            importe=importe
        )

        insertadas += 1

    return {
        "insertadas": insertadas,
        "omitidas": omitidas,
        "no_encontradas": no_encontradas
    }