"""Fecha y hora en la zona del gimnasio.

Las marcas de tiempo se guardan en UTC, que es lo correcto, pero casi todo lo
que el sistema reporta ("hoy", "a que hora viene la gente", "bajas de este mes")
solo tiene sentido en la hora local del local. El contenedor corre en UTC: sin
esto, un gimnasio en UTC-6 veria las entradas posteriores a las 18:00 contadas
como del dia siguiente.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from gym_core.config import core_settings


def zona() -> ZoneInfo:
    return ZoneInfo(core_settings.GYM_TIMEZONE)


def ahora_local() -> datetime:
    return datetime.now(zona())


def hoy_local() -> date:
    return ahora_local().date()
