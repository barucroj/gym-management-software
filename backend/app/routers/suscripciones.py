from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from gym_core.db import engine
from gym_core.models.suscripcion import Suscripcion

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/", response_model=list[Suscripcion])
def listar_suscripciones(session: Session = Depends(get_session)):
    return session.exec(select(Suscripcion)).all()

@router.get("/{suscripcion_id}", response_model=Suscripcion)
def obtener_suscripcion(suscripcion_id: int, session: Session = Depends(get_session)):
    suscripcion = session.get(Suscripcion, suscripcion_id)
    if not suscripcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada")
    return suscripcion

@router.post("/", response_model=Suscripcion, status_code=status.HTTP_201_CREATED)
def crear_suscripcion(suscripcion: Suscripcion, session: Session = Depends(get_session)):
    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)
    return suscripcion

@router.put("/{suscripcion_id}", response_model=Suscripcion)
def actualizar_suscripcion(suscripcion_id: int, datos_nuevos: Suscripcion, session: Session = Depends(get_session)):
    suscripcion_db = session.get(Suscripcion, suscripcion_id)
    if not suscripcion_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada")
    
    suscripcion_data = datos_nuevos.model_dump(exclude_unset=True)
    for key, value in suscripcion_data.items():
        if key != "id":
            setattr(suscripcion_db, key, value)
            
    session.add(suscripcion_db)
    session.commit()
    session.refresh(suscripcion_db)
    return suscripcion_db

@router.delete("/{suscripcion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_suscripcion(suscripcion_id: int, session: Session = Depends(get_session)):
    suscripcion = session.get(Suscripcion, suscripcion_id)
    if not suscripcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada")
    
    session.delete(suscripcion)
    session.commit()
    return None