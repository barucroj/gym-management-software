"""Endpoints de los planes de membresia."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from gym_core.db import get_session
from gym_core.models.plan import Plan

router = APIRouter()


def _nombre_ya_usado(session: Session, nombre: str) -> bool:
    return session.exec(select(Plan).where(Plan.nombre == nombre)).first() is not None


@router.get("/", response_model=list[PlanRead])
def listar_planes(session: Session = Depends(get_session)):
    return session.exec(select(Plan)).all()


@router.get("/{plan_id}", response_model=PlanRead)
def obtener_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    return plan


@router.post("/", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def crear_plan(datos: PlanCreate, session: Session = Depends(get_session)):
    # nombre es unique en la tabla: sin esta comprobacion el duplicado sale
    # como 500 al hacer commit.
    if _nombre_ya_usado(session, datos.nombre):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un plan con ese nombre"
        )

    plan = Plan(**datos.model_dump())
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


@router.put("/{plan_id}", response_model=PlanRead)
def actualizar_plan(plan_id: int, datos: PlanUpdate, session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")

    cambios = datos.model_dump(exclude_unset=True)

    nombre_nuevo = cambios.get("nombre")
    if nombre_nuevo and nombre_nuevo != plan.nombre and _nombre_ya_usado(session, nombre_nuevo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un plan con ese nombre"
        )

    for campo, valor in cambios.items():
        setattr(plan, campo, valor)

    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")

    # Un plan vendido no se borra: el historial de suscripciones lo referencia
    # y el precio pagado dejaria de poder explicarse. Se retira con activo=false.
    if plan.suscripciones:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El plan tiene suscripciones: retirarlo con activo=false",
        )

    session.delete(plan)
    session.commit()
    return None
