"""Tests del contrato del recurso asistencias."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan
from gym_core.models.suscripcion import Suscripcion


@pytest.fixture(name="miembro_id")
def miembro_fixture(session: Session) -> int:
    miembro = Miembro(nombre="Ana", apellidos="Torres")
    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro.id


def test_check_in(client_recepcion: TestClient, miembro_id: int) -> None:
    respuesta = client_recepcion.post("/api/v1/asistencias/", json={"miembro_id": miembro_id})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["registrada_en"] is not None
    assert cuerpo["suscripcion_id"] is None


def test_la_hora_la_pone_el_servidor(client_recepcion: TestClient, miembro_id: int) -> None:
    """Si la mandara el cliente, el registro no probaria nada."""
    respuesta = client_recepcion.post(
        "/api/v1/asistencias/",
        json={"miembro_id": miembro_id, "registrada_en": "2000-01-01T00:00:00"},
    )

    assert not respuesta.json()["registrada_en"].startswith("2000")


def test_entrada_sin_suscripcion_es_valida(client_recepcion: TestClient, miembro_id: int) -> None:
    """Se registra el dato aunque no haya vigencia: perderlo seria peor."""
    respuesta = client_recepcion.post("/api/v1/asistencias/", json={"miembro_id": miembro_id})

    assert respuesta.status_code == 201


def test_miembro_inexistente_devuelve_422(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/asistencias/", json={"miembro_id": 999})

    assert respuesta.status_code == 422


def test_suscripcion_inexistente_devuelve_422(
    client_recepcion: TestClient, miembro_id: int
) -> None:
    respuesta = client_recepcion.post(
        "/api/v1/asistencias/", json={"miembro_id": miembro_id, "suscripcion_id": 999}
    )

    assert respuesta.status_code == 422


def test_check_in_con_suscripcion_vigente(
    client_recepcion: TestClient, miembro_id: int, session: Session
) -> None:
    plan = Plan(nombre="Mensual", duracion_dias=30, precio=Decimal("450.00"))
    session.add(plan)
    session.commit()
    session.refresh(plan)
    suscripcion = Suscripcion(
        miembro_id=miembro_id,
        plan_id=plan.id,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=30),
        precio_pagado=Decimal("450.00"),
    )
    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)

    respuesta = client_recepcion.post(
        "/api/v1/asistencias/",
        json={"miembro_id": miembro_id, "suscripcion_id": suscripcion.id},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["suscripcion_id"] == suscripcion.id


def test_correccion_de_una_entrada_mal_cargada(
    client_recepcion: TestClient, miembro_id: int
) -> None:
    """El PUT si admite registrada_en: corregir no es lo mismo que registrar."""
    creada = client_recepcion.post(
        "/api/v1/asistencias/", json={"miembro_id": miembro_id}
    ).json()

    respuesta = client_recepcion.put(
        f"/api/v1/asistencias/{creada['id']}", json={"registrada_en": "2026-06-15T08:30:00"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["registrada_en"].startswith("2026-06-15T08:30")


def test_asistencia_inexistente_devuelve_404(client_recepcion: TestClient) -> None:
    assert client_recepcion.get("/api/v1/asistencias/404").status_code == 404
    assert client_recepcion.delete("/api/v1/asistencias/404").status_code == 404
