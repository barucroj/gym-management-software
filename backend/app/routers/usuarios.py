from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from gym_core.db import engine
from gym_core.models.usuario import Usuario

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

# 1. LISTAR TODOS
@router.get("/", response_model=list[Usuario])
def listar_usuarios(session: Session = Depends(get_session)):
    return session.exec(select(Usuario)).all()

# 2. OBTENER UN USUARIO POR ID
@router.get("/{usuario_id}", response_model=Usuario)
def obtener_usuario(usuario_id: int, session: Session = Depends(get_session)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario

# 3. CREAR USUARIO
@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def crear_usuario(usuario: Usuario, session: Session = Depends(get_session)):
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

# 4. ACTUALIZAR USUARIO
@router.put("/{usuario_id}", response_model=Usuario)
def actualizar_usuario(usuario_id: int, datos_nuevos: Usuario, session: Session = Depends(get_session)):
    usuario_db = session.get(Usuario, usuario_id)
    if not usuario_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    usuario_data = datos_nuevos.model_dump(exclude_unset=True)
    for key, value in usuario_data.items():
        if key != "id":
            setattr(usuario_db, key, value)
            
    session.add(usuario_db)
    session.commit()
    session.refresh(usuario_db)
    return usuario_db

# 5. ELIMINAR USUARIO
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, session: Session = Depends(get_session)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    session.delete(usuario)
    session.commit()
    return None