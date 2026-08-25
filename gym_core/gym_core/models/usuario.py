"""Personal que opera el sistema (no son los miembros del gimnasio)."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from gym_core.enums import RolUsuario


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120)
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    rol: RolUsuario = Field(default=RolUsuario.RECEPCION)
    activo: bool = Field(default=True)
    creado_en: datetime = Field(default_factory=_ahora)
