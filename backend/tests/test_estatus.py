"""Tests de la regla de estatus de suscripcion.

Es la unica regla de negocio del paso 1 y la comparten el API y el notifier,
asi que conviene fijarla con casos explicitos, incluidos los bordes.
"""

from datetime import date, timedelta

import pytest

from gym_core.enums import EstatusSuscripcion
from gym_core.estatus import calcular_estatus

HOY = date(2026, 6, 15)
DIAS_AVISO = 7


@pytest.mark.parametrize(
    ("fecha_fin", "esperado"),
    [
        (HOY + timedelta(days=30), EstatusSuscripcion.ACTIVA),
        (HOY + timedelta(days=8), EstatusSuscripcion.ACTIVA),
        (HOY + timedelta(days=7), EstatusSuscripcion.POR_VENCER),
        (HOY + timedelta(days=1), EstatusSuscripcion.POR_VENCER),
        (HOY, EstatusSuscripcion.POR_VENCER),
        (HOY - timedelta(days=1), EstatusSuscripcion.VENCIDA),
        (HOY - timedelta(days=90), EstatusSuscripcion.VENCIDA),
    ],
)
def test_calcular_estatus(fecha_fin: date, esperado: EstatusSuscripcion) -> None:
    assert calcular_estatus(fecha_fin, hoy=HOY, dias_aviso=DIAS_AVISO) is esperado


def test_ultimo_dia_sigue_vigente() -> None:
    """El ultimo dia de vigencia cuenta como valido, no como vencido."""
    assert calcular_estatus(HOY, hoy=HOY, dias_aviso=DIAS_AVISO) is not EstatusSuscripcion.VENCIDA


def test_frontera_exacta_del_umbral() -> None:
    """Justo en el umbral avisa; un dia mas alla, todavia no."""
    assert calcular_estatus(HOY + timedelta(days=3), hoy=HOY, dias_aviso=3) is EstatusSuscripcion.POR_VENCER
    assert calcular_estatus(HOY + timedelta(days=4), hoy=HOY, dias_aviso=3) is EstatusSuscripcion.ACTIVA


def test_umbral_cero_solo_avisa_el_ultimo_dia() -> None:
    assert calcular_estatus(HOY, hoy=HOY, dias_aviso=0) is EstatusSuscripcion.POR_VENCER
    assert calcular_estatus(HOY + timedelta(days=1), hoy=HOY, dias_aviso=0) is EstatusSuscripcion.ACTIVA
