from django.urls import path
from . import views
from . import views_importaciones
from .views_importaciones import importar_comprobantes_arca_view
from .views_importaciones import importar_cobranzas_view
from .views_importaciones import liquidacion_eliminar, liquidacion_obtener
from . import views_reportes

urlpatterns = [

    # Importaciones
    path("importar-dolar/", views_importaciones.importar_dolar_view, name="importar_dolar"),
    path("aseguradoras/",  views_importaciones.aseguradoras_view,  name="aseguradoras"),
    path("aseguradoras/activar/<int:id>/",     views_importaciones.activar_aseguradora,   name="activar_aseguradora"),
    path("aseguradoras/eliminar/<int:id>/",    views_importaciones.eliminar_o_desactivar_aseguradora,  name="eliminar_aseguradora"),
    path("aseguradoras/actualizar-grupo/<int:id>/", views_importaciones.actualizar_grupo_aseguradora, name="actualizar_grupo_aseguradora"),    
    path("importaciones/comprobantes-arca/",   importar_comprobantes_arca_view, name="importar_comprobantes_arca" ),
    path("importaciones/cobranzas/", importar_cobranzas_view, name="importar_cobranzas"),
    path("grafico-indice-mensual/", views.grafico_indice_mensual, name="grafico_indice_mensual"),
    path("parametros/", views.parametros_view, name="parametros"),
    path("parametros/nuevo/", views.parametro_nuevo_view, name="parametro_nuevo"),
    path("parametros/editar/<int:id>/", views.parametro_editar_view, name="parametro_editar"),
    path("parametros/eliminar/<int:id>/", views.parametro_eliminar_view, name="parametro_eliminar"),
    path("importar-reglas/", views_importaciones.importar_comisiones_view, name="importar_reglas"),
    path("importaciones-comisiones/", views_importaciones.historial_importaciones_comisiones, name="historial_importaciones_comisiones"),
    path("eliminar-importacion/<int:id>/", views_importaciones.eliminar_importacion, name="eliminar_importacion"),
    path("productores/",views_importaciones.productores_view,name="productores" ),
    path("productor_editar/<str:codigo>/", views_importaciones.productor_editar, name="productor_editar"),
    path("productor_eliminar/<str:codigo>/", views_importaciones.productor_eliminar, name="productor_eliminar"),
    path("pas-aseguradoras/", views_importaciones.pas_aseguradoras_view, name="pas_aseguradoras"),
    path("pas-aseguradora-editar/<int:id>/", views_importaciones.pas_aseguradora_editar, name="pas_aseguradora_editar"),
    path("pas-aseguradora-eliminar/<int:id>/", views_importaciones.pas_aseguradora_eliminar, name="pas_aseguradora_eliminar"),
    path("pas-aseguradora-guardar/",views_importaciones.pas_aseguradora_guardar,name="pas_aseguradora_guardar"),
    path("pas-clientes/", views_importaciones.pas_clientes_view, name="pas_clientes"),
    path("pas-cliente-guardar/", views_importaciones.pas_cliente_guardar, name="pas_cliente_guardar"),
    path("pas-cliente-eliminar/<int:id>/", views_importaciones.pas_cliente_eliminar, name="pas_cliente_eliminar"),
    path("reporte-comisiones/", views_reportes.reporte_comisiones_view, name="reporte_comisiones"),
    path("reglas-comision/",views_importaciones.reglas_comision_view, name="reglas_comision"),
    path("guardar-regla-comision/", views_importaciones.guardar_regla_comision),
    path("eliminar-regla-comision/<int:id>/", views_importaciones.eliminar_regla_comision),
    path("importar-liquidaciones/", views_importaciones.importar_liquidaciones_view, name="importar_liquidaciones"),
    path("aseguradoras/iva/<int:id>/", views.actualizar_iva_aseguradora, name="actualizar_iva_aseguradora"),
    path("liquidacion-eliminar/<int:id>/", views_importaciones.liquidacion_eliminar),
    path("liquidacion-obtener/<int:id>/", views_importaciones.liquidacion_eliminar),
    
]

