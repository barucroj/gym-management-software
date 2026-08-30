"""Tests de la busqueda de socios.

Corren contra PostgreSQL de verdad, no contra SQLite: la consulta se apoya en
pg_trgm y en la funcion gym_normalizar que crea la migracion. Ver las fixtures
*_pg de conftest.py.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from gym_core.models.miembro import Miembro

RUTA = "/api/v1/miembros/buscar"


@pytest.fixture(name="padron")
def padron_fixture(session_pg: Session) -> dict[str, Miembro]:
    socios = {
        "rodriguez": Miembro(nombre="José", apellidos="Rodríguez"),
        "nunez": Miembro(nombre="Ana", apellidos="Núñez"),
        "mendoza": Miembro(nombre="Carlos", apellidos="Mendoza"),
        "baja": Miembro(nombre="Pedro", apellidos="Rodríguez", activo=False),
    }
    for socio in socios.values():
        session_pg.add(socio)
    session_pg.commit()
    for socio in socios.values():
        session_pg.refresh(socio)
    return socios


def buscar(client: TestClient, q: str, **extra) -> list[dict]:
    respuesta = client.get(RUTA, params={"q": q, **extra})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def nombres(resultados: list[dict]) -> list[str]:
    return [r["nombre_completo"] for r in resultados]


def test_encuentra_por_apellido_bien_escrito(client_pg_recepcion, padron) -> None:
    assert "José Rodríguez" in nombres(buscar(client_pg_recepcion, "Rodríguez"))


def test_tolera_una_errata(client_pg_recepcion, padron) -> None:
    """El motivo de existir de la feature: recepcion escribe lo que escucha."""
    assert "José Rodríguez" in nombres(buscar(client_pg_recepcion, "Rodrigez"))


def test_ignora_los_acentos_en_los_dos_sentidos(client_pg_recepcion, padron) -> None:
    assert "Ana Núñez" in nombres(buscar(client_pg_recepcion, "Nunez"))
    assert "José Rodríguez" in nombres(buscar(client_pg_recepcion, "jose"))


def test_encuentra_por_nombre_y_apellido_juntos(client_pg_recepcion, padron) -> None:
    assert nombres(buscar(client_pg_recepcion, "carlos mendoza"))[0] == "Carlos Mendoza"


def test_un_prefijo_corto_alcanza(client_pg_recepcion, padron) -> None:
    """Recepcion teclea tres letras y espera ver algo, no una lista vacia."""
    assert "Carlos Mendoza" in nombres(buscar(client_pg_recepcion, "men"))


def test_el_mas_parecido_va_primero(client_pg_recepcion, padron) -> None:
    resultados = buscar(client_pg_recepcion, "Mendoza")

    assert resultados[0]["nombre_completo"] == "Carlos Mendoza"
    assert resultados[0]["puntaje"] > 0


def test_un_numero_se_lee_como_id_de_socio(client_pg_recepcion, padron) -> None:
    """Es el dato que recepcion tiene a mano: el id que muestra cada lista."""
    esperado = padron["mendoza"]

    resultados = buscar(client_pg_recepcion, str(esperado.id))

    assert [r["id"] for r in resultados] == [esperado.id]


def test_solo_activos_deja_fuera_a_los_de_baja(client_pg_recepcion, padron) -> None:
    todos = nombres(buscar(client_pg_recepcion, "Rodríguez"))
    activos = nombres(buscar(client_pg_recepcion, "Rodríguez", solo_activos=True))

    assert "Pedro Rodríguez" in todos
    assert "Pedro Rodríguez" not in activos


def test_el_limite_acota_los_resultados(client_pg_recepcion, padron) -> None:
    assert len(buscar(client_pg_recepcion, "Rodríguez", limite=1)) == 1


def test_no_devuelve_a_quien_no_se_parece(client_pg_recepcion, padron) -> None:
    assert nombres(buscar(client_pg_recepcion, "Villanueva")) == []


def test_la_busqueda_no_expone_las_notas_del_socio(client_pg_recepcion, padron) -> None:
    """Alimenta un desplegable: no hay motivo para que viaje el historial."""
    resultado = buscar(client_pg_recepcion, "Mendoza")[0]

    assert "notas" not in resultado
    assert "fecha_nacimiento" not in resultado


def test_una_sola_letra_no_devuelve_nada(client_pg_recepcion, padron) -> None:
    """Con un caracter cualquier umbral de parecido devuelve medio padron."""
    assert buscar(client_pg_recepcion, "a") == []


def test_un_id_de_un_solo_digito_se_encuentra(
    client_pg_recepcion, session_pg: Session
) -> None:
    """El minimo de dos caracteres es para los nombres, no para los ids.

    El id va puesto a mano: la secuencia de la base no se reinicia entre
    pruebas, asi que dejarlo al azar haria que el test dependiera del orden.
    """
    session_pg.add(Miembro(id=7, nombre="Sara", apellidos="Iglesias"))
    session_pg.commit()

    assert [r["id"] for r in buscar(client_pg_recepcion, "7")] == [7]


def test_un_id_inexistente_no_devuelve_nada(client_pg_recepcion, padron) -> None:
    assert buscar(client_pg_recepcion, "99999") == []


def test_buscar_no_se_confunde_con_el_id_en_la_ruta(client_pg_recepcion, padron) -> None:
    """Si /{miembro_id} se declarara antes, "buscar" se leeria como entero."""
    assert client_pg_recepcion.get(RUTA, params={"q": "Mendoza"}).status_code == 200


def test_exige_autenticacion(client: TestClient) -> None:
    """Se corta en la dependencia, antes de tocar la base: sirve SQLite."""
    assert client.get(RUTA, params={"q": "Mendoza"}).status_code == 401
