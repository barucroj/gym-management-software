"""Tests de las estadisticas.

Corren contra PostgreSQL: las consultas usan AT TIME ZONE y FILTER, que SQLite
no tiene. Ver las fixtures *_pg de conftest.py.
"""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.services import estadisticas
from gym_core.config import core_settings
from gym_core.enums import EstatusSuscripcion
from gym_core.estatus import calcular_estatus
from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan
from gym_core.models.suscripcion import Suscripcion

BASE = "/api/v1/estadisticas"


@pytest.fixture(name="miembro")
def miembro_fixture(session_pg: Session) -> Miembro:
    miembro = Miembro(nombre="Ana", apellidos="Torres")
    session_pg.add(miembro)
    session_pg.commit()
    session_pg.refresh(miembro)
    return miembro


@pytest.fixture(name="plan")
def plan_fixture(session_pg: Session) -> Plan:
    plan = Plan(nombre="Mensual", duracion_dias=30, precio=Decimal("500.00"))
    session_pg.add(plan)
    session_pg.commit()
    session_pg.refresh(plan)
    return plan


def registrar(session: Session, miembro: Miembro, cuando: datetime) -> None:
    session.add(Asistencia(miembro_id=miembro.id, registrada_en=cuando))
    session.commit()


# --- horas pico: el motivo de la feature ---


def test_las_horas_pico_devuelven_las_24_franjas(client_pg_recepcion: TestClient) -> None:
    """Un grafico sin las horas vacias dibuja un eje discontinuo."""
    respuesta = client_pg_recepcion.get(f"{BASE}/horas-pico")

    assert respuesta.status_code == 200, respuesta.text
    franjas = respuesta.json()
    assert [f["hora"] for f in franjas] == list(range(24))


def test_cada_entrada_cae_en_su_hora(session_pg: Session, miembro: Miembro) -> None:
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    a_las_19 = ayer.replace(hour=19, minute=30, second=0, microsecond=0)
    registrar(session_pg, miembro, a_las_19)
    registrar(session_pg, miembro, a_las_19)
    registrar(session_pg, miembro, a_las_19.replace(hour=7))

    conteo = {f.hora: f.asistencias for f in estadisticas.horas_pico(session_pg)}

    assert conteo[19] == 2
    assert conteo[7] == 1
    assert conteo[3] == 0


def test_la_hora_se_reporta_en_la_zona_del_gimnasio(
    session_pg: Session, miembro: Miembro, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El pico de las 19:00 de un gimnasio en UTC-6 no es la 01:00 UTC."""
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    registrar(session_pg, miembro, ayer.replace(hour=1, minute=0, second=0, microsecond=0))

    monkeypatch.setattr(core_settings, "GYM_TIMEZONE", "America/Mexico_City")
    conteo = {f.hora: f.asistencias for f in estadisticas.horas_pico(session_pg)}

    assert conteo[19] == 1
    assert conteo[1] == 0


def test_las_horas_pico_ignoran_lo_anterior_a_la_ventana(
    session_pg: Session, miembro: Miembro
) -> None:
    registrar(session_pg, miembro, datetime.now(timezone.utc) - timedelta(days=45))

    conteo = {f.hora: f.asistencias for f in estadisticas.horas_pico(session_pg, dias=30)}

    assert sum(conteo.values()) == 0


# --- serie diaria ---


def test_la_serie_diaria_incluye_los_dias_vacios(session_pg: Session, miembro: Miembro) -> None:
    registrar(session_pg, miembro, datetime.now(timezone.utc))

    serie = estadisticas.asistencias_por_dia(session_pg, dias=7)

    assert len(serie) == 7
    assert serie[-1].dia == estadisticas.hoy_local()
    assert serie[-1].asistencias == 1
    assert serie[0].asistencias == 0


# --- resumen ---


def test_el_resumen_cuenta_socios_y_asistencias(
    session_pg: Session, miembro: Miembro
) -> None:
    session_pg.add(Miembro(nombre="Luis", apellidos="Vera", activo=False))
    session_pg.commit()
    registrar(session_pg, miembro, datetime.now(timezone.utc))

    datos = estadisticas.resumen(session_pg)

    assert datos.total_socios == 2
    assert datos.socios_activos == 1
    assert datos.asistencias_hoy == 1


def test_el_conteo_por_estatus_no_se_aparta_de_la_regla(
    session_pg: Session, miembro: Miembro, plan: Plan
) -> None:
    """La regla vive en gym_core.estatus; el resumen la traduce a SQL.

    Si las dos se separaran, el panel y el notifier dirian cosas distintas del
    mismo socio, que es justo lo que el proyecto decidio evitar teniendo una
    sola regla. Se comparan dia por dia alrededor del umbral de aviso.
    """
    hoy = date(2026, 8, 30)
    aviso = core_settings.NOTIFIER_DAYS_BEFORE_EXPIRATION
    desplazamientos = list(range(-3, aviso + 4))

    for delta in desplazamientos:
        session_pg.add(
            Suscripcion(
                miembro_id=miembro.id,
                plan_id=plan.id,
                fecha_inicio=hoy - timedelta(days=60),
                fecha_fin=hoy + timedelta(days=delta),
                precio_pagado=Decimal("500.00"),
            )
        )
    session_pg.commit()

    esperado = Counter(
        calcular_estatus(hoy + timedelta(days=delta), hoy=hoy) for delta in desplazamientos
    )
    datos = estadisticas.resumen(session_pg, hoy=hoy)

    assert datos.suscripciones_activas == esperado[EstatusSuscripcion.ACTIVA]
    assert datos.suscripciones_por_vencer == esperado[EstatusSuscripcion.POR_VENCER]
    assert datos.suscripciones_vencidas == esperado[EstatusSuscripcion.VENCIDA]


def test_sin_ventas_los_ingresos_son_cero_y_no_nulos(session_pg: Session) -> None:
    """SUM sobre cero filas devuelve NULL, y el schema exige un Decimal."""
    assert estadisticas.resumen(session_pg).ingresos_del_mes == Decimal(0)


def test_los_ingresos_suman_lo_vendido_este_mes(
    session_pg: Session, miembro: Miembro, plan: Plan
) -> None:
    hoy = estadisticas.hoy_local()
    for precio in ("500.00", "300.00"):
        session_pg.add(
            Suscripcion(
                miembro_id=miembro.id,
                plan_id=plan.id,
                fecha_inicio=hoy,
                fecha_fin=hoy + timedelta(days=30),
                precio_pagado=Decimal(precio),
            )
        )
    session_pg.commit()

    assert estadisticas.resumen(session_pg).ingresos_del_mes == Decimal("800.00")


def test_el_resumen_responde_por_http(client_pg_recepcion: TestClient) -> None:
    respuesta = client_pg_recepcion.get(f"{BASE}/resumen")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total_socios"] == 0


def test_las_estadisticas_exigen_autenticacion(client: TestClient) -> None:
    """Se corta en la dependencia, antes de tocar la base: sirve SQLite."""
    for ruta in ("resumen", "horas-pico", "asistencias-por-dia"):
        assert client.get(f"{BASE}/{ruta}").status_code == 401
