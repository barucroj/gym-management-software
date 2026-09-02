"""Tests del contrato del recurso suscripciones.

Incluye el estatus, que es la razon de ser del sistema: no se guarda en
ninguna columna, se deriva de fecha_fin en cada lectura.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan

HOY = date.today()


@pytest.fixture(name="miembro_y_plan")
def miembro_y_plan_fixture(session: Session) -> tuple[int, int]:
    miembro = Miembro(nombre="Ana", apellidos="Torres")
    plan = Plan(nombre="Mensual", duracion_dias=30, precio=Decimal("450.00"))
    session.add_all([miembro, plan])
    session.commit()
    session.refresh(miembro)
    session.refresh(plan)
    return miembro.id, plan.id


def _alta(miembro_id: int, plan_id: int, dias: int = 30) -> dict:
    return {
        "miembro_id": miembro_id,
        "plan_id": plan_id,
        "fecha_inicio": HOY.isoformat(),
        "fecha_fin": (HOY + timedelta(days=dias)).isoformat(),
        "precio_pagado": "450.00",
    }


def test_alta_de_suscripcion(client_recepcion: TestClient, miembro_y_plan) -> None:
    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan))

    assert respuesta.status_code == 201
    assert Decimal(respuesta.json()["precio_pagado"]) == Decimal("450.00")


def test_la_respuesta_incluye_el_estatus_calculado(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    """No es una columna: se deriva de fecha_fin al leer."""
    vigente = client_recepcion.post(
        "/api/v1/suscripciones/", json=_alta(*miembro_y_plan, dias=30)
    ).json()

    assert vigente["estatus"] == "activa"


def test_una_suscripcion_terminada_figura_vencida(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    miembro_id, plan_id = miembro_y_plan
    alta = {
        "miembro_id": miembro_id,
        "plan_id": plan_id,
        "fecha_inicio": (HOY - timedelta(days=60)).isoformat(),
        "fecha_fin": (HOY - timedelta(days=30)).isoformat(),
        "precio_pagado": "450.00",
    }

    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=alta)

    assert respuesta.json()["estatus"] == "vencida"


def test_miembro_inexistente_devuelve_422(client_recepcion: TestClient, miembro_y_plan) -> None:
    _, plan_id = miembro_y_plan

    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=_alta(999, plan_id))

    assert respuesta.status_code == 422


def test_plan_inexistente_devuelve_422(client_recepcion: TestClient, miembro_y_plan) -> None:
    miembro_id, _ = miembro_y_plan

    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=_alta(miembro_id, 999))

    assert respuesta.status_code == 422


def test_vigencia_invertida_se_rechaza(client_recepcion: TestClient, miembro_y_plan) -> None:
    """Terminaria "vencida" desde el primer dia sin que nadie entienda por que."""
    respuesta = client_recepcion.post(
        "/api/v1/suscripciones/", json=_alta(*miembro_y_plan, dias=-10)
    )

    assert respuesta.status_code == 422


def test_el_cliente_no_impone_la_fecha_de_registro(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    """creada_en sella cuando el sistema registro la venta: no se antedata."""
    alta = {**_alta(*miembro_y_plan), "creada_en": "2000-01-01T00:00:00"}

    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=alta)

    assert not respuesta.json()["creada_en"].startswith("2000")


def test_suscripcion_con_asistencias_no_se_borra(
    client_recepcion: TestClient, miembro_y_plan, session: Session
) -> None:
    miembro_id, _ = miembro_y_plan
    creada = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan)).json()
    session.add(Asistencia(miembro_id=miembro_id, suscripcion_id=creada["id"]))
    session.commit()

    respuesta = client_recepcion.delete(f"/api/v1/suscripciones/{creada['id']}")

    assert respuesta.status_code == 409


def test_suscripcion_inexistente_devuelve_404(client_recepcion: TestClient) -> None:
    assert client_recepcion.get("/api/v1/suscripciones/404").status_code == 404
    assert client_recepcion.delete("/api/v1/suscripciones/404").status_code == 404


def _renovar(cliente: TestClient, anterior: dict, miembro_id: int, plan_id: int):
    return cliente.post(
        "/api/v1/suscripciones/",
        json={**_alta(miembro_id, plan_id), "renovada_de_id": anterior["id"]},
    )


def test_una_renovacion_queda_enlazada_a_la_anterior(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    """Sin el enlace, una renovacion y una venta nueva se ven identicas."""
    miembro_id, plan_id = miembro_y_plan
    anterior = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan)).json()

    respuesta = _renovar(client_recepcion, anterior, miembro_id, plan_id)

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["renovada_de_id"] == anterior["id"]


def test_una_venta_nueva_no_enlaza_nada(client_recepcion: TestClient, miembro_y_plan) -> None:
    respuesta = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan))

    assert respuesta.json()["renovada_de_id"] is None


def test_no_se_puede_renovar_una_suscripcion_inexistente(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    respuesta = client_recepcion.post(
        "/api/v1/suscripciones/", json={**_alta(*miembro_y_plan), "renovada_de_id": 9999}
    )

    assert respuesta.status_code == 422


def test_no_se_puede_renovar_la_suscripcion_de_otro_socio(
    client_recepcion: TestClient, miembro_y_plan, session: Session
) -> None:
    """Si se permitiera, la tasa de renovacion que se calcule seria ficcion."""
    _, plan_id = miembro_y_plan
    otro = Miembro(nombre="Luis", apellidos="Vera")
    session.add(otro)
    session.commit()
    session.refresh(otro)
    ajena = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan)).json()

    respuesta = _renovar(client_recepcion, ajena, otro.id, plan_id)

    assert respuesta.status_code == 422
    assert "otro miembro" in respuesta.json()["detail"]


def test_una_suscripcion_no_se_renueva_dos_veces(
    client_recepcion: TestClient, miembro_y_plan
) -> None:
    """Dos renovaciones de la misma serian una bifurcacion del historial."""
    miembro_id, plan_id = miembro_y_plan
    anterior = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan)).json()
    _renovar(client_recepcion, anterior, miembro_id, plan_id)

    respuesta = _renovar(client_recepcion, anterior, miembro_id, plan_id)

    assert respuesta.status_code == 409


def test_cancelar_suscripcion_put_y_post(client_recepcion: TestClient, miembro_y_plan) -> None:
    creada = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan, dias=30)).json()
    assert creada["estatus"] == "activa"

    # Cancelar via PUT sin y con slash
    resp_put = client_recepcion.put(f"/api/v1/suscripciones/{creada['id']}/cancelar")
    assert resp_put.status_code == 200
    assert resp_put.json()["status"] == "ok"
    assert resp_put.json()["estatus"] == "vencida"

    resp_put_slash = client_recepcion.put(f"/api/v1/suscripciones/{creada['id']}/cancelar/")
    assert resp_put_slash.status_code == 200

    # Segunda suscripción para probar POST sin y con slash
    creada2 = client_recepcion.post("/api/v1/suscripciones/", json=_alta(*miembro_y_plan, dias=15)).json()
    assert creada2["estatus"] == "activa"
    resp_post = client_recepcion.post(f"/api/v1/suscripciones/{creada2['id']}/cancelar")
    assert resp_post.status_code == 200
    assert resp_post.json()["status"] == "ok"
    assert resp_post.json()["estatus"] == "vencida"

    resp_post_slash = client_recepcion.post(f"/api/v1/suscripciones/{creada2['id']}/cancelar/")
    assert resp_post_slash.status_code == 200


def test_listar_suscripciones_deduplica_por_socio(client_recepcion: TestClient, miembro_y_plan) -> None:
    miembro_id, plan_id = miembro_y_plan
    # Crear 2 suscripciones para el mismo socio
    s1 = client_recepcion.post(
        "/api/v1/suscripciones/",
        json={
            "miembro_id": miembro_id,
            "plan_id": plan_id,
            "fecha_inicio": (HOY - timedelta(days=60)).isoformat(),
            "fecha_fin": (HOY - timedelta(days=30)).isoformat(),
            "precio_pagado": "450.00",
        },
    ).json()

    s2 = client_recepcion.post(
        "/api/v1/suscripciones/",
        json={
            "miembro_id": miembro_id,
            "plan_id": plan_id,
            "fecha_inicio": HOY.isoformat(),
            "fecha_fin": (HOY + timedelta(days=30)).isoformat(),
            "precio_pagado": "450.00",
        },
    ).json()

    # Por defecto, devuelve solo la más reciente por socio
    lista_recientes = client_recepcion.get("/api/v1/suscripciones/").json()
    suscripciones_socio = [s for s in lista_recientes if s["miembro_id"] == miembro_id]
    assert len(suscripciones_socio) == 1
    assert suscripciones_socio[0]["id"] == s2["id"]

    # Si se pide todo el historial, devuelve ambas
    lista_todas = client_recepcion.get("/api/v1/suscripciones/?solo_recientes=false").json()
    suscripciones_todas = [s for s in lista_todas if s["miembro_id"] == miembro_id]
    assert len(suscripciones_todas) == 2

