"""Tests de autenticacion y autorizacion.

Fijan las dos preguntas que el sistema debe responder siempre igual:
quien sos (401) y si te alcanza el rol (403).
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import crear_token_acceso
from gym_core.models.usuario import Usuario
from tests.conftest import CLAVE_ADMIN, CLAVE_RECEPCION

PROTEGIDO = "/api/v1/miembros/"


# --- LOGIN ---
def test_login_devuelve_un_token(client: TestClient, admin: Usuario) -> None:
    respuesta = client.post(
        "/api/v1/auth/login", data={"username": admin.email, "password": CLAVE_ADMIN}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["access_token"]


def test_login_con_contrasena_incorrecta_devuelve_401(client: TestClient, admin: Usuario) -> None:
    respuesta = client.post(
        "/api/v1/auth/login", data={"username": admin.email, "password": "noEsLaClave1"}
    )

    assert respuesta.status_code == 401


def test_email_inexistente_da_el_mismo_error_que_clave_mala(
    client: TestClient, admin: Usuario
) -> None:
    """No debe poder distinguirse: si no, se pueden enumerar los emails."""
    inexistente = client.post(
        "/api/v1/auth/login", data={"username": "nadie@gym.local", "password": "loQueSea1"}
    )
    clave_mala = client.post(
        "/api/v1/auth/login", data={"username": admin.email, "password": "noEsLaClave1"}
    )

    assert inexistente.status_code == clave_mala.status_code == 401
    assert inexistente.json()["detail"] == clave_mala.json()["detail"]


def test_usuario_inactivo_no_puede_entrar(
    client: TestClient, admin: Usuario, session: Session
) -> None:
    admin.activo = False
    session.add(admin)
    session.commit()

    respuesta = client.post(
        "/api/v1/auth/login", data={"username": admin.email, "password": CLAVE_ADMIN}
    )

    assert respuesta.status_code == 403


# --- ACCESO A RECURSOS PROTEGIDOS ---
def test_sin_token_no_se_entra(client: TestClient) -> None:
    assert client.get(PROTEGIDO).status_code == 401


def test_con_token_valido_se_entra(client_recepcion: TestClient) -> None:
    assert client_recepcion.get(PROTEGIDO).status_code == 200


def test_token_manipulado_se_rechaza(client_recepcion: TestClient) -> None:
    token = client_recepcion.headers["Authorization"].split()[1]
    client_recepcion.headers["Authorization"] = f"Bearer {token[:-2]}xx"

    assert client_recepcion.get(PROTEGIDO).status_code == 401


def test_token_expirado_se_rechaza(client: TestClient, admin: Usuario) -> None:
    vencido = crear_token_acceso(admin.id, admin.rol.value, expira_en=timedelta(minutes=-1))
    client.headers["Authorization"] = f"Bearer {vencido}"

    assert client.get(PROTEGIDO).status_code == 401


def test_token_de_un_usuario_borrado_se_rechaza(
    client_recepcion: TestClient, recepcion: Usuario, session: Session
) -> None:
    session.delete(recepcion)
    session.commit()

    assert client_recepcion.get(PROTEGIDO).status_code == 401


def test_dar_de_baja_invalida_el_token_al_instante(
    client_recepcion: TestClient, recepcion: Usuario, session: Session
) -> None:
    """El rol y el estado se releen de la base, no se creen del token."""
    assert client_recepcion.get(PROTEGIDO).status_code == 200

    recepcion.activo = False
    session.add(recepcion)
    session.commit()

    assert client_recepcion.get(PROTEGIDO).status_code == 403


# --- ROLES ---
def test_recepcion_no_administra_usuarios(client_recepcion: TestClient) -> None:
    assert client_recepcion.get("/api/v1/usuarios/").status_code == 403


def test_admin_si_administra_usuarios(client_admin: TestClient) -> None:
    assert client_admin.get("/api/v1/usuarios/").status_code == 200


# --- QUIEN SOY ---
def test_yo_devuelve_al_portador_sin_el_hash(client_admin: TestClient, admin: Usuario) -> None:
    respuesta = client_admin.get("/api/v1/auth/yo")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["email"] == admin.email
    assert "hashed_password" not in cuerpo


def test_yo_sin_token_devuelve_401(client: TestClient) -> None:
    assert client.get("/api/v1/auth/yo").status_code == 401


def test_los_healthchecks_siguen_abiertos(client: TestClient) -> None:
    """Si exigieran token, Docker no podria comprobar si el API esta sano."""
    assert client.get("/health").status_code == 200
