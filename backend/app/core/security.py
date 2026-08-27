"""Hashing de contrasenas y emision/verificacion de tokens JWT.

Aislado en su propio modulo a proposito: los routers y el futuro login solo
llaman a estas dos funciones, asi que cambiar de algoritmo mas adelante se
hace en un unico lugar.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# deprecated="auto" permite migrar de algoritmo sin invalidar los hashes ya
# guardados: passlib los marca como obsoletos, no como invalidos, y los sigue
# verificando hasta que el usuario cambie su contrasena.
_contexto = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro."""
    return _contexto.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Compara una contrasena en claro contra su hash."""
    return _contexto.verify(password, hashed)


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
