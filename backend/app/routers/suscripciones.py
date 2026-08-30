"""Endpoints de las suscripciones (la vigencia que un miembro compra)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.schemas.suscripcion import SuscripcionCreate, SuscripcionRead, SuscripcionUpdate
from gym_core.db import get_session
from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan
from gym_core.models.suscripcion import Suscripcion

router = APIRouter()


def _verificar_referencias(session: Session, miembro_id: int | None, plan_id: int | None) -> None:
    """Comprueba las claves foraneas antes de tocar la base.

    Sin esto, un id inexistente falla recien en el commit con un
    IntegrityError, que sale como 500 en lugar de como error del cliente.
    """
    if miembro_id is not None and session.get(Miembro, miembro_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe el miembro {miembro_id}",
        )
    if plan_id is not None and session.get(Plan, plan_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe el plan {plan_id}",
        )


@router.get("/", response_model=list[SuscripcionRead])
def listar_suscripciones(session: Session = Depends(get_session)):
    return [SuscripcionRead.desde(s) for s in session.exec(select(Suscripcion)).all()]


@router.get("/{suscripcion_id}", response_model=SuscripcionRead)
def obtener_suscripcion(suscripcion_id: int, session: Session = Depends(get_session)):
    suscripcion = session.get(Suscripcion, suscripcion_id)
    if not suscripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suscripcion no encontrada"
        )
    return SuscripcionRead.desde(suscripcion)


def _verificar_renovacion(session: Session, miembro_id: int, renovada_de_id: int | None) -> None:
    """Comprueba que la suscripcion que se dice renovar exista y encaje.

    Sin esta validacion el enlace podria apuntar a la suscripcion de otro
    socio, y la tasa de renovacion que se calcule despues seria ficcion.
    """
    if renovada_de_id is None:
        return

    anterior = session.get(Suscripcion, renovada_de_id)
    if anterior is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe la suscripcion {renovada_de_id}",
        )
    if anterior.miembro_id != miembro_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La suscripcion que se renueva es de otro miembro",
        )

    # La base tiene un unique sobre renovada_de_id, pero llegar hasta el commit
    # devolveria un 500. Un segundo intento de renovar lo mismo es un conflicto
    # del cliente, no un error del servidor.
    ya_renovada = session.exec(
        select(Suscripcion).where(Suscripcion.renovada_de_id == renovada_de_id)
    ).first()
    if ya_renovada is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La suscripcion {renovada_de_id} ya fue renovada por la {ya_renovada.id}",
        )


@router.post("/", response_model=SuscripcionRead, status_code=status.HTTP_201_CREATED)
def crear_suscripcion(datos: SuscripcionCreate, session: Session = Depends(get_session)):
    _verificar_referencias(session, datos.miembro_id, datos.plan_id)
    _verificar_renovacion(session, datos.miembro_id, datos.renovada_de_id)

    suscripcion = Suscripcion(**datos.model_dump())
    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)
    return SuscripcionRead.desde(suscripcion)


@router.put("/{suscripcion_id}", response_model=SuscripcionRead)
def actualizar_suscripcion(
    suscripcion_id: int, datos: SuscripcionUpdate, session: Session = Depends(get_session)
):
    suscripcion = session.get(Suscripcion, suscripcion_id)
    if not suscripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suscripcion no encontrada"
        )

    cambios = datos.model_dump(exclude_unset=True)
    _verificar_referencias(session, cambios.get("miembro_id"), cambios.get("plan_id"))

    # Si solo llega una de las dos fechas, la coherencia hay que verificarla
    # contra la que ya esta guardada: el schema no puede compararlas solo.
    inicio = cambios.get("fecha_inicio", suscripcion.fecha_inicio)
    fin = cambios.get("fecha_fin", suscripcion.fecha_fin)
    if fin < inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_fin no puede ser anterior a fecha_inicio",
        )

    for campo, valor in cambios.items():
        setattr(suscripcion, campo, valor)

    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)
    return SuscripcionRead.desde(suscripcion)


@router.delete("/{suscripcion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_suscripcion(suscripcion_id: int, session: Session = Depends(get_session)):
    suscripcion = session.get(Suscripcion, suscripcion_id)
    if not suscripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suscripcion no encontrada"
        )

    # Las asistencias registradas apuntan a esta suscripcion: borrarla dejaria
    # el historial de entradas sin explicacion.
    tiene_asistencias = session.exec(
        select(Asistencia).where(Asistencia.suscripcion_id == suscripcion_id)
    ).first()
    if tiene_asistencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La suscripcion tiene asistencias registradas y no puede eliminarse",
        )

    session.delete(suscripcion)
    session.commit()
    return None
