"""Tests del recurso usuarios: el contrato de entrada/salida y el hasheo.

El acceso al recurso lo cubre test_auth.py; aqui se entra ya autenticado como
administrador para poder mirar el contrato en si.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import verify_password
from gym_core.enums import RolUsuario
from gym_core.models.usuario import Usuario

ALTA = {
    "nombre": "Ada Lovelace",
    "email": "ada@gym.local",
    "password": "unaClaveLarga1",
}


def _ada(session: Session) -> Usuario:
    return session.exec(select(Usuario).where(Usuario.email == ALTA["email"])).one()


def test_crear_usuario_no_devuelve_el_hash(client_admin: TestClient) -> None:
    respuesta = client_admin.post("/api/v1/usuarios/", json=ALTA)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert "hashed_password" not in cuerpo
    assert "password" not in cuerpo
    assert cuerpo["email"] == ALTA["email"]


def test_la_contrasena_se_guarda_hasheada(client_admin: TestClient, session: Session) -> None:
    client_admin.post("/api/v1/usuarios/", json=ALTA)

    usuario = _ada(session)
    assert usuario.hashed_password != ALTA["password"]
    assert verify_password(ALTA["password"], usuario.hashed_password)


def test_listar_usuarios_no_expone_hashes(client_admin: TestClient) -> None:
    client_admin.post("/api/v1/usuarios/", json=ALTA)

    respuesta = client_admin.get("/api/v1/usuarios/")

    assert respuesta.status_code == 200
    assert "hashed_password" not in respuesta.text


def test_obtener_usuario_no_expone_el_hash(client_admin: TestClient) -> None:
    creado = client_admin.post("/api/v1/usuarios/", json=ALTA).json()

    respuesta = client_admin.get(f"/api/v1/usuarios/{creado['id']}")

    assert respuesta.status_code == 200
    assert "hashed_password" not in respuesta.json()


def test_email_duplicado_devuelve_409(client_admin: TestClient) -> None:
    client_admin.post("/api/v1/usuarios/", json=ALTA)

    respuesta = client_admin.post("/api/v1/usuarios/", json={**ALTA, "nombre": "Otra"})

    assert respuesta.status_code == 409


def test_el_cliente_no_puede_imponer_el_id(client_admin: TestClient) -> None:
    """UsuarioCreate no declara id, asi que pydantic lo descarta."""
    respuesta = client_admin.post("/api/v1/usuarios/", json={**ALTA, "id": 999})

    assert respuesta.json()["id"] != 999


def test_alta_sin_rol_queda_en_recepcion(client_admin: TestClient) -> None:
    respuesta = client_admin.post("/api/v1/usuarios/", json=ALTA)

    assert respuesta.json()["rol"] == RolUsuario.RECEPCION.value


def test_email_invalido_se_rechaza(client_admin: TestClient) -> None:
    respuesta = client_admin.post("/api/v1/usuarios/", json={**ALTA, "email": "no-es-un-email"})

    assert respuesta.status_code == 422


def test_contrasena_corta_se_rechaza(client_admin: TestClient) -> None:
    respuesta = client_admin.post("/api/v1/usuarios/", json={**ALTA, "password": "corta"})

    assert respuesta.status_code == 422


def test_actualizar_contrasena_la_vuelve_a_hashear(
    client_admin: TestClient, session: Session
) -> None:
    creado = client_admin.post("/api/v1/usuarios/", json=ALTA).json()
    hash_inicial = _ada(session).hashed_password

    respuesta = client_admin.put(
        f"/api/v1/usuarios/{creado['id']}", json={"password": "otraClaveLarga1"}
    )

    assert respuesta.status_code == 200
    session.expire_all()
    hash_nuevo = _ada(session).hashed_password
    assert hash_nuevo != hash_inicial
    assert verify_password("otraClaveLarga1", hash_nuevo)


def test_actualizar_a_un_email_ocupado_devuelve_409(client_admin: TestClient) -> None:
    primero = client_admin.post("/api/v1/usuarios/", json=ALTA).json()
    client_admin.post("/api/v1/usuarios/", json={**ALTA, "email": "otro@gym.local"})

    respuesta = client_admin.put(
        f"/api/v1/usuarios/{primero['id']}", json={"email": "otro@gym.local"}
    )

    assert respuesta.status_code == 409


def test_usuario_inexistente_devuelve_404(client_admin: TestClient) -> None:
    assert client_admin.get("/api/v1/usuarios/404").status_code == 404
    assert client_admin.put("/api/v1/usuarios/404", json={"nombre": "X"}).status_code == 404
    assert client_admin.delete("/api/v1/usuarios/404").status_code == 404
