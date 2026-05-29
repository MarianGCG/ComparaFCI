# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Aseguradoras(models.Model):

    nombre = models.TextField()
    cuit = models.CharField(max_length=13, blank=True, null=True)
    tipo_factura = models.CharField(max_length=1, blank=True, null=True)
    activa = models.BooleanField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    codigo_interno = models.CharField(max_length=20, blank=True, null=True)
    razon_social_afip = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default="#3366cc" )
    grupo = models.CharField(max_length=2, blank=True, null=True)
    incluye_iva = models.CharField(max_length=1, choices=[("S", "Sí"), ("N", "No")], default="N")

    # 👇 AGREGAR ESTO
    invierte_signo = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'aseguradoras'
        


class CobranzasComisiones(models.Model):
    comprobante = models.ForeignKey('ComprobantesComisiones', models.DO_NOTHING, blank=True, null=True)
    fecha_cobro = models.DateField()
    tipo_factura = models.CharField(max_length=1, blank=True, null=True)
    numero_comprobante = models.IntegerField(blank=True, null=True)
    importe = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=1, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.comprobante} - {self.importe}"

    class Meta:
        db_table = 'cobranzas_comisiones'


class ComprobantesComisiones(models.Model):
    aseguradora = models.ForeignKey(Aseguradoras, models.DO_NOTHING)
    fecha_comprobante = models.DateField()
    periodo_anio = models.IntegerField()
    periodo_mes = models.IntegerField()
    tipo_comprobante = models.CharField(max_length=20)
    tipo_factura = models.CharField(max_length=1)
    numero_comprobante = models.CharField(max_length=20)
    moneda = models.CharField(max_length=1, blank=True, null=True)
    neto = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    exento = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    iva = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    codigo_interno = models.CharField(max_length=20, blank=True, null=True)
    no_gravado = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.numero_comprobante}"
    
    class Meta:
        db_table = 'comprobantes_comisiones'
        unique_together = (('aseguradora', 'tipo_comprobante', 'tipo_factura', 'numero_comprobante', 'periodo_anio', 'periodo_mes'),)

class CotizacionesDolar(models.Model):
    id = models.BigAutoField(primary_key=True)
    periodo_anio = models.IntegerField()
    periodo_mes = models.IntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = 'cotizaciones_dolar'
        unique_together = (('periodo_anio', 'periodo_mes'),)

class ParametroSistema(models.Model):

    codigo = models.CharField(
        max_length=50,
        unique=True
    )

    valor = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    descripcion = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.codigo} = {self.valor}"

    class Meta:
        db_table = "parametros_sistema"
        verbose_name = "Parametro del sistema"
        verbose_name_plural = "Parametros del sistema"
        



class ImportacionComisiones(models.Model):

    aseguradora = models.ForeignKey(
        Aseguradoras,
        on_delete=models.CASCADE
    )

    nombre_archivo = models.CharField(max_length=200)

    fecha_importacion = models.DateTimeField(auto_now_add=True)

    registros = models.IntegerField(default=0)

    cantidad_clientes = models.IntegerField(default=0)

    comision_total = models.FloatField(default=0)

    usuario = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre_archivo}"
    
    

class LiquidacionAseguradora(models.Model):


    importacion = models.ForeignKey(
        ImportacionComisiones,
        on_delete=models.CASCADE,
        related_name="lineas",
        null=True,
        blank=True
    )

    aseguradora = models.ForeignKey(
        "Aseguradoras",
        on_delete=models.CASCADE
    )

    cliente = models.CharField(max_length=200, null=True, blank=True)
    cuit = models.CharField(max_length=20, null=True, blank=True)

    ramo = models.CharField(max_length=100, null=True, blank=True)
    poliza = models.CharField(max_length=50, null=True, blank=True)

    moneda = models.CharField(max_length=10, null=True, blank=True)

    premio = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    prima = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    porcentaje = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    comision_compania = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    comision_adelantada = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    comision_agente = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    comision_agente_con_iva = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    comision_agente_sin_iva = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    cotizacion_dolar = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    meses_adelanto = models.IntegerField(null=True, blank=True)

    fecha_liquidacion = models.DateField(null=True, blank=True)
    quincena = models.CharField(max_length=2, null=True, blank=True)    
    fecha_pago = models.DateField(null=True, blank=True)

    archivo_origen = models.CharField(max_length=200, null=True, blank=True)
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    endoso = models.IntegerField(null=True, blank=True)

    descuento_adelanto = models.DecimalField( max_digits=14, decimal_places=2, null=True, blank=True)



class PAS(models.Model):

    codigo_pas = models.CharField(
        max_length=20,
        primary_key=True
    )

    nombre = models.CharField(max_length=200)

    cuit = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    cvu = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    class Meta:
        db_table = "pas"
        
class PASAseguradora(models.Model):

    codigo_pas_aseguradora = models.AutoField(
        primary_key=True
    )

    pas = models.ForeignKey(
        "PAS",
        on_delete=models.CASCADE
    )

    aseguradora = models.ForeignKey(
        "Aseguradoras",
        on_delete=models.CASCADE
    )


    nivel = models.IntegerField(null=True, blank=True)
    rango = models.CharField(max_length=30, null=True, blank=True)


    fecha = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.pas} - {self.aseguradora}"

    class Meta:
        db_table = "pas_aseguradoras"




class PASCliente(models.Model):

    id = models.AutoField(primary_key=True)

    pas = models.ForeignKey(
        "PAS",
        on_delete=models.CASCADE
    )


    aseguradora = models.ForeignKey(
        "Aseguradoras",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    cliente = models.CharField(max_length=200)

    cliente_clave1 = models.CharField(max_length=100, blank=True, null=True)
    cliente_clave2 = models.CharField(max_length=100, blank=True, null=True)

    cuit = models.CharField(max_length=13, blank=True, null=True)



    def __str__(self):
        return self.cliente

    class Meta:
        db_table = "pas_clientes"


class ReglaComision(models.Model):


    BASE_COMISION_CHOICES = [
        ("Prima", "Prima"),
        ("Comision", "Comisión Agente"),
    ]


    aseguradora = models.ForeignKey(
        "Aseguradoras",
        on_delete=models.CASCADE
    )

    producto = models.CharField(max_length=50)

    nivel = models.IntegerField()

    anio_poliza = models.IntegerField(
        null=True,
        blank=True
    )

    moneda = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    rango = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    tope = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    porcentaje = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )


    base_comision = models.CharField(
        max_length=10,
        choices=BASE_COMISION_CHOICES,
        default="Prima"
    )


    class Meta:
        db_table = "reglas_comision"
        