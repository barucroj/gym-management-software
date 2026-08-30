"""Miembro del gimnasio."""

from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from gym_core.models.asistencia import Asistencia
    from gym_core.models.suscripcion import Suscripcion


class Miembro(SQLModel, table=True):
    __tablename__ = "miembros"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120, index=True)
    apellidos: str = Field(max_length=120, index=True)
    email: str | None = Field(default=None, max_length=255, index=True)
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = Field(default=None)
    fecha_registro: date = Field(default_factory=date.today)
    # Baja logica: se conserva el historial de asistencias y suscripciones.
    activo: bool = Field(default=True)
    # Cuando y por que se fue. activo solo dice cuantos hay de baja hoy; sin la
    # fecha no se puede calcular cuantos se van cada mes. Las mantiene el API al
    # cambiar activo, no el cliente.
    fecha_baja: date | None = Field(default=None)
    motivo_baja: str | None = Field(default=None, max_length=255)
    notas: str | None = Field(default=None)

    suscripciones: list["Suscripcion"] = Relationship(back_populates="miembro")
    asistencias: list["Asistencia"] = Relationship(back_populates="miembro")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}".strip()
