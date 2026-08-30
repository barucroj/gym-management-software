"""Tests del contrato del recurso miembros."""

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro

ALTA = {"nombre": "Ana", "apellidos": "Torres", "email": "ana@correo.local"}


def test_alta_de_miembro(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/miembros/", json=ALTA)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre_completo"] == "Ana Torres"
    assert cuerpo["activo"] is True
    assert cuerpo["fecha_registro"] == date.today().isoformat()


def test_apellidos_son_obligatorios(client_recepcion: TestClient) -> None:
    """El formulario del frontend no los manda: aqui queda documentado."""
    respuesta = client_recepcion.post(
        "/api/v1/miembros/", json={"nombre": "Ana", "email": "ana@correo.local"}
    )

    assert respuesta.status_code == 422


def test_email_invalido_se_rechaza(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post("/api/v1/miembros/", json={**ALTA, "email": "arroba-faltante"})

    assert respuesta.status_code == 422


def test_el_miembro_puede_no_tener_email(client_recepcion: TestClient) -> None:
    """Es opcional: no todos los miembros dejan correo."""
    respuesta = client_recepcion.post(
        "/api/v1/miembros/", json={"nombre": "Ana", "apellidos": "Torres"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None


def test_el_cliente_no_impone_fecha_de_registro_ni_estado(client_recepcion: TestClient) -> None:
    respuesta = client_recepcion.post(
        "/api/v1/miembros/", json={**ALTA, "fecha_registro": "2000-01-01", "activo": False}
    )

    cuerpo = respuesta.json()
    assert cuerpo["fecha_registro"] == date.today().isoformat()
    assert cuerpo["activo"] is True


def test_actualizacion_parcial_no_borra_lo_demas(client_recepcion: TestClient) -> None:
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    respuesta = client_recepcion.put(
        f"/api/v1/miembros/{creado['id']}", json={"telefono": "555-1234"}
    )

    cuerpo = respuesta.json()
    assert cuerpo["telefono"] == "555-1234"
    assert cuerpo["nombre"] == "Ana"
    assert cuerpo["email"] == "ana@correo.local"


def test_baja_logica_por_actualizacion(client_recepcion: TestClient) -> None:
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    respuesta = client_recepcion.put(f"/api/v1/miembros/{creado['id']}", json={"activo": False})

    assert respuesta.json()["activo"] is False


def test_miembro_sin_historial_se_puede_borrar(client_recepcion: TestClient) -> None:
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    assert client_recepcion.delete(f"/api/v1/miembros/{creado['id']}").status_code == 204


def test_miembro_con_historial_no_se_borra(
    client_recepcion: TestClient, session: Session
) -> None:
    """Borrarlo violaria la clave foranea y perderia el historial."""
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()
    session.add(Asistencia(miembro_id=creado["id"]))
    session.commit()

    respuesta = client_recepcion.delete(f"/api/v1/miembros/{creado['id']}")

    assert respuesta.status_code == 409
    assert session.get(Miembro, creado["id"]) is not None


def test_miembro_inexistente_devuelve_404(client_recepcion: TestClient) -> None:
    assert client_recepcion.get("/api/v1/miembros/404").status_code == 404
    assert client_recepcion.put("/api/v1/miembros/404", json={"nombre": "X"}).status_code == 404
    assert client_recepcion.delete("/api/v1/miembros/404").status_code == 404


def test_el_email_se_normaliza_a_minusculas(client_recepcion: TestClient) -> None:
    """Sin esto, Ana@correo.local y ana@correo.local serian distintos."""
    respuesta = client_recepcion.post(
        "/api/v1/miembros/", json={**ALTA, "email": "  Ana@Correo.Local  "}
    )

    assert respuesta.json()["email"] == "ana@correo.local"


def test_un_dominio_interno_es_valido(client_recepcion: TestClient) -> None:
    """El sistema corre en la red del gimnasio: .local es legitimo."""
    respuesta = client_recepcion.post(
        "/api/v1/miembros/", json={**ALTA, "email": "recepcion@gimnasio.local"}
    )

    assert respuesta.status_code == 201


def test_dar_de_baja_deja_constancia_de_la_fecha(client_recepcion: TestClient) -> None:
    """Sin la fecha solo se sabe cuantos hay de baja hoy, no cuantos se fueron."""
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    respuesta = client_recepcion.put(
        f"/api/v1/miembros/{creado['id']}",
        json={"activo": False, "motivo_baja": "Se mudó de ciudad"},
    )

    cuerpo = respuesta.json()
    assert cuerpo["activo"] is False
    assert cuerpo["fecha_baja"] == date.today().isoformat()
    assert cuerpo["motivo_baja"] == "Se mudó de ciudad"


def test_el_alta_no_trae_fecha_de_baja(client_recepcion: TestClient) -> None:
    cuerpo = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    assert cuerpo["fecha_baja"] is None
    assert cuerpo["motivo_baja"] is None


def test_reactivar_borra_la_baja_anterior(client_recepcion: TestClient) -> None:
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()
    client_recepcion.put(f"/api/v1/miembros/{creado['id']}", json={"activo": False})

    cuerpo = client_recepcion.put(
        f"/api/v1/miembros/{creado['id']}", json={"activo": True}
    ).json()

    assert cuerpo["fecha_baja"] is None
    assert cuerpo["motivo_baja"] is None


def test_editar_a_un_socio_ya_de_baja_no_le_mueve_la_fecha(
    client_recepcion: TestClient, session: Session
) -> None:
    """Si se corrige el telefono meses despues, la baja sigue siendo la de antes."""
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()
    client_recepcion.put(f"/api/v1/miembros/{creado['id']}", json={"activo": False})

    miembro = session.get(Miembro, creado["id"])
    miembro.fecha_baja = date(2020, 1, 15)
    session.add(miembro)
    session.commit()

    cuerpo = client_recepcion.put(
        f"/api/v1/miembros/{creado['id']}", json={"telefono": "555-1234"}
    ).json()

    assert cuerpo["fecha_baja"] == "2020-01-15"


def test_el_motivo_de_baja_no_se_guarda_si_el_socio_sigue_activo(
    client_recepcion: TestClient,
) -> None:
    creado = client_recepcion.post("/api/v1/miembros/", json=ALTA).json()

    cuerpo = client_recepcion.put(
        f"/api/v1/miembros/{creado['id']}", json={"motivo_baja": "Sin motivo"}
    ).json()

    assert cuerpo["motivo_baja"] is None
