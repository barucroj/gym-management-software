"""Contratos de salida de las estadisticas.

Solo hay schemas de lectura: estos endpoints no reciben nada que guardar.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ResumenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_socios: int
    socios_activos: int
    suscripciones_activas: int
    suscripciones_por_vencer: int
    suscripciones_vencidas: int
    asistencias_hoy: int
    ingresos_del_mes: Decimal


class FranjaHorariaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Hora local del gimnasio, de 0 a 23. Ver GYM_TIMEZONE.
    hora: int
    asistencias: int


class ConteoDiarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dia: date
    asistencias: int
