"""Contratos del recurso de autenticacion."""

from pydantic import BaseModel


class Token(BaseModel):
    """Respuesta del login, en el formato que espera OAuth2."""

    access_token: str
    token_type: str = "bearer"
