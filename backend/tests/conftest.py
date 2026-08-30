"""Fixtures compartidas por la suite del API.

Casi toda la suite corre sobre SQLite en memoria: lo que prueba es el contrato
HTTP y las reglas de autorizacion, nada que dependa de PostgreSQL, y hacerlo
sin servidor la mantiene rapida.

La excepcion es la busqueda de socios, que se apoya en pg_trgm. Para eso estan
las fixtures *_pg del final del archivo.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import hash_password
from app.main import app
from gym_core.config import core_settings
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


# ---------------------------------------------------------------
# PostgreSQL real, solo para lo que SQLite no puede expresar
# ---------------------------------------------------------------

BASE_DE_PRUEBA = "gymdb_test"


def _ruta_alembic() -> Path:
    """Busca gym_core/alembic.ini hacia arriba: vale en el repo y en la imagen."""
    for base in Path(__file__).resolve().parents:
        candidato = base / "gym_core" / "alembic.ini"
        if candidato.exists():
            return candidato
    pytest.skip("No se encontro gym_core/alembic.ini")


def _migrar(url) -> None:
    """Aplica las migraciones sobre `url`.

    env.py toma la URL de core_settings y pisa la de alembic.ini a proposito,
    para no versionar credenciales. La unica forma de apuntarlo a otra base es
    cambiar el ajuste mientras dura la llamada.
    """
    original = core_settings.DATABASE_URL
    core_settings.DATABASE_URL = url.render_as_string(hide_password=False)
    try:
        command.upgrade(Config(str(_ruta_alembic())), "head")
    finally:
        core_settings.DATABASE_URL = original


@pytest.fixture(scope="session", name="engine_pg")
def engine_pg_fixture():
    """Motor sobre PostgreSQL, en una base desechable creada al vuelo.

    El esquema lo levanta Alembic y no SQLModel.metadata.create_all: asi estos
    tests verifican tambien que la migracion deja creados el indice GIN y la
    funcion gym_normalizar de los que depende la busqueda. Con create_all no
    existirian y el fallo aparecería recien en produccion.

    Si no hay PostgreSQL a mano, los tests que la usan se saltan en vez de
    fallar: la suite tiene que seguir corriendo sin levantar la base.
    """
    url = make_url(core_settings.DATABASE_URL)
    if not url.get_backend_name().startswith("postgresql"):
        pytest.skip("DATABASE_URL no apunta a PostgreSQL")

    # WITH (FORCE) corta las conexiones que hayan quedado de una corrida
    # anterior interrumpida; sin eso, el DROP se queda esperando.
    mantenimiento = sa_create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    borrar = f'DROP DATABASE IF EXISTS "{BASE_DE_PRUEBA}" WITH (FORCE)'
    try:
        with mantenimiento.connect() as conexion:
            conexion.exec_driver_sql(borrar)
            conexion.exec_driver_sql(f'CREATE DATABASE "{BASE_DE_PRUEBA}"')
    except OperationalError as error:
        pytest.skip(f"No hay un PostgreSQL accesible: {error}")

    url_prueba = url.set(database=BASE_DE_PRUEBA)
    _migrar(url_prueba)
    engine = create_engine(url_prueba)
    try:
        yield engine
    finally:
        engine.dispose()
        with mantenimiento.connect() as conexion:
            conexion.exec_driver_sql(borrar)
        mantenimiento.dispose()


@pytest.fixture(name="session_pg")
def session_pg_fixture(engine_pg):
    """Sesion sobre PostgreSQL que no deja rastro.

    Todo ocurre dentro de una transaccion externa que se revierte al terminar.
    Los commit de la propia prueba caen en un savepoint, asi que el rollback
    final los alcanza igual y cada test arranca con la base vacia.
    """
    conexion = engine_pg.connect()
    transaccion = conexion.begin()
    try:
        with Session(bind=conexion) as session:
            yield session
    finally:
        transaccion.rollback()
        conexion.close()


@pytest.fixture(name="client_pg_recepcion")
def client_pg_recepcion_fixture(session_pg: Session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session_pg
    cliente = TestClient(app)
    usuario = _crear_usuario(session_pg, "recep@gym.local", CLAVE_RECEPCION, RolUsuario.RECEPCION)

    yield autenticar(cliente, usuario.email, CLAVE_RECEPCION)

    app.dependency_overrides.clear()
