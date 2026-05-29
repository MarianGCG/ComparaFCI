from ..models import ParametroSistema


def get_parametro(codigo, default=None):

    try:
        return ParametroSistema.objects.get(
            codigo=codigo
        ).valor

    except ParametroSistema.DoesNotExist:
        return default