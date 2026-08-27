"""Tests del contrato del recurso planes."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from gym_core.models.miembro import Miembro
from gym_core.models.suscripcion import Suscripcion

ALTA = {"nombre": "Mensual", "duracion_dias": 30, "precio": "450.00"}


def test_alta_de_plan(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/planes/", json=ALTA)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert Decimal(cuerpo["precio"]) == Decimal("450.00")
    assert cuerpo["activo"] is True


def test_nombre_duplicado_devuelve_409(client_recepcion: TestClient) -> None:
    client_recepcion.post("/api/v1/planes/", json=ALTA)

    respuesta = client_recepcion.post("/api/v1/planes/", json={**ALTA, "precio": "500.00"})

    assert respuesta.status_code == 409


def test_duracion_no_positiva_se_rechaza(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/planes/", json={**ALTA, "duracion_dias": 0})

    assert respuesta.status_code == 422


def test_precio_negativo_se_rechaza(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/planes/", json={**ALTA, "precio": "-1"})

    assert respuesta.status_code == 422


def test_renombrar_a_uno_ocupado_devuelve_409(client_recepcion: TestClient) -> None:
    primero = client_recepcion.post("/api/v1/planes/", json=ALTA).json()
    client_recepcion.post("/api/v1/planes/", json={**ALTA, "nombre": "Anual"})

    respuesta = client_recepcion.put(f"/api/v1/planes/{primero['id']}", json={"nombre": "Anual"})

    assert respuesta.status_code == 409


def test_plan_sin_ventas_se_puede_borrar(client_recepcion: TestClient) -> None:
    creado = client_recepcion.post("/api/v1/planes/", json=ALTA).json()

    assert client_recepcion.delete(f"/api/v1/planes/{creado['id']}").status_code == 204


def test_plan_con_suscripciones_no_se_borra(
    client_recepcion: TestClient, session: Session
) -> None:
    """El historial de cobros lo referencia: se retira con activo=false."""
    plan = client_recepcion.post("/api/v1/planes/", json=ALTA).json()
    miembro = Miembro(nombre="Ana", apellidos="Torres")
    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    session.add(
        Suscripcion(
            miembro_id=miembro.id,
            plan_id=plan["id"],
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
            precio_pagado=Decimal("450.00"),
        )
    )
    session.commit()

    respuesta = client_recepcion.delete(f"/api/v1/planes/{plan['id']}")

    assert respuesta.status_code == 409

    # La alternativa documentada si funciona.
    retirado = client_recepcion.put(f"/api/v1/planes/{plan['id']}", json={"activo": False})
    assert retirado.json()["activo"] is False


def test_plan_inexistente_devuelve_404(client_recepcion: TestClient) -> None:
    assert client_recepcion.get("/api/v1/planes/404").status_code == 404
    assert client_recepcion.put("/api/v1/planes/404", json={"nombre": "X"}).status_code == 404
    assert client_recepcion.delete("/api/v1/planes/404").status_code == 404
