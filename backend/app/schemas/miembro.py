"""Contratos de entrada y salida del recurso miembros."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tipos import Email


class MiembroCreate(BaseModel):
    """Alta de miembro.

    No declara fecha_registro ni activo: la primera la pone el modelo al
    insertar, y dar de baja es una operacion distinta de un alta.
    """

    nombre: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    email: Email | None = None
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None
    notas: str | None = None


class MiembroUpdate(BaseModel):
    """Actualizacion parcial. activo si esta: es como se da de baja."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellidos: str | None = Field(default=None, min_length=1, max_length=120)
    email: Email | None = None
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None
    activo: bool | None = None
    notas: str | None = None


class MiembroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellidos: str
    # Propiedad del modelo, no columna. Se expone para que cada pantalla no
    # tenga que concatenar nombre y apellidos por su cuenta.
    nombre_completo: str
    email: str | None
    telefono: str | None
    fecha_nacimiento: date | None
    fecha_registro: date
    activo: bool
    notas: str | None
