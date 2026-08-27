"""Fixtures compartidas por la suite del API.

La base es SQLite en memoria: lo que se prueba es el contrato HTTP y las
reglas de autorizacion, nada que dependa de PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import hash_password
from app.main import app
from gym_core.db import get_session
from gym_core.enums import RolUsuario
from gym_core.models.usuario import Usuario

CLAVE_ADMIN = "claveDelAdmin1"
CLAVE_RECEPCION = "claveRecepcion1"


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
    """Cliente HTTP sin autenticar, con la base en memoria enchufada.

    Una sola linea alcanza porque todos los routers dependen del mismo
    get_session de gym_core. FastAPI identifica cada dependencia por el objeto
    funcion, asi que mientras haya una sola funcion hay una sola cosa que
    sustituir.
    """
    app.dependency_overrides[get_session] = lambda: session

    yield TestClient(app)

    app.dependency_overrides.clear()


def _crear_usuario(session: Session, email: str, clave: str, rol: RolUsuario) -> Usuario:
    usuario = Usuario(
        nombre=email.split("@")[0],
        email=email,
        hashed_password=hash_password(clave),
        rol=rol,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@pytest.fixture(name="admin")
def admin_fixture(session: Session) -> Usuario:
    return _crear_usuario(session, "admin@gym.local", CLAVE_ADMIN, RolUsuario.ADMIN)


@pytest.fixture(name="recepcion")
def recepcion_fixture(session: Session) -> Usuario:
    return _crear_usuario(session, "recep@gym.local", CLAVE_RECEPCION, RolUsuario.RECEPCION)


def autenticar(client: TestClient, email: str, clave: str) -> TestClient:
    """Hace login de verdad y deja el token puesto en el cliente.

    Se usa el login real en vez de sobrescribir la dependencia para que los
    tests de los recursos tambien recorran el camino de autenticacion.
    """
    respuesta = client.post("/api/v1/auth/login", data={"username": email, "password": clave})
    assert respuesta.status_code == 200, respuesta.text
    client.headers["Authorization"] = f"Bearer {respuesta.json()['access_token']}"
    return client


@pytest.fixture(name="client_admin")
def client_admin_fixture(client: TestClient, admin: Usuario) -> TestClient:
    return autenticar(client, admin.email, CLAVE_ADMIN)


@pytest.fixture(name="client_recepcion")
def client_recepcion_fixture(client: TestClient, recepcion: Usuario) -> TestClient:
    return autenticar(client, recepcion.email, CLAVE_RECEPCION)
