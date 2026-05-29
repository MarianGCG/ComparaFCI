import pandas as pd
from ..models import CotizacionesDolar

from decimal import Decimal



def limpiar_importe(valor):
    if valor is None:
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
    



def importar_cotizaciones_excel(archivo):

    import pandas as pd
    from decimal import Decimal

    # 🔹 CLAVE PARA RENDER
    archivo.seek(0)

    df = pd.read_excel(archivo)

    # limpiar nombres columnas
    df.columns = df.columns.astype(str).str.strip().str.lower()

    insertadas = 0
    actualizadas = 0
    omitidas = 0

    for _, row in df.iterrows():

        anio = row.get("periodo_anio")
        mes = row.get("periodo_mes")
        valor = row.get("valor")

        if pd.isna(anio) or pd.isna(mes):
            omitidas += 1
            continue

        try:
            anio = int(anio)
            mes = int(mes)
        except:
            omitidas += 1
            continue

        if pd.isna(valor):
            valor = None
        else:
            valor = Decimal(str(valor))

        obj, created = CotizacionesDolar.objects.update_or_create(
            periodo_anio=anio,
            periodo_mes=mes,
            defaults={"valor": valor}
        )

        if created:
            insertadas += 1
        else:
            actualizadas += 1

    return {
        "insertadas": insertadas,
        "actualizadas": actualizadas,
        "omitidas": omitidas
    }
