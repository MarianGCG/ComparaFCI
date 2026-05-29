import pandas as pd
from datetime import datetime
from ..models import Aseguradoras, ComprobantesComisiones
from io import BytesIO


def limpiar_cuit(valor):
    if pd.isna(valor):
        return None

    cuit = str(valor).replace("-", "").replace(".0", "").strip()
    return cuit if cuit else None


def limpiar_importe(valor):

    if pd.isna(valor):
        return 0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return 0

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", "")

    try:
        return float(texto)
    except:
        return 0


from io import BytesIO
import pandas as pd
from datetime import datetime
from ..models import Aseguradoras, ComprobantesComisiones

def leer_excel_arca(archivo):
    import pandas as pd

    archivo.seek(0)
    df_raw = pd.read_excel(archivo, header=None)

    fila_header = None

    for i in range(min(15, len(df_raw))):
        fila_texto = " ".join(df_raw.iloc[i].astype(str)).lower()

        if (
            "fecha" in fila_texto
            and ("tipo" in fila_texto or "comprobante" in fila_texto)
            and ("número" in fila_texto or "numero" in fila_texto)
        ):
            fila_header = i
            break

    if fila_header is None:
        raise Exception("No se encontró la fila de encabezados")

    archivo.seek(0)
    df = pd.read_excel(archivo, header=fila_header)

    df.columns = df.columns.astype(str).str.strip()

    return df






def importar_comprobantes_arca(archivo):

    import pandas as pd

    # ================================
    # LEER ARCHIVO (compatible local y Render)
    # ================================
    try:
        archivo.seek(0)
        df = leer_excel_arca(archivo)
    except Exception as e:
        return {
            "ooinsertados": 0,
            "actualizados": 0,
            "omitidos": 0,
            "no_encontrados": 0,
            "error": str(e)
        }
    print(df.columns.tolist())
    # limpiar nombres columnas
    df.columns = df.columns.astype(str).str.strip()

    # ================================
    # CONTADORES
    # ================================
    insertados = 0
    actualizados = 0
    omitidos = 0
    no_encontrados = 0

    # ================================
    # RECORRER FILAS
    # ================================
    for _, row in df.iterrows():

        fecha = row.get("Fecha")
        tipo_texto = str(row.get("Tipo", "")).strip()
        numero = str(row.get("Número Desde", "")).replace(".0", "").strip()
        cuit = limpiar_cuit(row.get("Nro. Doc. Receptor"))

        # validar datos mínimos
        if pd.isna(fecha) or not numero or not cuit:
            omitidos += 1
            continue

        # ================================
        # FECHA
        # ================================
        try:
            fecha = pd.to_datetime(fecha, dayfirst=True).date()
        except:
            omitidos += 1
            continue

        # ================================
        # PERIODO = MES ANTERIOR
        # ================================
        periodo_mes = fecha.month - 1
        periodo_anio = fecha.year

        if periodo_mes == 0:
            periodo_mes = 12
            periodo_anio -= 1

        # ================================
        # IMPORTES
        # ================================
        neto = limpiar_importe(row.get("Neto Gravado Total"))
        no_gravado = limpiar_importe(row.get("Neto No Gravado"))
        exento = limpiar_importe(row.get("Op. Exentas"))
        iva = limpiar_importe(row.get("Total IVA"))
        total = limpiar_importe(row.get("Imp. Total"))

        # ================================
        # TIPO COMPROBANTE
        # ================================
        if "nota de crédito" in tipo_texto.lower():
            tipo_comprobante = "NOTA_CREDITO"
            neto = -neto
            no_gravado = -no_gravado
            exento = -exento
            iva = -iva
            total = -total
        else:
            tipo_comprobante = "FACTURA"

        # ================================
        # TIPO FACTURA
        # ================================
        if tipo_texto.endswith("A"):
            tipo_factura = "A"
        elif tipo_texto.endswith("B"):
            tipo_factura = "B"
        elif tipo_texto.endswith("C"):
            tipo_factura = "C"
        else:
            tipo_factura = "A"

        # ================================
        # BUSCAR ASEGURADORA
        # ================================
        aseguradora = Aseguradoras.objects.filter(cuit=cuit).first()

        if not aseguradora:
            no_encontrados += 1
            continue

        # ================================
        # INSERT / UPDATE
        # ================================
        obj, created = ComprobantesComisiones.objects.update_or_create(
            aseguradora=aseguradora,
            tipo_comprobante=tipo_comprobante,
            tipo_factura=tipo_factura,
            numero_comprobante=numero,
            periodo_anio=periodo_anio,
            periodo_mes=periodo_mes,
            defaults={
                "fecha_comprobante": fecha,
                "moneda": "$",
                "neto": neto,
                "no_gravado": no_gravado,
                "exento": exento,
                "iva": iva,
                "total": total,
            }
        )

        if created:
            insertados += 1
        else:
            actualizados += 1

    # ================================
    # RESULTADO
    # ================================
    return {
        "insertados": insertados,
        "actualizados": actualizados,
        "omitidos": omitidos,
        "no_encontrados": no_encontrados
    }