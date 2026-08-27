"""Dependencias de autenticacion y autorizacion.

Se declaran una sola vez y se aplican al montar los routers en main.py, para
que proteger un endpoint no dependa de acordarse de escribir un if adentro.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.security import decodificar_token
from gym_core.db import get_session
from gym_core.enums import RolUsuario
from gym_core.models.usuario import Usuario

# tokenUrl es informativo: le dice a Swagger UI adonde pedir el token para
# que el boton "Authorize" de /docs funcione solo.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _no_autorizado() -> HTTPException:
    # WWW-Authenticate es parte del contrato del 401: le dice al cliente que
    # tipo de credencial se espera.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Usuario:
    """Traduce el token a un usuario real, o corta la peticion con 401."""
    payload = decodificar_token(token)
    if payload is None:
        raise _no_autorizado()

    sub = payload.get("sub")
    try:
        usuario_id = int(sub)
    except (TypeError, ValueError):
        raise _no_autorizado()

    # Se relee de la base en cada peticion a proposito. El token lleva el rol
    # adentro, pero fue congelado al emitirse: si al usuario lo dan de baja o
    # le cambian el rol, el token seguiria diciendo lo viejo hasta expirar.
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise _no_autorizado()

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo"
        )
    return usuario


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Restringe un router a los administradores.

    401 y 403 no son lo mismo: 401 es "no se quien sos", 403 es "se quien sos
    y no te alcanza". Devolver 401 aqui haria que el cliente pidiera login de
    nuevo sin necesidad.
    """
    if usuario.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return usuario
