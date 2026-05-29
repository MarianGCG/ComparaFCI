import pandas as pd
import unicodedata

from ..models import LiquidacionAseguradora
from ..models import ImportacionComisiones,  ReglaComision
import io
import re
from datetime import date
import calendar

def obtener_fecha_desde_nombre_archivo(nombre_archivo):

    try:
        texto = nombre_archivo.upper()

        # AAAAMM + Q (0Q,1Q,2Q)
        match = re.search(r"(20\d{2})(\d{2}).*?([012])Q", texto)

        if not match:
            print("❌ No se pudo parsear:", nombre_archivo)
            return None

        anio = int(match.group(1))
        mes = int(match.group(2))
        q = int(match.group(3))

        # 👇 TU REGLA
        if q == 1:
            dia = 15
        else:
            dia = calendar.monthrange(anio, mes)[1]

        fecha = date(anio, mes, dia)

        print("✔ FECHA OK:", fecha, "Q:", q)

        return fecha

    except Exception as e:
        print("ERROR:", nombre_archivo, e)
        return None
    

# ==========================================
# NORMALIZAR TEXTO
# ==========================================


def normalizar_texto(texto):

    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace("\xa0", " ")   # 👈 CLAVE
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")

    texto = " ".join(texto.split())      # 👈 limpia espacios dobles

    texto = texto.lower().strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")

    return texto



# ==========================================
# LIMPIAR NUMEROS (1.234,56 → 1234.56)
# ==========================================
import math

def limpiar_numero(valor):

    if valor is None:
        return None

    # 🔥 AGREGAR ESTO
    if isinstance(valor, float) and math.isnan(valor):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return None

    texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except:
        return None
    


# ====

def limpiar_fecha(valor):

    if valor is None:
        return None

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return None

    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except:
        return None



import re

# ====
def obtener_fecha_liquidacion(nombre_archivo):

    texto = str(nombre_archivo)

    match = re.search(r"(20\d{2})(\d{2})_?([12])Q", texto)
    if not match:
        return None, None

    anio = int(match.group(1))
    mes = int(match.group(2))
    quincena = match.group(3)   # ahora devuelve "1" o "2"

    if quincena == "1":
        fecha = date(anio, mes, 15)
    else:
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        fecha = date(anio, mes, ultimo_dia)

    return fecha, quincena



# ==========================================
# DETECTAR COLUMNAS
# ==========================================

COLUMNAS_EQUIVALENTES = {

    "cliente": [
        "cliente", 
        "tomador", 
        "Contratante", 
        "Apellido y Nombre del Cliente", 
        "ASEGURADO",
        "Asegurado",
        "Detalle"
    ],

    "cuit": [
        "cuit",
        "dni/cuit",
        "documento",
        "documento del tomador"
    ],

    "ramo": [
        "ramo", 
        "Línea de Negocio",
        "SECCION", 
        "Sección",
        "producto",
        "Sc"        
    ],

    "poliza": [
        "poliza",
        "póliza",
        "n de poliza",
        "numero de poliza",
        "N° DE PÓLIZA",
        "Nro. Póliza",
        "Número de Póliza",
        "Nro Poliza"
    ],

    "premio": [
        "premio",
        "premio en $"
    ],

    "prima": [
        "prima",
        "prima tecnica",
        "prima de tarifa",
        "PrimaTecnica",
        "Prima Técnica"
    ],

    "porcentaje": [
        "% comision",
        "% comisión",
        "porcentaje", 
        "% Prima"
    ],

    "comision": [
        "comision",
        "comision bruta",
        "comision neta",
        "comisión",
        "Comisiones devengadas",
        "Comisión Total" ,
        "ComisiónPesos",
        "Comisión Pesos",
        "ComisionBruta"
    ],

    "comision_adelantada": [
        "comision adelanto",
        "comision adelantada"
    ],


    "descuento_adelanto": [
        "descuento adelanto",
        "desc adelanto"
    ],

    "endoso": [
        "endoso",
        "nro endoso",
        "Número Certificado"
    ],


    "moneda": [
        "moneda" ,
        "Mda"
         
    ],

    "meses_adelanto": [
        "meses adelanto",
        "meses de adelanto",
        "mes adelanto"
    ],

    "cotizacion_dolar": [
        "cot usd",
        "cotizacion dolar",
        "cotización dólar",
        "tipo de cambio"  ,
        "moneda_valor"
    ],

    "fecha_pago": [
        "fecha de cobranza",
        "fecha cobranza",
        "fecha pago",
        "FECHACOBRO"
    ],

}

def detectar_columnas(columnas_excel):

    columnas_normalizadas = {
        normalizar_texto(c): c for c in columnas_excel
    }

    resultado = {}

    for campo, alias_list in COLUMNAS_EQUIVALENTES.items():

        for alias in alias_list:

            alias_norm = normalizar_texto(alias)

            for col_norm, col_original in columnas_normalizadas.items():

                if alias_norm == col_norm:   # 🔥 CAMBIO CLAVE
                    resultado[campo] = col_original
                    break

            if campo in resultado:
                break

    return resultado


# ==========================================
# VALIDAR CAMPOS OBLIGATORIOS
# ==========================================

def validar_columnas(columnas_detectadas):

    obligatorias = [
        "cliente",
        "poliza",
        "premio",
        "prima",
        "porcentaje",
        "comision"
    ]

    faltantes = []

    for c in obligatorias:
        if c not in columnas_detectadas:
            faltantes.append(c)

    if faltantes:
        raise Exception(
            f"Faltan columnas obligatorias: {', '.join(faltantes)}"
        )


# ==========================================
# DETECTAR HEADER
# ==========================================
# ==========================================
# DETECTAR HEADER
# ==========================================
def leer_excel_detectando_header(archivo):

    nombre = archivo.name.lower()

    # =========================
    # 🔵 EXCEL
    # =========================
    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):

        df_temp = pd.read_excel(archivo, header=None)

        # 🔍 DETECTAR HEADER SOLO PARA EXCEL
        fila_header = None

        for i, fila in df_temp.iterrows():

            texto = " ".join([normalizar_texto(x) for x in fila.values])

            if (
                "poliza" in texto
                or "cliente" in texto
                or "tomador" in texto
                or "prima" in texto
                or "comision" in texto
            ):
                fila_header = i
                break

        if fila_header is None:
            fila_header = 0

        archivo.seek(0)

        df = pd.read_excel(archivo, header=fila_header)

    # =========================
    # 🟢 CSV / TXT (Zurich)
    # =========================
    elif nombre.endswith(".csv") or nombre.endswith(".txt"):

        contenido = archivo.read().decode("utf-8", errors="ignore")
        archivo.seek(0)

        # 🔥 HEADER DIRECTO (fila 0)
        df = pd.read_csv(
            io.StringIO(contenido),
            header=0,
            sep=r"\s+",
            engine="python"
        )

    else:
        raise Exception(f"Formato no soportado: {nombre}")

    return df





# ==========================================
# IMPORTADOR PRINCIPAL
# ==========================================

def importar_comisiones_excel(archivo, aseguradora_id):

    nombre_archivo = archivo.name

    # 👉 obtener fecha y quincena desde nombre
    fecha_liq = obtener_fecha_desde_nombre_archivo(nombre_archivo)

    try:
        partes = nombre_archivo.split("_")
        q = partes[2].replace("Q", "")
    except:
        q = None

    # --------------------------------------
    # REEMPLAZAR SI YA EXISTE
    # --------------------------------------

    ImportacionComisiones.objects.filter(
        nombre_archivo=nombre_archivo
    ).delete()

    # --------------------------------------


    df_raw = pd.read_excel(archivo, header=None)

    fila_header = detectar_header(df_raw)

    archivo.seek(0)

    df = pd.read_excel(archivo, header=fila_header)

    df.columns = [normalizar_texto(c) for c in df.columns]

    columnas = detectar_columnas(df.columns)

    # 🔥 SI NO VIENE PORCENTAJE → CALCULARLO
    if "porcentaje" not in columnas:

        if "prima" in columnas and "comision" in columnas:

            df["porcentaje"] = (
                df[columnas["comision"]] /
                df[columnas["prima"]]
            ) * 100

            columnas["porcentaje"] = "porcentaje"

    # ✅ recién ahora validar
    validar_columnas(columnas)



    # --------------------------------------
    # CREAR IMPORTACION
    # --------------------------------------

    importacion = ImportacionComisiones.objects.create(
        aseguradora_id=aseguradora_id,
        nombre_archivo=nombre_archivo,
    )

    registros = 0
    clientes_unicos = set()
    comision_total = 0

    # ==========================================
    # 🔥 VALIDAR COMISION ADELANTADA (ANTES DE GUARDAR)
    # ==========================================

    errores = []

    for i, row in df.iterrows():

        valor_meses = limpiar_numero(
            row[columnas["meses_adelanto"]]
        ) if "meses_adelanto" in columnas else None

        meses = int(valor_meses) if valor_meses is not None else 0


        prima = limpiar_numero(row[columnas["prima"]]) or 0

        porcentaje = limpiar_numero(row[columnas["porcentaje"]])

        # 🔥 NO dividir más
        porcentaje = limpiar_numero(row[columnas["porcentaje"]])


            


        comision_adelantada = (
            limpiar_numero(row[columnas["comision_adelantada"]])
            if "comision_adelantada" in columnas
            else 0
        ) or 0

        if (
            comision_adelantada > 0
            and meses > 0
            and porcentaje > 0
            and prima > 0
        ):
            
            calculado = meses * (porcentaje / 100) * prima
            if abs(calculado - comision_adelantada) > 0.01:
                errores.append(
                    f"Fila {i+1}: {calculado:.2f} ≠ {comision_adelantada:.2f}"
                )

    # 👉 SI HAY ERRORES → CORTAR TODO
    if errores:
        raise Exception(
            "Cálculo Control Comisión Adelantada incorrecto\n\n"
            + "\n".join(errores[:10])
        )





    for _, row in df.iterrows():

        cliente = row[columnas["cliente"]]

        cuit = None
        if "cuit" in columnas:
            cuit = row[columnas["cuit"]]
            cuit = str(cuit).replace(".0", "").strip() if cuit else None
            

        if pd.isna(cliente):
            continue

        cliente = str(cliente).strip()
        cuit = str(cuit).replace(".0", "").strip()

        if cliente == "" or cuit == "":
            continue

        premio = limpiar_numero(row[columnas["premio"]])
        prima = limpiar_numero(row[columnas["prima"]])
        porcentaje = limpiar_numero(row[columnas["porcentaje"]])


        meses_adelanto = None

        valor_meses = limpiar_numero(
            row[columnas.get("meses_adelanto")]
        ) if columnas.get("meses_adelanto") else None

        meses_adelanto = int(valor_meses) if valor_meses is not None else None


                
        comision = limpiar_numero(row[columnas["comision"]])


        # ==========================
        # 🔥 COMISION AGENTE
        # ==========================

        comision_adelantada = limpiar_numero(
            row[columnas.get("comision_adelantada")]
        ) if columnas.get("comision_adelantada") else None

        if comision_adelantada and comision_adelantada > 0:
            comision_agente_final = comision_adelantada
        else:
            comision_agente_final = comision

        endoso_val = None

        if "endoso" in columnas:
            valor_endoso = limpiar_numero(row[columnas["endoso"]])

            if valor_endoso is not None:
                endoso_val = int(valor_endoso)


        if "moneda" in columnas:
            moneda_valor = str(row[columnas["moneda"]]).strip().upper()

            if moneda_valor in ["USD", "U$S"]:
                moneda_valor = "U$S"
            else:
                moneda_valor = "$"

        else:
            moneda_valor = "$"

            


        LiquidacionAseguradora.objects.create(

            importacion=importacion,
            aseguradora_id=aseguradora_id,

            cliente=cliente,
            cuit=cuit,

            ramo=str(row[columnas["ramo"]])[:20] if "ramo" in columnas else None,
            poliza=str(row[columnas["poliza"]]).replace(".0", ""),

            premio=premio,
            prima=prima,
            porcentaje=porcentaje,


                

            cotizacion_dolar=limpiar_numero(row[columnas["cotizacion_dolar"]]) if "cotizacion_dolar" in columnas else None,

            fecha_liquidacion=fecha_liq,
            quincena=q,

            fecha_pago=limpiar_fecha(row[columnas["fecha_pago"]]) if "fecha_pago" in columnas else None,

            moneda= moneda_valor,   # ✅ acá sí

            comision_agente=comision_agente_final,    
                        

            meses_adelanto=meses_adelanto,
            comision_adelantada=comision_adelantada,

            descuento_adelanto=limpiar_numero(
                row[columnas["descuento_adelanto"]]
            ) if "descuento_adelanto" in columnas else None,

            endoso=endoso_val,


            archivo_origen=nombre_archivo
        )

        registros += 1

        clientes_unicos.add(cuit)

        if comision:
            comision_total += comision

    # --------------------------------------
    # GUARDAR RESUMEN
    # --------------------------------------

    importacion.registros = registros
    importacion.cantidad_clientes = len(clientes_unicos)
    importacion.comision_total = comision_total

    importacion.save()

    return f"{registros} registros importados correctamente"



def buscar_porcentaje_comision(aseguradora_id, producto, nivel, anio_poliza, moneda):

    regla = ReglaComision.objects.filter(
        aseguradora_id=aseguradora_id,
        producto__iexact=producto,
        nivel=nivel,
        anio_poliza=anio_poliza
    ).first()

    if regla:
        return regla.porcentaje

    return None


import pdfplumber
import pandas as pd
import re

def procesar_pdf_atm(archivo):

    filas = []

    with pdfplumber.open(archivo) as pdf:
        for page in pdf.pages:

            texto = page.extract_text()

            if not texto:
                continue

            lineas = texto.split("\n")

            for linea in lineas:

                if re.match(r"^\d+\s+\d+\s+\d+", linea):

                    partes = linea.split()

                    try:
                        ramo = partes[0]
                        poliza = partes[1]
                        endoso = partes[2]

                        cliente = " ".join(partes[3:-6])

                        premio = limpiar_numero(partes[-5])
                        prima = limpiar_numero(partes[-4])
                        comision = limpiar_numero(partes[-1])

                        porcentaje = (comision / prima * 100) if prima else 0

                        filas.append({
                            "cliente": cliente,
                            "poliza": poliza,
                            "endoso": endoso,
                            "ramo": ramo,
                            "premio": premio,
                            "prima": prima,
                            "porcentaje": porcentaje,
                            "comision": comision,
                            "moneda": "$"
                        })

                    except Exception as e:
                        print("Error línea:", linea, e)

    return pd.DataFrame(filas)

def importar_desde_dataframe(df, nombre_archivo, aseguradora_id):

    # simular archivo excel
    from io import BytesIO

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    output.name = nombre_archivo.replace(".pdf", ".xlsx")

    return importar_comisiones_excel(output, aseguradora_id)

def detectar_header(df_raw):

    claves_cliente = [normalizar_texto(x) for x in COLUMNAS_EQUIVALENTES["cliente"]]
    claves_poliza = [normalizar_texto(x) for x in COLUMNAS_EQUIVALENTES["poliza"]]

    for i, fila in df_raw.iterrows():

        textos = [normalizar_texto(x) for x in fila.values]

        tiene_cliente = any(
            any(clave in celda for clave in claves_cliente)
            for celda in textos
        )

        tiene_poliza = any(
            any(clave in celda for clave in claves_poliza)
            for celda in textos
        )

        # 👉 condición mínima (simple como querés)
        if tiene_cliente or tiene_poliza:
            return i

    return 0