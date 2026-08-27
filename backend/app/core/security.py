"""Hashing de contrasenas y emision/verificacion de tokens JWT.

Aislado en su propio modulo a proposito: el login y los routers solo llaman
a estas funciones, asi que cambiar de algoritmo mas adelante se hace en un
unico lugar.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt ignora en silencio todo lo que pase de 72 bytes. Se recorta de forma
# explicita para que el comportamiento no dependa de la version instalada:
# algunas truncan sin avisar y otras lanzan error.
_MAX_BYTES = 72


def _codificar(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BYTES]


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro.

    Cada llamada genera una sal distinta, asi que dos usuarios con la misma
    contrasena tienen hashes diferentes.
    """
    return bcrypt.hashpw(_codificar(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Compara una contrasena en claro contra su hash."""
    try:
        return bcrypt.checkpw(_codificar(password), hashed.encode("utf-8"))
    except ValueError:
        # Hash con formato invalido (dato corrupto o migrado a mano): no es
        # una credencial valida, pero tampoco debe tumbar la peticion.
        return False


def crear_token_acceso(usuario_id: int, rol: str, expira_en: timedelta | None = None) -> str:
    """Firma un JWT que identifica a un usuario durante un tiempo limitado.

    El token no se guarda en ningun lado: la firma es lo que lo hace valido,
    asi que el API puede verificarlo sin consultar la base.
    """
    ahora = datetime.now(timezone.utc)
    if expira_en is None:
        expira_en = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        # "sub" (subject) es un claim estandar y debe ser string, aunque el
        # id sea entero. Devolverlo como int rompe validadores estrictos.
        "sub": str(usuario_id),
        "rol": rol,
        "iat": ahora,
        "exp": ahora + expira_en,
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token: str) -> dict | None:
    """Verifica firma y expiracion. Devuelve None si el token no sirve.

    Se devuelve None en lugar de propagar la excepcion para que quien llama
    decida el codigo HTTP: aqui no se sabe si es un 401 o un 403.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
