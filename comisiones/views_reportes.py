from django.shortcuts import render
from django.db.models import Q

from django.http import HttpResponse
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from decimal import InvalidOperation
from .models import (
    LiquidacionAseguradora,
    PAS,
    PASCliente,
    Aseguradoras,
    PASAseguradora
) 

def reporte_comisiones_view(request):


    pas_codigo = request.GET.get("pas")
    ver_grafico = request.GET.get("ver_grafico")    
    solo_con_pas = pas_codigo == "SOLO"
    aseguradora_id = request.GET.get("aseguradora")
    clave1 = request.GET.get("clave1")
    clave2 = request.GET.get("clave2")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    exportar = request.GET.get("exportar")

    datos = LiquidacionAseguradora.objects.select_related("aseguradora")

    # ============================
    # FILTRO PAS (clientes)
    # ============================

    
    if pas_codigo and pas_codigo != "SOLO":
        clientes = PASCliente.objects.filter(
            pas__codigo_pas=pas_codigo
        )

        filtro = Q()

        for c in clientes:

            sub_filtro = Q()

            # 🔥 NUEVO: FILTRO POR ASEGURADORA
            if c.aseguradora_id:
                sub_filtro &= Q(aseguradora_id=c.aseguradora_id)


            if c.aseguradora_id:
                sub_filtro &= Q(aseguradora_id=c.aseguradora_id)
            elif aseguradora_id:
                sub_filtro &= Q(aseguradora_id=aseguradora_id)

                
            if c.cliente_clave1:
                sub_filtro &= Q(cliente__icontains=c.cliente_clave1)

            if c.cliente_clave2:
                sub_filtro &= Q(cliente__icontains=c.cliente_clave2)

            if sub_filtro:
                filtro |= sub_filtro

                
        if filtro:
            datos = datos.filter(filtro)
        else:
            datos = datos.none()

    # ============================
    # OTROS FILTROS
    # ============================

    if aseguradora_id:
        datos = datos.filter(aseguradora_id=aseguradora_id)

    if clave1:
        datos = datos.filter(cliente__icontains=clave1)

    if clave2:
        datos = datos.filter(cliente__icontains=clave2)

    if fecha_desde:
        datos = datos.filter(fecha_liquidacion__gte=fecha_desde)

    if fecha_hasta:
        datos = datos.filter(fecha_liquidacion__lte=fecha_hasta)


    datos = datos.order_by(
        "aseguradora__nombre",
        "cliente", 
        "poliza",
        "endoso" ,              
        "fecha_liquidacion",
        "quincena"
    )


    # ============================
    # PAS seleccionado
    # ============================

    pas_obj = PAS.objects.filter(codigo_pas=pas_codigo).first()
    pas_seleccionado = pas_obj.nombre if pas_obj else ""
    # ============================
    # 🔥 MAPA PAS CLIENTE (UNA VEZ)
    # ============================

    pas_clientes = PASCliente.objects.select_related("pas")

    mapa_pas = []

    for pc in pas_clientes:
        mapa_pas.append({
            "pas_codigo": pc.pas.codigo_pas,
            "nombre": pc.pas.nombre,
            "clave1": normalizar_texto(pc.cliente_clave1),
            "clave2": normalizar_texto(pc.cliente_clave2),
            "aseguradora": pc.aseguradora_id
        })

    # ============================
    # 🔥 FILTRO SOLO PAS
    # ============================

    if solo_con_pas:

        datos_filtrados = []

        for d in datos:

            cliente_norm = normalizar_texto(d.cliente)

            tiene_pas = False

            for m in mapa_pas:

                if m["aseguradora"] and m["aseguradora"] != d.aseguradora_id:
                    continue

                ok = True

                if m["clave1"] and m["clave1"] not in cliente_norm:
                    ok = False

                if m["clave2"] and m["clave2"] not in cliente_norm:
                    ok = False

                if ok:
                    tiene_pas = True
                    break

            if tiene_pas:
                datos_filtrados.append(d)

        datos = datos_filtrados


    filas = []

    for d in datos:

        # 🔹 porcentaje de la liquidación (SIEMPRE)
        porcentaje = d.porcentaje
        comision_compania = d.comision_agente

        # 🔹 default
        porcentaje_pas = 0
        comision_pas = 0

        prima_original = d.prima or 0

        # 🔥 NORMALIZAR SIGNO PRIMERO (ANTES DE TODO)

        comision_agente = normalizar_signo(d.comision_agente or 0, d.aseguradora)
        prima = normalizar_signo(d.prima or 0, d.aseguradora)
        comision_adelantada = normalizar_signo(d.comision_adelantada or 0, d.aseguradora)
        descuento_adelanto = normalizar_signo(d.descuento_adelanto or 0, d.aseguradora)



        # ============================
        # BUSCAR % PAS (regla)
        # ============================

        # ============================
        # 🔥 BUSCAR PAS POR FILA
        # ============================

        pas_para_fila = None
        pas_nombre = ""
        cliente_norm = normalizar_texto(d.cliente)

        for m in mapa_pas:

            if m["aseguradora"] and m["aseguradora"] != d.aseguradora_id:
                continue

            ok = True

            if m["clave1"] and m["clave1"] not in cliente_norm:
                ok = False

            if m["clave2"] and m["clave2"] not in cliente_norm:
                ok = False

            if ok:
                pas_para_fila = m["pas_codigo"]
                pas_nombre = m["nombre"]
                break

        if pas_codigo and pas_codigo != "SOLO":
            pas_usar = pas_codigo
        else:
            pas_usar = pas_para_fila

            
        
        if pas_usar:

            pa = PASAseguradora.objects.filter(
                pas_id=pas_usar,
                aseguradora_id=d.aseguradora_id
            ).first()

            
            if pa:

                from comisiones.models import ReglaComision

   
                moneda = normalizar_texto(d.moneda)
                ramo = normalizar_texto(d.ramo)


                regla = None

                # 1️⃣ intento: match específico por ramo
                if ramo:

                    reglas = ReglaComision.objects.filter(
                        aseguradora_id=d.aseguradora_id,
                        moneda__iexact=moneda,
                        nivel=pa.nivel
                    )

                    regla = None

                    for r in reglas:
                        if normalizar_texto(r.producto) == ramo:
                            regla = r
                            break

                        


                # 2️⃣ fallback: producto vacío (regla general)
                if not regla:
                    regla = ReglaComision.objects.filter(
                        aseguradora_id=d.aseguradora_id,
                        nivel=pa.nivel,
                        moneda__iexact=moneda
                    ).filter(
                        Q(producto__isnull=True) | Q(producto="")
                    ).first()



                if regla:
                    porcentaje_pas = regla.porcentaje

                    
                    if Decimal(comision_adelantada or 0) > 0:
                        base = comision_adelantada   # 🔥 YA TOTAL

                        if porcentaje not in [None, 0, "0"]:
                           comision_pas = base * porcentaje_pas / porcentaje
                        else:
                           comision_pas = 0
                        
                    else:
                        if regla.base_comision == "Comision":
                            base = comision_agente or 0
                            comision_pas = base * porcentaje_pas / 100
                        else:
                            base = prima or 0
                            comision_pas = base * porcentaje_pas / 100
                        
                    

                if d.moneda == "U$S" and d.cotizacion_dolar:
                    comision_pas *= d.cotizacion_dolar



        # ============================
        # 🔥 NEGATIVO (nota crédito)
        # ============================

        valores = [
            d.comision_agente,
            d.descuento_adelanto,
            d.comision_adelantada
        ]




        if d.moneda == "U$S" and d.cotizacion_dolar:
            comision_agente *= d.cotizacion_dolar
            prima *= d.cotizacion_dolar
            comision_adelantada *= d.cotizacion_dolar
            descuento_adelanto *= d.cotizacion_dolar



        # 🔥 SI HAY DESCUENTO → reemplaza comisión agente
        if descuento_adelanto != 0:
            comision_agente = descuento_adelanto


      


        if descuento_adelanto != 0 and porcentaje:

            try:
                desc = Decimal(descuento_adelanto or 0)
                porc_pas = Decimal(porcentaje_pas or 0)
                porc = Decimal(porcentaje or 0)

                if porc != 0:
                    comision_pas = porc_pas * desc / porc
                else:
                    comision_pas = Decimal('0')

            except Exception:
                comision_pas = Decimal('0')
                
        
        


        # 🔥 redondeo final único
                
        if descuento_adelanto:
            descuento_adelanto = round(descuento_adelanto, 2)
        else:
            descuento_adelanto = 0
            
    
        # ============================
        # 🔥 COMISION PAS SIN IVA
        # ============================



        if d.aseguradora and d.aseguradora.incluye_iva == "S":
            base = Decimal(comision_pas or 0)
            comision_pas_sin_iva = base / Decimal("1.21")
        else:
            comision_pas_sin_iva = Decimal(comision_pas or 0)




            


        # 🔥 SIN PAS → igualar a agente
        if not pas_para_fila:
            porcentaje_pas = porcentaje or 0
            comision_pas = comision_agente or 0
            comision_pas_sin_iva = comision_agente or 0



        # 🔥 recién acá redondeás
        comision_pas = round(comision_pas, 2)
        comision_pas_sin_iva = round(comision_pas_sin_iva, 2)
        prima = round(prima, 2)
        comision_adelantada = round(comision_adelantada, 2)



        # ============================
        # ARMAR FILA
        # ============================



        try:
            if prima and porcentaje and porcentaje != 0:
                meses = (
                    comision_agente / (prima * (porcentaje / 100))
                )

                meses = round(meses)

            else:
                meses = 0

        except:
            meses = 0
            


        filas.append({
            "fecha": d.fecha_liquidacion,
            "quincena": d.quincena,
            "aseg": d.aseguradora.nombre,
            "cliente": d.cliente,
            "ramo": d.ramo,
            "poliza": d.poliza,
            "endoso": d.endoso,
            "moneda": d.moneda,
            "cotizacion": d.cotizacion_dolar,
            "prima_original": prima_original,
            "meses": meses,
            "prima": prima,
            "porcentaje": porcentaje ,
            "comision_agente": comision_agente,
            "descuento_adelanto": descuento_adelanto,
            "comision_adelantada": comision_adelantada,
            "porcentaje_pas": (porcentaje_pas or 0) ,
            "comision_pas": comision_pas,
            "comision_pas_sin_iva": comision_pas_sin_iva,
            "pas_nombre": pas_nombre
        })

# ============================
# EXPORTAR EXCEL
# ============================

    if exportar == "excel":

        df = pd.DataFrame(filas)

        if request.GET.get("solo_pas") == "1":
            columnas = [
                "fecha", "quincena", "aseg",  "cliente", "ramo",
                "poliza", "endoso", "moneda", "cotizacion",
                "prima_original",
                "meses", "prima",                
                "porcentaje_pas", "comision_pas", "comision_pas_sin_iva"
            ]
        else:
            columnas = [
                "fecha", "quincena", "aseg", "cliente", "ramo",
                "poliza", "endoso", "moneda", "cotizacion",
                "prima_original",
                "meses", "prima",  
                "porcentaje", "comision_agente",
                "descuento_adelanto", "comision_adelantada",
                "porcentaje_pas", "comision_pas", "comision_pas_sin_iva"
            ]

        df = df[columnas]
        
        df["quincena"] = df["quincena"].apply(lambda x: "" if str(x) == "0" else x)
        df = df.rename(columns={
            "fecha": "Fecha",
            "aseg": "Aseguradora",
            "cliente": "Cliente",
            "ramo": "Ramo",
            "poliza": "Poliza",
            "endoso": "Endoso",
            "moneda": "Moneda",
            "cotizacion": "Cotización",
            "prima_original": "Prima U$S",            
            "meses": "Meses",
            "prima": "Prima",
            "porcentaje": "Porcentaje",
            "comision_agente": "Comisión Agente",
            "descuento_adelanto": "Descuento Adelanto",
            "comision_adelantada": "Comisión Adelantada",
            "prima_original": "Prima U$S",
            "porcentaje_pas": "% PAS",
            "comision_pas": "Comisión PAS",
            "comision_pas_sin_iva": "Comisión PAS s/IVA"
        })

        # ============================
        # 🔥 FORZAR NUMÉRICOS (CLAVE)
        # ============================

        columnas_moneda = [
            "Cotización",
            "Prima U$S",
            "Prima",
            "Comisión PAS",
            "Comisión PAS s/IVA"
        ]

        # 👇 SOLO si existen
        for col in [
            "Porcentaje",
            "Comisión Agente",
            "Descuento Adelanto",
            "Comisión Adelantada"
        ]:
            if col in df.columns:
                columnas_moneda.append(col)
                



        columnas_porcentaje = [
            "% PAS"
        ]

        for col in columnas_moneda:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in columnas_porcentaje:
            df[col] = pd.to_numeric(df[col], errors='coerce') 

            


        # 👉 CREAR RESPONSE
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=reporte_comisiones.xlsx'

        # 👉 TODO EL EXCEL ADENTRO
        with pd.ExcelWriter(response, engine='xlsxwriter') as writer:

            # mover tabla hacia abajo
            df.to_excel(writer, index=False, sheet_name='Reporte', startrow=4)
            workbook  = writer.book
            worksheet = writer.sheets['Reporte']
              

            # =========================
            # FORMATO HEADER (AZUL)
            # =========================

            formato_header = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'middle',
                'border': 1,
                'bg_color': '#1F4E78',
                'font_color': 'white'
            })

            for col_num, col_name in enumerate(df.columns):
                worksheet.write(4, col_num, col_name, formato_header)

                

            # ============================
            # CALCULAR TOTALES
            # ============================


            total_bruto =  df["Comisión PAS s/IVA"].sum()
            total_neto = df["Comisión PAS s/IVA"].sum()

            descuento = 0.09
            pago = total_neto * (1 - descuento)

            # ============================
            # POSICIÓN (columna O)
            # ============================
            col_inicio = len(df.columns) - 2
            fila_inicio = len(df) + 8

            # ============================
            # FORMATOS
            # ============================

            # 🎨 Azul sistema
            azul = '#1F4E78'

            formato_titulo_caja = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 2,
                'bg_color': azul,
                'font_color': 'white'
            })

            formato_label = workbook.add_format({
                'border': 2,
                'bold': True
            })

            formato_moneda = workbook.add_format({
                'num_format': '$ #,##0.00',
                'border': 1,
                'align': 'right'
            })

            formato_porcentaje = workbook.add_format({
                'num_format': '0%',
                'border': 2
            })

            # ============================
            # 🧾 TÍTULO CON MERGE
            # ============================

            worksheet.merge_range(
                fila_inicio, col_inicio,
                fila_inicio, col_inicio + 1,
                "Monotributo",
                formato_titulo_caja
            )

            # ============================
            # 📊 CUADRO
            # ============================

            # ==worksheet.write(fila_inicio+1, col_inicio, "Bruto", formato_label)
            # ==worksheet.write(fila_inicio+1, col_inicio+1, total_bruto, formato_moneda)

            # ==worksheet.write(fila_inicio+2, col_inicio, "IVA", formato_label)
            # ==worksheet.write(fila_inicio+2, col_inicio+1, "-", formato_label)

            worksheet.write(fila_inicio+1, col_inicio, "A facturar", formato_label)
            worksheet.write(fila_inicio+1, col_inicio+1, total_neto, formato_moneda)

            worksheet.write(fila_inicio+2, col_inicio, "Desc. (Imp.)", formato_label)
            worksheet.write(fila_inicio+2, col_inicio+1, descuento, formato_porcentaje)

            worksheet.write(fila_inicio+3, col_inicio, "Pago", formato_label)
            worksheet.write(fila_inicio+3, col_inicio+1, pago, formato_moneda)


            # =========================
            # ENCABEZADO
            # =========================
            from datetime import date


            formato_titulo = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'left',
                'font_color': '#1F4E78'
            })


            formato_texto = workbook.add_format({
                'bold': True
            })


            worksheet.merge_range(
                0, 0, 0, len(df.columns)-1,
                f"Reporte de Comisiones - {pas_seleccionado}",
                formato_titulo
            )


            # 👇 
            worksheet.set_row(1, 12)
      

            # 👇
            worksheet.write(2, 0, f"Periodo: {fecha_desde} al {fecha_hasta}", formato_texto)
            worksheet.write(3, 0, f"Fecha emisión: {date.today().strftime('%d/%m/%Y')}", formato_texto)



            # =========================
            # FORMATO COLUMNAS
            # =========================

            columnas_moneda = [
                "Prima",
                "Comisión PAS",
                "Comisión PAS s/IVA"
            ]

            columnas_porcentaje = [
                "% PAS"
            ]

            # 👉 asegurar tipo numérico
            for col in columnas_moneda + columnas_porcentaje:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 👉 aplicar formato correcto
            for i, col in enumerate(df.columns):

                if col in columnas_moneda:
                    worksheet.set_column(i, i, 18, formato_moneda)

                elif col in columnas_porcentaje:
                    worksheet.set_column(i, i, 12, formato_porcentaje)
                    
            # =========================
            # AUTO ANCHO
            # =========================
            for i, col in enumerate(df.columns):
                ancho = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2

                worksheet.set_column(i, i, ancho)


        worksheet.autofilter(4, 0, 4 + len(df), len(df.columns)-1)
        return response



    # ============================
    # TOTALES
    # ============================



    total_prima = sum([d["prima"] or 0 for d in filas])
    total_comision = sum([d["comision_agente"] or 0 for d in filas])
    total_comision_pas_sin_iva = sum([d["comision_pas_sin_iva"] or 0 for d in filas])

    from collections import defaultdict


    totales_pas = {}
    totales_agente = {}
    grafico_pass = {}

    for f in filas:

        pas = f["pas_nombre"] or "Sin PAS"

        # PAS
        totales_pas[pas] = totales_pas.get(pas, 0) + (f["comision_pas_sin_iva"] or 0)

        # AGENTE
        totales_agente[pas] = totales_agente.get(pas, 0) + (f["comision_agente"] or 0)

        aseg = f["aseg"] or "Sin Aseg"

        if pas not in grafico_pass:
            grafico_pass[pas] = {}

        if aseg not in grafico_pass[pas]:
            grafico_pass[pas][aseg] = 0

        grafico_pass[pas][aseg] += float(
            f["comision_pas_sin_iva"] or 0
        )

        
    totales_pas = {k: float(v or 0) for k, v in totales_pas.items()}
    totales_agente = {k: float(v or 0) for k, v in totales_agente.items()}


    grafico_pass = {
        pas: {
            aseg: float(valor)
            for aseg, valor in datos.items()
        }
        for pas, datos in grafico_pass.items()
    }


    # ============================
    # RENDER
    # ============================

    return render(
        request,
        "reportes/comisiones.html",
        {
            "datos": filas,
            "pas": PAS.objects.all().order_by("codigo_pas"),
            "aseguradoras": Aseguradoras.objects.filter(activa=True).order_by("nombre"),
            "pas_seleccionado": pas_seleccionado,
            "total_prima": total_prima,
            "total_comision": total_comision,
            "total_comision_pas_sin_iva": total_comision_pas_sin_iva,
            "totales_pas": totales_pas,
            "totales_agente": totales_agente,
            "ver_grafico": ver_grafico,
            "grafico_pass": grafico_pass
        }
    )


import unicodedata

def normalizar_texto(texto):

    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace("\xa0", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")

    texto = " ".join(texto.split())

    texto = texto.lower().strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")

    return texto



def normalizar_signo(valor, aseguradora):

    if valor in [None, "", " "]:
        return Decimal('0')

    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError):
        return Decimal('0')

    if getattr(aseguradora, "invierte_signo", False):
        valor = abs(valor)

    return valor