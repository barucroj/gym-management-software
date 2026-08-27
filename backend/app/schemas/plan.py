"""Contratos de entrada y salida del recurso planes."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = None
    # Las mismas restricciones que la tabla: un plan de cero dias o de precio
    # negativo no tiene sentido, y conviene rechazarlo antes de llegar a la base.
    duracion_dias: int = Field(gt=0)
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    activo: bool = True


class PlanUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = None
    duracion_dias: int | None = Field(default=None, gt=0)
    precio: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    activo: bool | None = None


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    duracion_dias: int
    precio: Decimal
    activo: bool
