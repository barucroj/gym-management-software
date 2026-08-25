"""Motor y sesion de base de datos."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from gym_core.config import core_settings

engine = create_engine(core_settings.DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Entrega una sesion y la cierra al terminar.

    En FastAPI se usa como dependencia; en el notifier, como context manager.
    """
    with Session(engine) as session:
        yield session
