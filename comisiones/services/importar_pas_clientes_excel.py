import pandas as pd
from ..models import PASCliente, PAS, Aseguradoras

def importar_pas_clientes_excel(archivo):

    df = pd.read_excel(archivo)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # 🔥 BORRAR TODO
    PASCliente.objects.all().delete()

    registros = 0
    errores = 0

    for _, row in df.iterrows():

        try:
            # =========================
            # PAS
            # =========================
            pas_codigo = str(row.get("pas")).strip()

            pas = PAS.objects.filter(codigo_pas=pas_codigo).first()
            if not pas:
                errores += 1
                continue

            # =========================
            # ASEGURADORA
            # =========================
            nombre_aseg = str(row.get("aseguradora")).strip()

            aseguradora = None
            if nombre_aseg and nombre_aseg.lower() != "nan":
                aseguradora = Aseguradoras.objects.filter(
                    nombre__iexact=nombre_aseg
                ).first()

            # =========================
            # CLIENTE
            # =========================
            cliente = str(row.get("cliente")).strip()
            if not cliente:
                errores += 1
                continue

            clave1 = str(row.get("clave1")).strip() if row.get("clave1") else None
            clave2 = str(row.get("clave2")).strip() if row.get("clave2") else None
            cuit = str(row.get("cuit")).strip() if row.get("cuit") else None

            # =========================
            # GUARDAR
            # =========================
            PASCliente.objects.create(
                pas=pas,
                aseguradora=aseguradora,
                cliente=cliente,
                cliente_clave1=clave1,
                cliente_clave2=clave2,
                cuit=cuit
            )

            registros += 1

        except:
            errores += 1

    return f"{registros} clientes importados - {errores} errores"