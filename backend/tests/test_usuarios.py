"""Tests del recurso usuarios.

Corren contra SQLite en memoria: lo que se verifica es el contrato HTTP y el
hasheo, nada que dependa de PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.security import verify_password
from app.main import app
from app.routers.usuarios import get_session
from gym_core.enums import RolUsuario
from gym_core.models.usuario import Usuario

ALTA = {
    "nombre": "Ada Lovelace",
    "email": "ada@gym.local",
    "password": "unaClaveLarga1",
}


@pytest.fixture(name="session")
def session_fixture():
    # StaticPool + check_same_thread: TestClient atiende en otro hilo y sin
    # esto veria una base en memoria distinta (vacia).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_crear_usuario_no_devuelve_el_hash(client: TestClient) -> None:
    respuesta = client.post("/api/v1/usuarios/", json=ALTA)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert "hashed_password" not in cuerpo
    assert "password" not in cuerpo
    assert cuerpo["email"] == "ada@gym.local"


def test_la_contrasena_se_guarda_hasheada(client: TestClient, session: Session) -> None:
    client.post("/api/v1/usuarios/", json=ALTA)

    usuario = session.exec(select(Usuario)).one()
    assert usuario.hashed_password != ALTA["password"]
    assert verify_password(ALTA["password"], usuario.hashed_password)


def test_listar_usuarios_no_expone_hashes(client: TestClient) -> None:
    client.post("/api/v1/usuarios/", json=ALTA)

    respuesta = client.get("/api/v1/usuarios/")

    assert respuesta.status_code == 200
    assert "hashed_password" not in respuesta.text


def test_obtener_usuario_no_expone_el_hash(client: TestClient) -> None:
    creado = client.post("/api/v1/usuarios/", json=ALTA).json()

    respuesta = client.get(f"/api/v1/usuarios/{creado['id']}")

    assert respuesta.status_code == 200
    assert "hashed_password" not in respuesta.json()


def test_email_duplicado_devuelve_409(client: TestClient) -> None:
    client.post("/api/v1/usuarios/", json=ALTA)

    respuesta = client.post("/api/v1/usuarios/", json={**ALTA, "nombre": "Otra"})

    assert respuesta.status_code == 409


def test_el_cliente_no_puede_imponer_el_id(client: TestClient) -> None:
    """UsuarioCreate no declara id, asi que pydantic lo descarta."""
    respuesta = client.post("/api/v1/usuarios/", json={**ALTA, "id": 999})

    assert respuesta.json()["id"] != 999


def test_alta_sin_rol_queda_en_recepcion(client: TestClient) -> None:
    respuesta = client.post("/api/v1/usuarios/", json=ALTA)

    assert respuesta.json()["rol"] == RolUsuario.RECEPCION.value


def test_contrasena_corta_se_rechaza(client: TestClient) -> None:
    respuesta = client.post("/api/v1/usuarios/", json={**ALTA, "password": "corta"})

    assert respuesta.status_code == 422


def test_actualizar_contrasena_la_vuelve_a_hashear(client: TestClient, session: Session) -> None:
    creado = client.post("/api/v1/usuarios/", json=ALTA).json()
    hash_inicial = session.exec(select(Usuario)).one().hashed_password

    respuesta = client.put(
        f"/api/v1/usuarios/{creado['id']}", json={"password": "otraClaveLarga1"}
    )

    assert respuesta.status_code == 200
    session.expire_all()
    hash_nuevo = session.exec(select(Usuario)).one().hashed_password
    assert hash_nuevo != hash_inicial
    assert verify_password("otraClaveLarga1", hash_nuevo)


def test_actualizar_a_un_email_ocupado_devuelve_409(client: TestClient) -> None:
    primero = client.post("/api/v1/usuarios/", json=ALTA).json()
    client.post("/api/v1/usuarios/", json={**ALTA, "email": "otro@gym.local"})

    respuesta = client.put(
        f"/api/v1/usuarios/{primero['id']}", json={"email": "otro@gym.local"}
    )

    assert respuesta.status_code == 409


def test_usuario_inexistente_devuelve_404(client: TestClient) -> None:
    assert client.get("/api/v1/usuarios/404").status_code == 404
    assert client.put("/api/v1/usuarios/404", json={"nombre": "X"}).status_code == 404
    assert client.delete("/api/v1/usuarios/404").status_code == 404
