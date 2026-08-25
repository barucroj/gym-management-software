"""Plan de membresia: define duracion y precio de una suscripcion."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from gym_core.models.suscripcion import Suscripcion


class Plan(SQLModel, table=True):
    __tablename__ = "planes"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=80, unique=True, index=True)
    descripcion: str | None = Field(default=None)
    duracion_dias: int = Field(gt=0)
    precio: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    # Permite retirar un plan de la oferta sin borrar las suscripciones que lo usaron.
    activo: bool = Field(default=True)

    suscripciones: list["Suscripcion"] = Relationship(back_populates="plan")
