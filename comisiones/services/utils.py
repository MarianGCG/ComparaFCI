import pandas as pd

def limpiar_cuit(valor):
    if pd.isna(valor):
        return None

    cuit = str(valor).replace("-", "").replace(".0", "").strip()
    return cuit if cuit else None