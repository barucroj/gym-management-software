# Gym Management Software

Sistema local de administración de gimnasio. **No es SaaS ni multi-tenant**: está pensado
para desplegarse en la infraestructura de un único gimnasio.

## Funcionalidad objetivo

- **Suscripciones:** consultar las suscripciones de los miembros y su estatus
  (`activa`, `próxima a vencer`, `vencida`).
- **Notificaciones:** alertar cuando una suscripción está próxima a vencer.
- **Asistencias:** registrar y consultar las asistencias de los miembros al gimnasio.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| Base de datos | PostgreSQL 16 (contenedor, volumen persistente) |
| Autenticación | JWT (`python-jose`) + hashing con `passlib`/`bcrypt` |
| Validación | Pydantic |
| Testing | pytest + httpx |
| Frontend | Angular *(pendiente)* |
| Contenedores | Docker + Docker Compose |
| Reverse proxy | Nginx |

---

## Arquitectura

Cinco servicios, orquestados con Docker Compose:

```
                       ┌──────────────┐
   navegador  ───────▶ │  proxy       │  Nginx · único punto de entrada
                       │  (:80)       │  /  → frontend   ·  /api → backend
                       └──────┬───────┘
                              │
                       ┌──────▼───────┐        ┌──────────────┐
                       │  api         │        │  notifier    │
                       │  FastAPI     │        │  worker      │
                       │  (:8000)     │        │  scheduler   │
                       └──────┬───────┘        └──────┬───────┘
                              │                       │
                              └───────────┬───────────┘
                                   ┌──────▼───────┐
                                   │  db          │
                                   │  PostgreSQL  │
                                   └──────────────┘
```

**Decisión de diseño:** el `notifier` es un proceso **separado** del API. Revisar
vencimientos es una tarea periódica de background; meterla dentro del proceso de FastAPI
lo acoplaría al ciclo de vida de los workers HTTP y complicaría el escalado.

---

## Estructura del repositorio

```
gym-management-software/
├── gym_core/                  # paquete compartido (API + notifier)
│   ├── gym_core/
│   │   ├── config.py          # settings comunes (DATABASE_URL, umbral de aviso)
│   │   ├── db.py              # engine y sesion de base de datos
│   │   ├── enums.py           # RolUsuario, EstatusSuscripcion
│   │   ├── estatus.py         # regla de negocio del estatus de suscripcion
│   │   └── models/            # modelos SQLModel (tablas)
│   ├── alembic/               # migraciones de base de datos
│   ├── alembic.ini
│   └── pyproject.toml
├── backend/
│   ├── app/
│   │   ├── main.py            # instancia FastAPI y healthchecks
│   │   ├── core/              # configuracion propia del API y seguridad (JWT)
│   │   ├── schemas/           # DTOs Pydantic (entrada/salida)
│   │   ├── routers/           # endpoints por modulo
│   │   └── services/          # logica de negocio
│   ├── tests/                 # pytest
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── notifier/
│   ├── worker.py              # scheduler de notificaciones
│   └── Dockerfile
├── proxy/
│   └── nginx.conf
├── frontend/                  # Angular (pendiente)
├── docs/                      # documentacion (los PDF no se versionan)
├── docker-compose.yml
├── .env.example
├── .dockerignore
└── README.md
```

**Por que existe `gym_core`:** el API y el notifier necesitan los mismos modelos
y la misma regla de vencimiento. Duplicarlos garantizaria que se desincronicen,
y hacer que el notifier consulte al API por HTTP agregaria acoplamiento
innecesario para una tarea que solo lee de la base. En su lugar viven en un
paquete local que ambas imagenes instalan con `pip install ./gym_core`.

Por eso el contexto de build de `backend/Dockerfile` y `notifier/Dockerfile`
es la **raiz del repo**, no su propia carpeta.

---

## Puesta en marcha

### Requisitos

- Docker Desktop (Windows) o Docker Engine + Compose plugin (Linux)
- Python 3.12+ (solo si se va a desarrollar el backend fuera de Docker)

### 1. Clonar y configurar variables de entorno

```bash
git clone https://github.com/barucroj/gym-management-software.git
cd gym-management-software
```

Copiar la plantilla de variables de entorno:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Editar `.env` y cambiar como mínimo `POSTGRES_PASSWORD` y `JWT_SECRET_KEY`.
El archivo `.env` está en `.gitignore` y **nunca** debe subirse al repositorio.

### 2. Opción A — Levantar todo con Docker (recomendado)

```bash
docker compose up --build
```

Servicios disponibles:

| URL | Descripción |
|---|---|
| http://localhost/api/health | Healthcheck vía Nginx |
| http://localhost/docs | Documentación interactiva (Swagger UI) |
| http://localhost:8000/health | API directa, sin pasar por el proxy |

Comandos útiles:

```bash
docker compose ps               # estado de los servicios
docker compose logs -f api      # logs del backend
docker compose logs -f notifier # logs del worker
docker compose run --build --rm tests   # correr la suite de tests
docker compose down             # detener (conserva los datos)
docker compose down -v          # detener y BORRAR el volumen de la base de datos
```

### 2. Opción B — Backend en local con virtualenv

Útil para iterar rápido sobre el API. La base de datos sigue corriendo en Docker.

```bash
docker compose up -d db
```

**Linux / macOS**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Ajustar `DATABASE_URL` en `.env` para apuntar a `localhost` en vez de `db`:

```
DATABASE_URL=postgresql+psycopg://gym:changeme@localhost:5432/gymdb
```

Levantar el servidor de desarrollo con recarga automática:

```bash
uvicorn app.main:app --reload
```

Disponible en http://localhost:8000/docs

### 3. Migraciones de base de datos (Alembic)

El esquema se versiona con Alembic. Las tablas **no** se crean solas al arrancar
el API: hay que aplicar las migraciones.

```bash
docker compose run --build --rm migrate          # aplica las pendientes
```

Para crear una migracion nueva despues de modificar los modelos de `gym_core`:

```bash
docker compose run --build --rm   -v "$(pwd)/gym_core/alembic/versions:/code/gym_core/alembic/versions"   migrate alembic -c gym_core/alembic.ini revision --autogenerate -m "descripcion del cambio"
```

El volumen es necesario para que el archivo generado quede en tu disco y no
solo dentro del contenedor. **Revisa siempre** el archivo resultante antes de
commitearlo: autogenerate acierta casi siempre, pero no adivina renombres de
columnas ni migraciones de datos.

Otros comandos:

```bash
docker compose run --rm migrate alembic -c gym_core/alembic.ini current
docker compose run --rm migrate alembic -c gym_core/alembic.ini history
docker compose run --rm migrate alembic -c gym_core/alembic.ini downgrade -1
```

### 4. Ejecutar los tests

**Con Docker (no requiere Python local):**

```bash
docker compose run --build --rm tests
```

> El `--build` importa: sin el, Docker reutiliza la imagen anterior y los
> cambios recientes en `gym_core` o en los tests no se reflejan.

El servicio `tests` usa el stage `dev` del Dockerfile del backend, que agrega
`requirements-dev.txt` y la carpeta `tests/`. Esta bajo el profile `test`, asi que
**no** se levanta con `docker compose up`.

**Con virtualenv local:**

```bash
cd backend
pytest
```

---

## Flujo de trabajo con Git

| Rama | Propósito |
|---|---|
| `main` | Código estable. Solo recibe merges desde `develop`. |
| `develop` | Rama de integración. Base de todo el trabajo nuevo. |
| `feature/*` | Una rama por funcionalidad. Se mergea a `develop`. |

```bash
git checkout develop
git pull origin develop
git checkout -b feature/registro-asistencias
# ... trabajo y commits ...
git push -u origin feature/registro-asistencias
```

Los mensajes de commit siguen [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.

---

## Modelo de datos

| Tabla | Descripcion |
|---|---|
| `usuarios` | Personal que opera el sistema (Admin / Recepcion) |
| `miembros` | Miembros del gimnasio |
| `planes` | Planes de membresia: duracion y precio |
| `suscripciones` | Vigencia que un miembro compra sobre un plan |
| `asistencias` | Registro de entrada de un miembro |

**El estatus de una suscripcion no se guarda: se calcula.** Un campo `estatus`
persistido quedaria obsoleto en cuanto pasara un dia sin correr un job de
actualizacion. Se deriva siempre de `fecha_fin` contra la fecha actual
(`gym_core.estatus.calcular_estatus`):

| Estatus | Condicion |
|---|---|
| `vencida` | `fecha_fin` ya paso |
| `por_vencer` | quedan `NOTIFIER_DAYS_BEFORE_EXPIRATION` dias o menos |
| `activa` | queda mas tiempo que el umbral |

El ultimo dia de vigencia cuenta como `por_vencer`, no como `vencida`.

Las vigencias usan `date` y no `datetime`: son dias de calendario, y modelarlas
con marcas de tiempo obliga a pelear con zonas horarias sin ganar nada. Las
asistencias si usan `datetime` en UTC, porque ahi la hora si importa.

## Estado actual

Estructura base, contenedores y documentación. La lógica de negocio (miembros,
suscripciones, asistencias, autenticación) aún no está implementada.
