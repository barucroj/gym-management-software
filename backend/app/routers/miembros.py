from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from gym_core.db import engine
from gym_core.models.miembro import Miembro

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/", response_model=list[Miembro])
def listar_miembros(session: Session = Depends(get_session)):
    return session.exec(select(Miembro)).all()

@router.get("/{miembro_id}", response_model=Miembro)
def obtener_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    return miembro

@router.post("/", response_model=Miembro, status_code=status.HTTP_201_CREATED)
def crear_miembro(miembro: Miembro, session: Session = Depends(get_session)):
    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro

@router.put("/{miembro_id}", response_model=Miembro)
def actualizar_miembro(miembro_id: int, datos_nuevos: Miembro, session: Session = Depends(get_session)):
    miembro_db = session.get(Miembro, miembro_id)
    if not miembro_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    
    miembro_data = datos_nuevos.model_dump(exclude_unset=True)
    for key, value in miembro_data.items():
        if key != "id":
            setattr(miembro_db, key, value)
            
    session.add(miembro_db)
    session.commit()
    session.refresh(miembro_db)
    return miembro_db

@router.delete("/{miembro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    
    session.delete(miembro)
    session.commit()
    return None