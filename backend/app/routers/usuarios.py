"""Endpoints del personal que opera el sistema.

Ningun endpoint devuelve hashed_password ni lo acepta como entrada: la
contrasena entra en claro por UsuarioCreate/UsuarioUpdate y se hashea aqui.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.security import hash_password
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from gym_core.db import get_session
from gym_core.models.usuario import Usuario

router = APIRouter()


def _email_ya_registrado(session: Session, email: str) -> bool:
    return session.exec(select(Usuario).where(Usuario.email == email)).first() is not None


# 1. LISTAR TODOS
@router.get("/", response_model=list[UsuarioRead])
def listar_usuarios(session: Session = Depends(get_session)):
    return session.exec(select(Usuario)).all()


# 2. OBTENER UN USUARIO POR ID
@router.get("/{usuario_id}", response_model=UsuarioRead)
def obtener_usuario(usuario_id: int, session: Session = Depends(get_session)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


# 3. CREAR USUARIO
@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCreate, session: Session = Depends(get_session)):
    # El email es unique en la tabla: sin esta comprobacion, un duplicado
    # revienta en el commit con un IntegrityError y sale como 500.
    if _email_ya_registrado(session, datos.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El email ya esta registrado"
        )

    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        hashed_password=hash_password(datos.password),
        rol=datos.rol,
        activo=datos.activo,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# 4. ACTUALIZAR USUARIO
@router.put("/{usuario_id}", response_model=UsuarioRead)
def actualizar_usuario(
    usuario_id: int, datos: UsuarioUpdate, session: Session = Depends(get_session)
):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # exclude_unset distingue "no lo mando" de "lo mando en null".
    cambios = datos.model_dump(exclude_unset=True)

    password = cambios.pop("password", None)
    if password is not None:
        usuario.hashed_password = hash_password(password)

    email_nuevo = cambios.get("email")
    if email_nuevo and email_nuevo != usuario.email and _email_ya_registrado(session, email_nuevo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El email ya esta registrado"
        )

    # Ya no hace falta filtrar "id" a mano: UsuarioUpdate simplemente no lo tiene.
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# 5. ELIMINAR USUARIO
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, session: Session = Depends(get_session)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    session.delete(usuario)
    session.commit()
    return None
