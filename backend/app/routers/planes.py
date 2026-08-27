from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from gym_core.db import engine
from gym_core.models.plan import Plan

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/", response_model=list[Plan])
def listar_planes(session: Session = Depends(get_session)):
    return session.exec(select(Plan)).all()

@router.get("/{plan_id}", response_model=Plan)
def obtener_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    return plan

@router.post("/", response_model=Plan, status_code=status.HTTP_201_CREATED)
def crear_plan(plan: Plan, session: Session = Depends(get_session)):
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan

@router.put("/{plan_id}", response_model=Plan)
def actualizar_plan(plan_id: int, datos_nuevos: Plan, session: Session = Depends(get_session)):
    plan_db = session.get(Plan, plan_id)
    if not plan_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    
    plan_data = datos_nuevos.model_dump(exclude_unset=True)
    for key, value in plan_data.items():
        if key != "id":
            setattr(plan_db, key, value)
            
    session.add(plan_db)
    session.commit()
    session.refresh(plan_db)
    return plan_db

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    
    session.delete(plan)
    session.commit()
    return None