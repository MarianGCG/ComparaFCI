from django.shortcuts import render, redirect

from .forms import ImportarExcelForm
from .models import (
    Aseguradoras,
    ComprobantesComisiones,
    ImportacionComisiones,
    PAS,
    PASAseguradora,
    PASCliente,
    ReglaComision,
    LiquidacionAseguradora,
    CotizacionesDolar
)

from .services.dolar_service import importar_cotizaciones_excel
from .services.aseguradoras_service import importar_aseguradoras_excel
from .services.comprobantes_arca_service import importar_comprobantes_arca
from .services.cobranzas_service import importar_cobranzas_excel
from .services.comisiones_service import importar_comisiones_excel
from .services.pas_service import importar_pas_excel
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .services.reglas_comision_service import importar_reglas_comision_excel
from .models import ReglaComision

    
# ================================
# IMPORTAR DÓLAR
# ================================
def importar_dolar_view(request):

    resultado = None

    if request.method == "POST":
        form = ImportarExcelForm(request.POST, request.FILES)

        if form.is_valid():
            archivo = request.FILES["archivo"]
            resultado = importar_cotizaciones_excel(archivo)

    else:
        form = ImportarExcelForm()


    # 👇 SIEMPRE carga datos al abrir pantalla
    cotizaciones = CotizacionesDolar.objects.all().order_by(
        "-periodo_anio",
        "-periodo_mes"
    )

    return render(
        request,
        "importaciones/form_importar.html",
        {
            "form": form,
            "resultado": resultado,
            "titulo": "Importar cotizaciones dólar",
            "cotizaciones": cotizaciones

        }
    )


# ================================
# LISTAR ASEGURADORAS
# ================================
def listar_aseguradoras_view(request):

    aseguradoras = Aseguradoras.objects.all().order_by("nombre")

    return render(
        request,
        "importaciones/listar_aseguradoras.html",
        {
            "aseguradoras": aseguradoras,
            "titulo": "Listado de Aseguradoras"
        }
    )


# ================================
# IMPORTAR COMPROBANTES ARCA
# ================================
def importar_comprobantes_arca_view(request):

    resultado = None

    if request.method == "POST":

        archivo = request.FILES.get("archivo")

        if archivo:
            resultado = importar_comprobantes_arca(archivo)

    return render(
        request,
        "importaciones/comprobantes_arca.html",
        {
            "resultado": resultado
        }
    )


# ================================
# IMPORTAR COBRANZAS
# ================================
def importar_cobranzas_view(request):

    resultado = None

    if request.method == "POST":

        archivo = request.FILES.get("archivo")

        if archivo:
            resultado = importar_cobranzas_excel(archivo)

    return render(
        request,
        "importaciones/cobranzas.html",
        {
            "resultado": resultado
        }
    )


# ================================
# ASEGURADORAS
# ================================
def aseguradoras_view(request):

    resultado = None

    if request.method == "POST" and "archivo" in request.FILES:

        form = ImportarExcelForm(request.POST, request.FILES)

        if form.is_valid():
            archivo = request.FILES["archivo"]
            resultado = importar_aseguradoras_excel(archivo)

    else:
        form = ImportarExcelForm()


    # 🔥 AGREGAR ESTO ACÁ
    toggle_signo = request.GET.get("toggle_signo")

    if toggle_signo:

        aseg = Aseguradoras.objects.get(id=toggle_signo)
        aseg.invierte_signo = not aseg.invierte_signo
        aseg.save()
        

    aseguradoras = Aseguradoras.objects.all()

    # FILTROS
    nombre = request.GET.get("nombre")
    estado = request.GET.get("estado")
    ordenar = request.GET.get("ordenar")

    if nombre:
        aseguradoras = aseguradoras.filter(nombre__icontains=nombre)

    if estado == "activas":
        aseguradoras = aseguradoras.filter(activa=True)

    elif estado == "inactivas":
        aseguradoras = aseguradoras.filter(activa=False)

    columnas_validas = [
        "nombre",
        "cuit",
        "tipo_factura",
        "email",
        "codigo_interno",
        "grupo",
        "activa",
        "color",
    ]

    if ordenar in columnas_validas:
        aseguradoras = aseguradoras.order_by(ordenar)
    else:
        aseguradoras = aseguradoras.order_by("nombre")

    return render(
        request,
        "importaciones/aseguradoras.html",
        {
            "form": form,
            "resultado": resultado,
            "aseguradoras": aseguradoras,
            "ordenar_actual": ordenar,
        }
    )

# ================================
# ACTUALIZAR GRUPO ASEGURADORA
# ================================
def actualizar_grupo_aseguradora(request, id):

    aseguradora = Aseguradoras.objects.get(id=id)

    grupo = request.POST.get("grupo")

    if grupo:
        aseguradora.grupo = grupo.strip().upper()
    else:
        aseguradora.grupo = None

    aseguradora.save()

    return redirect("aseguradoras")



# ================================
# ACTIVAR ASEGURADORA
# ================================
def activar_aseguradora(request, id):

    aseguradora = Aseguradoras.objects.get(id=id)

    color = request.POST.get("color")

    if color:
        aseguradora.color = color

    aseguradora.activa = True
    aseguradora.save()

    return redirect("aseguradoras")


# ================================
# ELIMINAR / DESACTIVAR ASEGURADORA
# ================================
def eliminar_o_desactivar_aseguradora(request, id):

    aseguradora = Aseguradoras.objects.get(id=id)

    tiene_movimientos = ComprobantesComisiones.objects.filter(
        aseguradora_id=aseguradora.id
    ).exists()

    if tiene_movimientos:
        aseguradora.activa = False
        aseguradora.save()
    else:
        aseguradora.delete()

    return redirect("aseguradoras")


# ================================
# HISTORIAL LIQUIDACIONES
# ================================


def obtener_historial_importaciones():
    return ImportacionComisiones.objects.all().order_by("-fecha_importacion")


# ================================
# IMPORTAR LIQUIDACIONES
# ================================
def importar_liquidaciones_view(request):

    resultado = None
    aseguradoras = Aseguradoras.objects.filter(activa=True).order_by("nombre")

    if request.method == "POST":

        archivo = request.FILES.get("archivo")
        aseguradora_id = request.POST.get("aseguradora_id")

        if archivo and aseguradora_id:

            nombre_archivo = archivo.name.lower()

            # 🔵 SI ES PDF
            if nombre_archivo.endswith(".pdf"):

                from .services.comisiones_service import (
                    procesar_pdf_atm,
                    importar_desde_dataframe
                )

                df = procesar_pdf_atm(archivo)

                resultado = importar_desde_dataframe(
                    df,
                    archivo.name,
                    aseguradora_id
                )

            # 🟢 SI ES EXCEL (TU FLUJO ORIGINAL)
            else:

                resultado = importar_comisiones_excel(
                    archivo,
                    aseguradora_id
                )

    historial = obtener_historial_importaciones()

    return render(
        request,
        "importaciones/importar_liquidaciones.html",
        {
            "resultado": resultado,
            "aseguradoras": aseguradoras,
            "importaciones": historial
        }
    )


# ================================
# IMPORTAR COMISIONES
# ================================






def importar_comisiones_view(request):

    resultado = None
    aseguradora_id = None

    aseguradoras = Aseguradoras.objects.filter(activa=True).order_by("nombre")

    if request.method == "POST":

        archivo = request.FILES.get("archivo")
        aseguradora_id = request.POST.get("aseguradora_id")

        if not aseguradora_id:
            resultado = "Seleccione una aseguradora"

        elif not archivo:
            resultado = "Debe seleccionar un archivo"

        else:

            aseguradora = Aseguradoras.objects.get(id=aseguradora_id)


            nombre_archivo = archivo.name.upper()

            # 🔹 parte antes del "_"
            codigo_archivo = nombre_archivo.split("_")[0].strip()

            # 🔹 nombre aseguradora
            aseguradora = Aseguradoras.objects.get(id=aseguradora_id)
            nombre_aseguradora = aseguradora.nombre.upper().strip()

            # 🔹 validar
            if codigo_archivo != nombre_aseguradora:

                resultado = f"❌ Archivo inválido. Esperado: {nombre_aseguradora} | Recibido: {codigo_archivo}"

            else:
          
          
                cantidad_inicial = ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).count()

                ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).delete()

                resultado = importar_reglas_comision_excel(
                    archivo,
                    aseguradora_id
                )

                cantidad_actual = ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).count()

                cantidad_importadas = cantidad_actual
               

                

    # SIEMPRE cargar importaciones antes del render
    importaciones = ImportacionComisiones.objects.all().order_by("-fecha_importacion")

    return render(
        request,
        "importaciones/importar_comisiones.html",
        {
            "resultado": resultado,
            "aseguradoras": aseguradoras,
            "importaciones": importaciones,
            "aseguradora_seleccionada": int(aseguradora_id) if aseguradora_id else None
        }
    )




# ================================
# HISTORIAL DE IMPORTACIONES
# ================================
def historial_importaciones_comisiones(request):

    importaciones = ImportacionComisiones.objects.all().order_by("-fecha_importacion")

    return render(
        request,
        "importaciones/historial_importaciones.html",
        {
            "importaciones": importaciones
        }
    )


# ================================
# ELIMINAR IMPORTACIÓN
# ================================
def eliminar_importacion(request, id):

    importacion = ImportacionComisiones.objects.get(id=id)

    importacion.delete()

    return redirect("importar_liquidaciones")





def productores_view(request):

    resultado = None

    if request.method == "POST":
        archivo = request.FILES.get("archivo")

        if archivo:
            resultado = importar_pas_excel(archivo)

        request.session["mensaje_importacion"] = resultado
        return redirect("productores")


    resultado = request.session.pop("mensaje_importacion", None)

    productores = PAS.objects.all().order_by("codigo_pas")

    return render(request,"importaciones/productores.html",{
        "productores": productores,
        "resultado": resultado
    })



def productor_eliminar(request, codigo):

    p = get_object_or_404(PAS, codigo_pas=codigo)
    p.delete()

    return redirect("productores")

def productor_editar(request, codigo):

    codigo = str(codigo).strip()
    print("CODIGO RECIBIDO:", codigo)

    try:
        p = PAS.objects.get(codigo_pas=codigo)
    except PAS.DoesNotExist:
        return JsonResponse({"ok": False})

    if request.method == "POST":

        data = json.loads(request.body)

        p.nombre = data.get("nombre")
        p.cuit = data.get("cuit")
        p.cvu = data.get("cvu")

        p.save()

        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False})



# ================================
# PAS - ASEGURADORAS
# ================================
def pas_aseguradoras_view(request):

    datos = (
        PASAseguradora.objects
        .select_related("pas","aseguradora")
        .order_by("pas__codigo_pas")
    )

    pas = PAS.objects.all().order_by("codigo_pas")

    aseguradoras = Aseguradoras.objects.filter(activa=True).order_by("nombre")

    return render(
        request,
        "importaciones/pas_aseguradoras.html",
        {
            "datos": datos,
            "pas": pas,
            "aseguradoras": aseguradoras
        }
    )



def pas_aseguradora_eliminar(request, id):

    obj = PASAseguradora.objects.get(
        codigo_pas_aseguradora=id
    )

    obj.delete()

    return redirect("pas_aseguradoras")



def pas_aseguradora_editar(request, id):

    obj = get_object_or_404(PAS_Aseguradora, id=id)

    if request.method == "POST":

        data = json.loads(request.body)

        obj.codigo_pas = data.get("codigo_pas")
        obj.aseguradora = data.get("aseguradora")

        obj.save()

        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False})


# ================================
# PAS - CLIENTES
# ================================


def pas_clientes_view(request):

    resultado = None
    pas_codigo = request.GET.get("pas")

    datos = PASCliente.objects.select_related("pas", "aseguradora")

    # ✅ FILTRO
    if pas_codigo:
        datos = datos.filter(pas__codigo_pas=pas_codigo)

    # 🔥 IMPORTACIÓN
    if request.method == "POST" and "importar_excel" in request.POST:

        archivo = request.FILES.get("archivo")

        if archivo:
            from .services.importar_pas_clientes_excel import importar_pas_clientes_excel
            resultado = importar_pas_clientes_excel(archivo)

            # 🔁 refrescar queryset después de importar
            datos = PASCliente.objects.select_related("pas", "aseguradora")

            if pas_codigo:
                datos = datos.filter(pas__codigo_pas=pas_codigo)

    # ✅ ORDEN FINAL
    datos = datos.order_by("pas__codigo_pas")

    pas = PAS.objects.all().order_by("codigo_pas")
    aseguradoras = Aseguradoras.objects.filter(activa=True).order_by("nombre")

    return render(
        request,
        "importaciones/pas_clientes.html",
        {
            "datos": datos,
            "pas": pas,
            "aseguradoras": aseguradoras,
            "resultado": resultado
        }
    )




def pas_aseguradora_guardar(request):

    if request.method == "POST":

        data = json.loads(request.body)

        id = data.get("id")
        pas_id = data.get("pas")
        aseguradora_id = data.get("aseguradora")
        nivel = data.get("nivel")
        rango = data.get("rango")

        if id:
            obj = PASAseguradora.objects.get(id=int(id))
        else:
            obj = PASAseguradora()

        obj.pas_id = int(pas_id) if pas_id else None
        obj.aseguradora_id = int(aseguradora_id) if aseguradora_id else None
        obj.nivel = int(nivel) if nivel else None
        obj.rango = rango or None

        obj.save()

        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False})



def pas_cliente_guardar(request):

    if request.method == "POST":

        data = json.loads(request.body)

        id = data.get("id")
        pas_id = data.get("pas")
        aseguradora_id = data.get("aseguradora")        
        cliente = data.get("cliente")
        clave1 = data.get("clave1")
        clave2 = data.get("clave2")
        cuit = data.get("cuit")


        if id:
            obj = PASCliente.objects.get(id=id)
        else:
            obj = PASCliente()

        obj.pas_id = pas_id
        obj.aseguradora_id = int(aseguradora_id) if aseguradora_id else None
        obj.cliente = cliente
        obj.cliente_clave1 = clave1
        obj.cliente_clave2 = clave2
        obj.cuit = cuit

        
        obj.save()

        return JsonResponse({
            "ok": True,
            "id": obj.id,
            "pas": obj.pas.codigo_pas,
            "aseguradora": obj.aseguradora.nombre if obj.aseguradora else "",
            "aseguradora_id": obj.aseguradora.id if obj.aseguradora else "",   # 👈 CLAVE
            "cliente": obj.cliente,
            "clave1": obj.cliente_clave1,
            "clave2": obj.cliente_clave2
        })


    return JsonResponse({"ok": False})






def pas_cliente_eliminar(request, id):

    obj = PASCliente.objects.get(id=id)

    obj.delete()

    return redirect("pas_clientes")


def importar_pas_clientes_view(request):

    resultado = None

    if request.method == "POST":

        archivo = request.FILES.get("archivo")

        if archivo:
            from .services.importar_pas_clientes_excel import importar_pas_clientes_excel
            resultado = importar_pas_clientes_excel(archivo)

    return render(
        request,
        "importaciones/importar_pas_clientes.html",
        {
            "resultado": resultado
        }
    )


def guardar_regla_comision(request):

    if request.method == "POST":

        data = json.loads(request.body)

        regla_id = data.get("id")
        print("ID RECIBIDO:", regla_id)

        if regla_id:
            try:
                regla_id = int(str(regla_id).replace(".", ""))
            except:
                return JsonResponse({"ok": False, "error": "ID inválido"})

            regla = ReglaComision.objects.filter(id=regla_id).first()

            if not regla:
                return JsonResponse({"ok": False, "error": "Registro no encontrado"})
        else:
            regla = ReglaComision()

            # 🔹 SOLO NUEVA
            regla.aseguradora_id = data["aseguradora"]
            regla.producto = data["producto"]
            regla.moneda = data["moneda"]

     
        print("DATA:", data)
        print("ANTES:", regla.nivel, regla.rango, regla.anio_poliza, regla.porcentaje)

        # 🔥 SIEMPRE EDITABLES
        regla.nivel = int(data.get("nivel") or 0)
        regla.anio_poliza = int(data.get("anio") or 0)
        regla.porcentaje = float(data.get("porcentaje") or 0)
        regla.rango = data.get("rango") or None
        regla.base_comision = data.get("base_comision", "Prima")

        regla.save()

        print("DESPUES:", regla.nivel, regla.rango, regla.anio_poliza, regla.porcentaje)

        return JsonResponse({
            "ok": True,
            "regla": {
                "id": regla.id,
                "aseguradora": regla.aseguradora.nombre,
                "aseguradora_id": regla.aseguradora.id,
                "producto": regla.producto,
                "moneda": regla.moneda,
                "nivel": regla.nivel,
                "rango": regla.rango,
                "anio": regla.anio_poliza,
                "porcentaje": regla.porcentaje, 
                "base_comision": regla.base_comision
            }
        })



    return JsonResponse({"ok": False})


def normalizar_moneda(m):
    if not m:
        return ""

    m = m.strip().upper()

    if m in ["U$S", "USD", "U S D", "DOLAR", "DÓLAR", "UDS"]:
        return "U$S"

    if m in ["$", "ARS", "PESOS"]:
        return "$"

    return m



def eliminar_regla_comision(request, id):

    try:
        ReglaComision.objects.get(id=id).delete()
        return JsonResponse({"ok": True})
    except:
        return JsonResponse({"ok": False})


def reglas_comision_view(request):

    resultado = None

    cantidad_inicial = None
    cantidad_actual = None
    cantidad_importadas = None

    if request.method == "POST":

        aseguradora_id = int(request.POST["aseguradora_id"])
        archivo = request.FILES.get("archivo")

        if archivo:

            nombre_archivo = archivo.name.upper()
            codigo_archivo = nombre_archivo.split("_")[0].strip()

            aseguradora = Aseguradoras.objects.get(id=aseguradora_id)
            nombre_aseguradora = aseguradora.nombre.upper().strip()

            largo = len(nombre_aseguradora)

            # 🚨 VALIDAR PRIMERO
            if codigo_archivo[:largo] != nombre_aseguradora:

                resultado = f"❌ Archivo inválido. Esperado: {nombre_aseguradora} | Recibido: {codigo_archivo}"

            else:
                    
                # 🔹 1. cantidad inicial (ANTES de borrar)
                cantidad_inicial = ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).count()

                # 🔹 2. borrar
                ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).delete()

                # 🔹 3. importar
                resultado = importar_reglas_comision_excel(
                    archivo,
                    aseguradora_id
                )

                # 🔹 4. cantidad final (DESPUÉS de importar)
                cantidad_actual = ReglaComision.objects.filter(
                    aseguradora_id=aseguradora_id
                ).count()

                # 🔹 5. importadas reales (desde BD)
                cantidad_importadas = cantidad_actual


    reglas = ReglaComision.objects.select_related("aseguradora").all()

    aseguradoras = Aseguradoras.objects.filter(activa=True).order_by("nombre")

    from collections import defaultdict


    from collections import defaultdict

    arbol_tmp = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for r in reglas:
        arbol_tmp[r.aseguradora.nombre][r.producto][r.moneda].append(r)

    # 👇 convertir a dict normal (CLAVE)
    arbol = {}

    for aseg, productos in arbol_tmp.items():
        arbol[aseg] = {}
        for prod, monedas in productos.items():
            arbol[aseg][prod] = {}
            for moneda, regs in monedas.items():
                arbol[aseg][prod][moneda] = regs

                

    return render(
        request,
        "importaciones/reglas_comision.html",
        {
            "reglas": reglas,
            "aseguradoras": aseguradoras,
            "resultado": resultado,
            "arbol": arbol ,  # 👈 NUEVO
            "cantidad_inicial": cantidad_inicial,
            "cantidad_actual": cantidad_actual,
            "cantidad_importadas": cantidad_importadas,

        }
    )        




def liquidacion_obtener(request, id):

    l = LiquidacionAseguradora.objects.get(id=id)

    return JsonResponse({
        "id": l.id,
        "cliente": l.cliente,
        "poliza": l.poliza,
        "prima": float(l.prima or 0),
        "comision": float(l.comision_agente or 0),
    })




@csrf_exempt
def liquidacion_eliminar(request, id):

    if request.method == "POST":
        try:
            LiquidacionAseguradora.objects.filter(id=id).delete()
            return JsonResponse({"ok": True})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)})

    return JsonResponse({"ok": False, "error": "Método inválido"})


