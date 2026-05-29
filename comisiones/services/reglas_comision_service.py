import pandas as pd
import unicodedata
from ..models import ReglaComision, Aseguradoras
from .comisiones_service import (
    COLUMNAS_EQUIVALENTES,
    normalizar_texto,
    detectar_columnas
)


def normalizar(texto):
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto


def importar_reglas_comision_excel(archivo, aseguradora_id):

    aseguradora = Aseguradoras.objects.get(id=aseguradora_id)

    # borrar reglas existentes
    ReglaComision.objects.filter(
        aseguradora_id=aseguradora_id
    ).delete()


    # Busco la linea que está el titulo en el archivo de comisiones de la aseguradora 
    # palabras clave (solo lo importante)

    df_temp = pd.read_excel(archivo, header=None)

    fila_header = None

    # 🔥 usar equivalencias existentes
    claves_cliente = [normalizar_texto(x) for x in COLUMNAS_EQUIVALENTES["cliente"]]
    claves_poliza = [normalizar_texto(x) for x in COLUMNAS_EQUIVALENTES["poliza"]]

    for i, fila in df_temp.iterrows():

        textos = [normalizar_texto(x) for x in fila.values]

        tiene_cliente = any(
            any(clave in celda for clave in claves_cliente)
            for celda in textos
        )

        tiene_poliza = any(
            any(clave in celda for clave in claves_poliza)
            for celda in textos
        )

        # 👉 condición mínima REAL
        if tiene_cliente and tiene_poliza:
            fila_header = i
            break

    # fallback
    if fila_header is None:
        fila_header = 0

    archivo.seek(0)
    df = pd.read_excel(archivo, header=fila_header)    

    df.columns = [normalizar(c) for c in df.columns]
    columnas_detectadas = detectar_columnas(df.columns)
    print("COLUMNAS DETECTADAS:", columnas_detectadas)

    registros = 0
    errores = 0

    for i, row in df.iterrows():

        try:

            # ------------------------
            # ASEGURADORA
            # ------------------------

            nombre_aseg = str(row.get("aseguradora")).strip()

            if nombre_aseg == "" or nombre_aseg.lower() == "nan":
                continue

            aseguradora = Aseguradoras.objects.filter(
                nombre__iexact=nombre_aseg
            ).first()

            if not aseguradora:
                errores += 1
                continue


            # ------------------------
            # PRODUCTO
            # ------------------------

            producto = None
            if "ramo" in columnas_detectadas:
                producto = str(row[columnas_detectadas["ramo"]]).strip().upper()

            if producto == "" or producto.lower() == "nan":
                producto = None

                
            # ------------------------
            # NIVEL
            # ------------------------
            nivel = None
            if "nivel" in columnas_detectadas:
                nivel = row[columnas_detectadas["nivel"]]

            try:
                nivel = int(float(nivel))
            except:
                errores += 1
                continue

            # ------------------------
            # AÑO POLIZA
            # ------------------------

            anio = row.get("anio_poliza")

            if pd.isna(anio) or str(anio).strip() == "":
                anio_poliza = None
            else:
                try:
                    anio_poliza = int(float(anio))
                except:
                    anio_poliza = None


            # ------------------------
            # MONEDA
            # ------------------------

            moneda = None
            if "moneda" in columnas_detectadas:
                moneda = str(row[columnas_detectadas["moneda"]]).strip().upper()

            if moneda in ["U$S", "USD"]:
                moneda = "U$S"
            elif moneda in ["$", "ARS"]:
                moneda = "$"
            else:
                moneda = None
                

            # ------------------------
            # RANGO
            # ------------------------

            rango = row.get("rango")

            if pd.isna(rango):
                rango = None
            else:
                rango = str(rango).strip().upper()


            # ------------------------
            # TOPE
            # ------------------------

            tope = row.get("tope")

            if pd.isna(tope) or str(tope).strip() == "":
                tope = None
            else:
                try:
                    tope = float(
                        str(tope)
                        .replace("U$S", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )
                except:
                    tope = None


            # ------------------------
            # PORCENTAJE
            # ------------------------

            if "porcentaje" not in columnas_detectadas:
                raise Exception("No se encontró columna porcentaje")

            porcentaje = row[columnas_detectadas["porcentaje"]]

            if pd.isna(porcentaje):
                errores += 1
                continue

            try:
                porcentaje = float(
                    str(porcentaje)
                    .replace("%", "")
                    .replace(",", ".")
                )
            except:
                errores += 1
                continue

            # ------------------------
            # BASE COMISION
            # ------------------------

            base = None
            if "base_comision" in columnas_detectadas:
                base = str(row[columnas_detectadas["base_comision"]]).strip().upper()

            if base in ["PRIMA"]:
                base_comision = "Prima"
            elif base in ["COMISION", "COMISIÓN"]:
                base_comision = "Comision"
            else:
                base_comision = "Prima"
                
                


            # ------------------------
            # GUARDAR
            # ------------------------

            ReglaComision.objects.update_or_create(

                aseguradora=aseguradora,
                producto=producto,
                nivel=nivel,
                anio_poliza=anio_poliza,
                moneda=moneda,
                rango=rango,
                tope=tope,

                defaults={
                    "porcentaje": porcentaje,
                    "base_comision": base_comision   # 🔥 NUEVO                    
                }

            )

            registros += 1

        except:
            errores += 1


    return f"{registros} reglas importadas - {errores} errores"