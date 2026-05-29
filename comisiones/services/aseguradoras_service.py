import pandas as pd
from ..models import Aseguradoras
from .utils import limpiar_cuit

def importar_aseguradoras_excel(archivo):

    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    insertadas = 0
    actualizadas = 0
    omitidas = 0

    for _, row in df.iterrows():

        nombre = row.get("nombre")
        cuit = row.get("cuit")
        tipo_factura = row.get("tipo_factura")
        email = row.get("email")
        codigo_interno = row.get("codigo_interno")
        razon_social_afip = row.get("razon_social_afip")
        grupo = row.get("grupo")

        # ---------------------------
        # VALIDACIONES BÁSICAS
        # ---------------------------
        if pd.isna(cuit):
            omitidas += 1
            continue

        # ---------------------------
        # NORMALIZAR CUIT
        # ---------------------------
        cuit = str(cuit).replace("-", "").replace(".0", "").strip()

        # ---------------------------
        # NORMALIZAR CÓDIGO INTERNO
        # ---------------------------
        if pd.isna(codigo_interno):
            codigo_interno = None
        else:
            codigo_interno = str(codigo_interno).strip()
            if codigo_interno == "" or codigo_interno.lower() == "none":
                codigo_interno = None
            else:
                codigo_interno = codigo_interno.replace(".0", "")

        # ---------------------------
        # NORMALIZAR OTROS CAMPOS
        # ---------------------------
        nombre = None if pd.isna(nombre) else str(nombre).strip()
        tipo_factura = None if pd.isna(tipo_factura) else str(tipo_factura).strip()
        email = None if pd.isna(email) else str(email).strip()
        razon_social_afip = None if pd.isna(razon_social_afip) else str(razon_social_afip).strip()
        grupo = None if pd.isna(grupo) else str(grupo).strip().upper()
        # ---------------------------
        # BUSCAR EXISTENTE (CUIT + CODIGO)
        # ---------------------------
        aseguradora = Aseguradoras.objects.filter(
            cuit=cuit,
            codigo_interno=codigo_interno
        ).first()

        if aseguradora:
            # ---------------------------
            # ACTUALIZAR
            # ---------------------------
            aseguradora.nombre = nombre
            aseguradora.tipo_factura = tipo_factura
            aseguradora.email = email
            aseguradora.razon_social_afip = razon_social_afip
            aseguradora.grupo = grupo   # ← AGREGAR
            aseguradora.activa = True  # reactivar si estaba inactiva
            aseguradora.save()

            actualizadas += 1

        else:
            # ---------------------------
            # CREAR NUEVA
            # ---------------------------
            Aseguradoras.objects.create(
                nombre=nombre,
                cuit=cuit,
                tipo_factura=tipo_factura,
                email=email,
                codigo_interno=codigo_interno,
                razon_social_afip=razon_social_afip,
                grupo=grupo,   # ← AGREGAR
                activa=True
            )

            insertadas += 1

    return {
        "insertadas": insertadas,
        "actualizadas": actualizadas,
        "omitidas": omitidas
    }