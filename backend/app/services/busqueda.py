"""Busqueda de socios por nombre, tolerante a erratas.

Recepcion escribe el nombre como lo escucha: "Rodrigez" por "Rodriguez",
"Nuñez" por "Nunez". Un LIKE falla en los dos casos y deja a quien atiende
recorriendo la lista a mano, que es justo lo que la pantalla deberia evitar.

La comparacion la hace PostgreSQL con pg_trgm, no Python: el indice GIN que
crea la migracion d4b8c1e07a52 cubre las dos condiciones del WHERE, asi que la
consulta sigue siendo barata cuando el gimnasio tenga miles de socios. Hacerlo
en Python obligaria a traerse la tabla entera en cada tecla.
"""

from dataclasses import dataclass

from sqlalchemy import String, func, or_, select, text
from sqlmodel import Session

from app.services.motor import exigir_postgresql
from gym_core.models.miembro import Miembro

LIMITE_POR_DEFECTO = 10

# Umbral de word_similarity. El de fabrica (0.6) es demasiado exigente para una
# recepcion: descarta "car" contra "Carlos Mendoza", que puntua 0.375. Con 0.3
# entran tanto los prefijos cortos como las erratas de una o dos letras, sin
# llenar la lista de nombres que no se parecen en nada.
UMBRAL_POR_DEFECTO = 0.3

# Por debajo de dos caracteres cualquier umbral de parecido devuelve medio
# padron. No aplica a los ids: "7" es una consulta exacta, no un prefijo.
LONGITUD_MINIMA = 2


@dataclass(frozen=True)
class ResultadoBusqueda:
    miembro: Miembro
    # Cuanto se parece el socio a lo que se tecleo, de 0 a 1. Se expone para
    # que la pantalla pueda distinguir una coincidencia exacta de una dudosa.
    puntaje: float


def _normalizar(valor):
    """Misma expresion que indexa la migracion: si difiere, el indice no se usa."""
    return func.gym_normalizar(valor, type_=String)


def _nombre_completo():
    return _normalizar(Miembro.nombre + " " + Miembro.apellidos)


def buscar_miembros(
    session: Session,
    consulta: str,
    *,
    limite: int = LIMITE_POR_DEFECTO,
    umbral: float = UMBRAL_POR_DEFECTO,
    solo_activos: bool = False,
) -> list[ResultadoBusqueda]:
    """Devuelve los socios que mas se parecen a `consulta`, de mejor a peor."""
    consulta = consulta.strip()
    id_candidato = consulta.lstrip("#").strip()

    # Un numero es un id de socio, no un nombre: es lo que recepcion tiene a
    # mano en la lista de vencimientos y en el carnet. Se resuelve directo, en
    # vez de dejar que compita por parecido con nombres que no tienen nada que
    # ver, y antes del minimo de longitud: los primeros socios del gimnasio
    # tienen ids de un solo digito.
    if id_candidato.isdigit() and id_candidato:
        miembro = session.get(Miembro, int(id_candidato))
        return [ResultadoBusqueda(miembro=miembro, puntaje=1.0)] if miembro else []

    if len(consulta) < LONGITUD_MINIMA:
        return []


    exigir_postgresql(session, "La busqueda de socios (pg_trgm)")

    # El umbral gobierna al operador <%. Se fija por transaccion (is_local) para
    # no alterar la sesion de conexiones que el pool reutiliza despues.
    session.execute(
        text("SELECT set_config('pg_trgm.word_similarity_threshold', :umbral, true)"),
        {"umbral": str(umbral)},
    )

    texto = _nombre_completo()
    q = _normalizar(consulta)

    # similarity compara las dos cadenas enteras y premia el nombre completo
    # bien escrito; word_similarity busca el mejor tramo y es la que rescata
    # "mendoza" contra "Carlos Mendoza". Se toma la mejor de las dos.
    puntaje = func.greatest(func.similarity(texto, q), func.word_similarity(q, texto))

    # Las dos condiciones se resuelven por el indice GIN: <% de forma nativa y
    # LIKE porque gin_trgm_ops tambien sabe extraer trigramas de un patron.
    coincide = or_(
        q.op("<%")(texto),
        texto.like(func.concat("%", q, "%")),
    )
    if solo_activos:
        coincide = coincide & (Miembro.activo.is_(True))

    sentencia = (
        select(Miembro, puntaje.label("puntaje"))
        .where(coincide)
        # El desempate por apellidos evita que dos socios igual de parecidos
        # salgan en orden distinto en cada llamada.
        .order_by(puntaje.desc(), Miembro.apellidos, Miembro.nombre)
        .limit(limite)
    )

    return [
        ResultadoBusqueda(miembro=miembro, puntaje=float(valor))
        for miembro, valor in session.execute(sentencia).all()
    ]
