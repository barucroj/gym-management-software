"""Tests de la configuracion de CORS.

CORS es lo que permite a un navegador llamar al API desde otro origen. Con
Nginx sirviendo frontend y API por el mismo origen no hace falta, asi que lo
que se fija aqui es que este apagado salvo que se declare explicitamente.
"""

from fastapi.testclient import TestClient

from app.core.config import Settings


def test_sin_configurar_no_hay_origenes() -> None:
    assert Settings(CORS_ORIGINS="").cors_origins == []


def test_se_separan_por_coma_y_se_limpian_espacios() -> None:
    settings = Settings(CORS_ORIGINS="http://uno.local, http://dos.local ,")

    assert settings.cors_origins == ["http://uno.local", "http://dos.local"]


def test_nunca_se_responde_con_comodin(client: TestClient) -> None:
    """El comodin junto a allow_credentials es invalido para el navegador.

    Vale con CORS apagado (no hay cabecera) y encendido (origen explicito).
    """
    respuesta = client.get("/health", headers={"Origin": "http://cualquiera.local"})

    assert respuesta.headers.get("access-control-allow-origin") != "*"
