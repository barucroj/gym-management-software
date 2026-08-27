"""Endpoints de los miembros del gimnasio."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.schemas.miembro import MiembroCreate, MiembroRead, MiembroUpdate
from gym_core.db import get_session
from gym_core.models.miembro import Miembro

router = APIRouter()


@router.get("/", response_model=list[MiembroRead])
def listar_miembros(session: Session = Depends(get_session)):
    return session.exec(select(Miembro)).all()


@router.get("/{miembro_id}", response_model=MiembroRead)
def obtener_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    return miembro


@router.post("/", response_model=MiembroRead, status_code=status.HTTP_201_CREATED)
def crear_miembro(datos: MiembroCreate, session: Session = Depends(get_session)):
    miembro = Miembro(**datos.model_dump())
    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro


@router.put("/{miembro_id}", response_model=MiembroRead)
def actualizar_miembro(
    miembro_id: int, datos: MiembroUpdate, session: Session = Depends(get_session)
):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(miembro, campo, valor)

    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro


@router.delete("/{miembro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    # El modelo preve baja logica. Borrar de verdad a alguien con historial
    # violaria las claves foraneas de suscripciones y asistencias, y ademas
    # perderia datos que el gimnasio necesita conservar.
    if miembro.suscripciones or miembro.asistencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El miembro tiene historial: darlo de baja con activo=false",
        )

    session.delete(miembro)
    session.commit()
    return None
