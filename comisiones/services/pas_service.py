import pandas as pd
import unicodedata

from ..models import PAS


def normalizar(texto):

    if not texto:
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii","ignore").decode("ascii")

    return texto


def limpiar_cuit(valor):

    if not valor:
        return None

    texto = str(valor).strip()

    texto = texto.replace(".0","")

    return texto

def importar_pas_excel(archivo):

    df = pd.read_excel(archivo)

    df.columns = df.columns.str.strip().str.lower()
    df.columns = [normalizar(c) for c in df.columns]

    columnas = {
        "codigo": None,
        "nombre": None,
        "cuit": None,
        "cvu": None
    }

    for c in df.columns:

        c_lower = c.lower()

        if "codigo" in c_lower:
            columnas["codigo"] = c

        elif "nombre" in c_lower:
            columnas["nombre"] = c

        elif "cuit" in c_lower:
            columnas["cuit"] = c

        elif "cvu" in c_lower:
            columnas["cvu"] = c


            


    # validar columnas obligatorias
    faltantes = [k for k,v in columnas.items() if v is None and k in ["codigo","nombre"]]

    if faltantes:
        return "Faltan columnas obligatorias: " + ", ".join(faltantes)


    registros = 0

    for _, row in df.iterrows():

        codigo = row[columnas["codigo"]]
        nombre = row[columnas["nombre"]]

        if pd.isna(codigo) or pd.isna(nombre):
            continue

        
        codigo = str(codigo).replace(".0","").strip()
        nombre = str(nombre).strip()

        cuit = limpiar_cuit(row[columnas["cuit"]]) if columnas["cuit"] else None
        cvu = row[columnas["cvu"]] if columnas["cvu"] else None

        PAS.objects.update_or_create(
            codigo_pas=codigo,
            defaults={
                "nombre": nombre,
                "cuit": cuit,
                "cvu": cvu
            }
        )

        registros += 1

    return f"{registros} PAS importados"