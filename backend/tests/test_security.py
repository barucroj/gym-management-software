"""Tests del hashing de contrasenas.

Importan sobre todo por la compatibilidad: el modulo dejo de usar passlib y
pasa a llamar a bcrypt directamente, asi que hay que probar que los hashes
guardados antes del cambio siguen sirviendo.
"""

from app.core.security import hash_password, verify_password

CLAVE = "claveDelAdmin1"

# Hash real generado con passlib 1.7.4 (CryptContext(schemes=["bcrypt"])),
# antes de retirar esa dependencia. Si algun dia deja de verificar, todos los
# usuarios existentes quedarian sin poder entrar.
HASH_DE_PASSLIB = "$2b$12$YC02.J2TQ2UqkLsqzA1z8e2ouSdz24ETnM1frqGEU2QeNb414bgpW"


def test_un_hash_generado_por_passlib_sigue_validando() -> None:
    assert verify_password(CLAVE, HASH_DE_PASSLIB)


def test_una_clave_distinta_no_valida_contra_ese_hash() -> None:
    assert not verify_password("otraClave1", HASH_DE_PASSLIB)


def test_el_hash_no_es_la_contrasena() -> None:
    hashed = hash_password(CLAVE)

    assert hashed != CLAVE
    assert hashed.startswith("$2b$")


def test_la_misma_clave_produce_hashes_distintos() -> None:
    """Cada hash lleva su propia sal: dos usuarios con la misma contrasena
    no deben poder reconocerse entre si mirando la tabla."""
    assert hash_password(CLAVE) != hash_password(CLAVE)


def test_ida_y_vuelta() -> None:
    assert verify_password(CLAVE, hash_password(CLAVE))


def test_un_hash_corrupto_no_revienta() -> None:
    """Devuelve False en lugar de propagar la excepcion de bcrypt."""
    assert not verify_password(CLAVE, "esto-no-es-un-hash")


def test_bcrypt_solo_considera_los_primeros_72_bytes() -> None:
    """Comportamiento conocido de bcrypt, fijado para que no sorprenda.

    Por eso los schemas limitan la contrasena a 72: aceptar mas seria
    prometer una seguridad que el algoritmo no da.
    """
    base = "a" * 72
    hashed = hash_password(base)

    assert verify_password(base + "loQueSea", hashed)
