"""Crea el primer administrador del sistema.

Existe porque el recurso /usuarios exige rol admin: sin este comando no
habria forma de crear el primer administrador sin ser uno ya. Vive fuera del
API a proposito, para que no exista ningun endpoint capaz de hacerlo.

    docker compose run --rm \
      -e ADMIN_EMAIL=admin@gym.local \
      -e ADMIN_PASSWORD=una-clave-larga \
      api python -m app.cli.crear_admin

Es idempotente: si el email ya existe, no hace nada y sale sin error.
"""

import os
import sys

from sqlmodel import Session, select

from app.core.security import hash_password
from gym_core.db import engine
from gym_core.enums import RolUsuario
from gym_core.models.usuario import Usuario

_MIN_PASSWORD = 8


def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    nombre = os.getenv("ADMIN_NOMBRE", "Administrador").strip()

    if not email or not password:
        print("Faltan ADMIN_EMAIL y/o ADMIN_PASSWORD.", file=sys.stderr)
        return 1

    if len(password) < _MIN_PASSWORD:
        print(f"La contrasena debe tener al menos {_MIN_PASSWORD} caracteres.", file=sys.stderr)
        return 1

    with Session(engine) as session:
        existente = session.exec(select(Usuario).where(Usuario.email == email)).first()
        if existente is not None:
            print(f"El usuario {email} ya existe (id={existente.id}). Sin cambios.")
            return 0

        admin = Usuario(
            nombre=nombre,
            email=email,
            hashed_password=hash_password(password),
            rol=RolUsuario.ADMIN,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        print(f"Administrador creado: {admin.email} (id={admin.id})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
