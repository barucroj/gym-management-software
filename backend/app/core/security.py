"""Hashing y verificacion de contrasenas.

Aislado en su propio modulo a proposito: los routers y el futuro login solo
llaman a estas dos funciones, asi que cambiar de algoritmo mas adelante se
hace en un unico lugar.
"""

from passlib.context import CryptContext

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
