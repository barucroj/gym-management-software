"""Regla de negocio: estatus de una suscripcion.

El estatus NO se guarda en la base de datos. Si se guardara, quedaria obsoleto
en cuanto pasara un dia sin que corriera un proceso de actualizacion. Se deriva
siempre de la fecha de fin contra la fecha actual.

Vive en gym_core para que el API y el notifier apliquen exactamente la misma
regla: si divergieran, el sistema podria alertar de un vencimiento que la
pantalla de consulta reporta como activo.
"""

from datetime import date

from gym_core.config import core_settings
from gym_core.enums import EstatusSuscripcion


def calcular_estatus(
    fecha_fin: date,
    hoy: date | None = None,
    dias_aviso: int | None = None,
) -> EstatusSuscripcion:
    """Devuelve el estatus de una suscripcion que termina en `fecha_fin`.

    Args:
        fecha_fin: ultimo dia de vigencia, inclusivo.
        hoy: fecha de referencia. Por defecto, la fecha actual.
        dias_aviso: umbral de anticipacion para considerarla por vencer.
            Por defecto, NOTIFIER_DAYS_BEFORE_EXPIRATION.

    Reglas:
        - VENCIDA:    fecha_fin ya paso.
        - POR_VENCER: quedan `dias_aviso` dias o menos.
        - ACTIVA:     queda mas tiempo que el umbral.

    El ultimo dia de vigencia cuenta como POR_VENCER, no como VENCIDA: la
    suscripcion sigue siendo valida ese dia.
    """
    hoy = hoy or date.today()
    if dias_aviso is None:
        dias_aviso = core_settings.NOTIFIER_DAYS_BEFORE_EXPIRATION

    if fecha_fin < hoy:
        return EstatusSuscripcion.VENCIDA
    if (fecha_fin - hoy).days <= dias_aviso:
        return EstatusSuscripcion.POR_VENCER
    return EstatusSuscripcion.ACTIVA
