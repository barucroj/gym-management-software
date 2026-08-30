"""Estadisticas del gimnasio, calculadas al vuelo.

Nada de lo que hay aqui se persiste. Todo se deriva de las tablas que ya
existen, por el mismo motivo que el estatus de una suscripcion: un numero
guardado queda obsoleto en cuanto pasa un dia sin que corra un proceso que lo
actualice.

Las cuentas las hace PostgreSQL, no Python. Hoy el dashboard se descarga el
padron entero y cuenta en el navegador, lo que ademas obliga a mandar los datos
de cada socio para poder mostrar un total.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Integer, cast, func, select
from sqlmodel import Session

from app.services.motor import exigir_postgresql
from app.services.tiempo import ahora_local, hoy_local
from gym_core.config import core_settings
from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.suscripcion import Suscripcion

HORAS_DEL_DIA = 24
DIAS_HORAS_PICO = 30
DIAS_GRAFICO = 7


@dataclass(frozen=True)
class Resumen:
    total_socios: int
    socios_activos: int
    suscripciones_activas: int
    suscripciones_por_vencer: int
    suscripciones_vencidas: int
    asistencias_hoy: int
    ingresos_del_mes: Decimal


@dataclass(frozen=True)
class FranjaHoraria:
    hora: int
    asistencias: int


@dataclass(frozen=True)
class ConteoDiario:
    dia: date
    asistencias: int


def _local(columna):
    """Pasa una marca de tiempo UTC a la hora local del gimnasio.

    timezone(zona, ts) es la forma funcional de AT TIME ZONE. Se aplica en SQL
    y no en Python para poder agrupar sin traerse cada asistencia una por una.
    """
    return func.timezone(core_settings.GYM_TIMEZONE, columna)


def _dia_local():
    return func.date(_local(Asistencia.registrada_en))


def resumen(session: Session, hoy: date | None = None) -> Resumen:
    """KPIs del panel: socios, suscripciones por estatus, asistencias e ingresos."""
    exigir_postgresql(session, "El resumen de estadisticas")
    hoy = hoy or hoy_local()

    # La regla de estatus vive en gym_core.estatus y no se reescribe aqui: se
    # traducen sus dos umbrales a fechas de corte para poder contar en SQL.
    # test_estadisticas compara dia por dia contra calcular_estatus, que es lo
    # que evita que el panel y el notifier terminen diciendo cosas distintas.
    corte_aviso = hoy + timedelta(days=core_settings.NOTIFIER_DAYS_BEFORE_EXPIRATION)

    total_socios, socios_activos = session.execute(
        select(
            func.count(Miembro.id),
            func.count(Miembro.id).filter(Miembro.activo.is_(True)),
        )
    ).one()

    activas, por_vencer, vencidas = session.execute(
        select(
            func.count(Suscripcion.id).filter(Suscripcion.fecha_fin > corte_aviso),
            func.count(Suscripcion.id).filter(
                Suscripcion.fecha_fin >= hoy, Suscripcion.fecha_fin <= corte_aviso
            ),
            func.count(Suscripcion.id).filter(Suscripcion.fecha_fin < hoy),
        )
    ).one()

    asistencias_hoy = session.execute(
        select(func.count(Asistencia.id)).where(_dia_local() == hoy)
    ).scalar_one()

    # El ingreso se cuenta cuando se cobro (creada_en), no cuando empieza la
    # vigencia: una suscripcion vendida hoy para el mes que viene ya se cobro.
    # coalesce porque sin ventas SUM devuelve NULL, no cero.
    ingresos = session.execute(
        select(func.coalesce(func.sum(Suscripcion.precio_pagado), 0)).where(
            func.date(_local(Suscripcion.creada_en)) >= hoy.replace(day=1),
            func.date(_local(Suscripcion.creada_en)) <= hoy,
        )
    ).scalar_one()

    return Resumen(
        total_socios=total_socios,
        socios_activos=socios_activos,
        suscripciones_activas=activas,
        suscripciones_por_vencer=por_vencer,
        suscripciones_vencidas=vencidas,
        asistencias_hoy=asistencias_hoy,
        ingresos_del_mes=Decimal(ingresos),
    )


def horas_pico(session: Session, dias: int = DIAS_HORAS_PICO) -> list[FranjaHoraria]:
    """A que hora viene la gente, en los ultimos `dias` dias.

    Devuelve siempre las 24 franjas, incluidas las de cero: un grafico al que
    le faltan las horas vacias dibuja un eje discontinuo y exagera los picos.
    """
    exigir_postgresql(session, "Las horas pico")
    desde = ahora_local() - timedelta(days=dias)

    hora = cast(func.extract("hour", _local(Asistencia.registrada_en)), Integer).label("hora")
    filas = session.execute(
        select(hora, func.count(Asistencia.id))
        .where(Asistencia.registrada_en >= desde)
        .group_by(hora)
    ).all()

    conteo = {int(franja): int(total) for franja, total in filas}
    return [FranjaHoraria(hora=h, asistencias=conteo.get(h, 0)) for h in range(HORAS_DEL_DIA)]


def asistencias_por_dia(session: Session, dias: int = DIAS_GRAFICO) -> list[ConteoDiario]:
    """Asistencias de cada uno de los ultimos `dias` dias, hoy incluido.

    Los dias sin nadie tambien salen, por el mismo motivo que las horas vacias.
    """
    exigir_postgresql(session, "Las asistencias por dia")
    primero = hoy_local() - timedelta(days=dias - 1)

    # La expresion se arma una sola vez y se reusa en las tres clausulas. Cada
    # llamada a _dia_local() crearia un bind param nuevo, y entonces PostgreSQL
    # no reconoceria el GROUP BY como el mismo del SELECT.
    dia = _dia_local()
    filas = session.execute(
        select(dia.label("dia"), func.count(Asistencia.id)).where(dia >= primero).group_by(dia)
    ).all()

    conteo = {dia: int(total) for dia, total in filas}
    return [
        ConteoDiario(dia=jornada, asistencias=conteo.get(jornada, 0))
        for jornada in (primero + timedelta(days=i) for i in range(dias))
    ]
