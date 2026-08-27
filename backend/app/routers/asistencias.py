from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from gym_core.db import engine
from gym_core.models.asistencia import Asistencia

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/", response_model=list[Asistencia])
def listar_asistencias(session: Session = Depends(get_session)):
    return session.exec(select(Asistencia)).all()

@router.get("/{asistencia_id}", response_model=Asistencia)
def obtener_asistencia(asistencia_id: int, session: Session = Depends(get_session)):
    asistencia = session.get(Asistencia, asistencia_id)
    if not asistencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada")
    return asistencia

@router.post("/", response_model=Asistencia, status_code=status.HTTP_201_CREATED)
def registrar_asistencia(asistencia: Asistencia, session: Session = Depends(get_session)):
    session.add(asistencia)
    session.commit()
    session.refresh(asistencia)
    return asistencia

@router.put("/{asistencia_id}", response_model=Asistencia)
def actualizar_asistencia(asistencia_id: int, datos_nuevos: Asistencia, session: Session = Depends(get_session)):
    asistencia_db = session.get(Asistencia, asistencia_id)
    if not asistencia_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada")
    
    asistencia_data = datos_nuevos.model_dump(exclude_unset=True)
    for key, value in asistencia_data.items():
        if key != "id":
            setattr(asistencia_db, key, value)
            
    session.add(asistencia_db)
    session.commit()
    session.refresh(asistencia_db)
    return asistencia_db

@router.delete("/{asistencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asistencia(asistencia_id: int, session: Session = Depends(get_session)):
    asistencia = session.get(Asistencia, asistencia_id)
    if not asistencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada")
    
    session.delete(asistencia)
    session.commit()
    return None