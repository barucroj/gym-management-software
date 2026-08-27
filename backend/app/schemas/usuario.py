"""Contratos de entrada y salida del recurso usuarios.

Separados a proposito del modelo de tabla gym_core.models.Usuario: el modelo
describe COMO SE GUARDA en Postgres, estos schemas describen QUE SE ACEPTA y
QUE SE DEVUELVE. hashed_password no aparece en ninguno de los tres.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from gym_core.enums import RolUsuario

# bcrypt ignora en silencio todo lo que pase de 72 bytes, asi que se rechaza
# antes en lugar de recortar la contrasena sin avisar.
_MAX_PASSWORD = 72
_MIN_PASSWORD = 8


class UsuarioCreate(BaseModel):
    """Alta de usuario: recibe la contrasena en claro y el API la hashea.

    No declara id ni creado_en: los asigna la base de datos, no el cliente.
    """

    nombre: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=_MIN_PASSWORD, max_length=_MAX_PASSWORD)
    rol: RolUsuario = RolUsuario.RECEPCION
    activo: bool = True


class UsuarioUpdate(BaseModel):
    """Actualizacion parcial: todo opcional, solo se aplica lo que llega."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    password: str | None = Field(
        default=None, min_length=_MIN_PASSWORD, max_length=_MAX_PASSWORD
    )
    rol: RolUsuario | None = None
    activo: bool | None = None


class UsuarioRead(BaseModel):
    """Lo unico que el API devuelve de un usuario.

    Un campo se filtra por omision, no por prohibicion: si manana el modelo
    gana una columna sensible, no se publica sola, hay que agregarla aqui.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: RolUsuario
    activo: bool
    creado_en: datetime
