"""Registro de entrada de un miembro al gimnasio."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from gym_core.models.miembro import Miembro


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Asistencia(SQLModel, table=True):
    __tablename__ = "asistencias"

    id: int | None = Field(default=None, primary_key=True)
    miembro_id: int = Field(foreign_key="miembros.id", index=True)

    # Instante del check-in. A diferencia de las vigencias (que son fechas de
    # calendario), aqui interesa la hora, asi que se guarda como datetime UTC.
    registrada_en: datetime = Field(
        default_factory=_ahora,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )

    # Suscripcion vigente al momento del ingreso, si la habia. Es opcional
    # a proposito: permite registrar la entrada de alguien sin suscripcion
    # activa en vez de perder el dato.
    suscripcion_id: int | None = Field(
        default=None, foreign_key="suscripciones.id", index=True
    )

    # Quien atendio el check-in. Lo pone el API con el usuario del token, no el
    # cliente: si viniera del cuerpo de la peticion, cualquiera podria anotar
    # entradas a nombre de otro y la auditoria no valdria nada.
    #
    # Nullable porque las asistencias anteriores a esta columna se registraron
    # cuando el dato no se pedia.
    usuario_id: int | None = Field(
        default=None, foreign_key="usuarios.id", index=True
    )

    miembro: "Miembro" = Relationship(back_populates="asistencias")
