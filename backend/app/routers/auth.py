"""Emision de tokens. Es el unico router que NO exige estar autenticado."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.security import crear_token_acceso, verify_password
from app.schemas.auth import Token
from app.schemas.usuario import UsuarioRead
from gym_core.db import get_session
from gym_core.models.usuario import Usuario

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    formulario: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Valida credenciales y devuelve un token.

    OAuth2PasswordRequestForm recibe los datos como formulario, no como JSON.
    Es lo que exige el estandar y lo que usa el boton "Authorize" de /docs.
    El campo se llama "username" por el estandar, pero aqui lleva el email.
    """
    usuario = session.exec(
        select(Usuario).where(Usuario.email == formulario.username)
    ).first()

    # Mismo error para "no existe" y "contrasena incorrecta": si fueran
    # distintos, cualquiera podria averiguar que emails estan registrados
    # probando el login uno por uno.
    if usuario is None or not verify_password(formulario.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo"
        )

    return Token(access_token=crear_token_acceso(usuario.id, usuario.rol.value))


@router.get("/yo", response_model=UsuarioRead)
def usuario_actual(usuario: Usuario = Depends(get_current_user)):
    """Devuelve quien es el portador del token.

    El frontend lo usa al arrancar para saber si su token guardado sigue
    sirviendo y con que rol, sin tener que decodificarlo por su cuenta.
    """
    return usuario
