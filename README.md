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
gym-managment-sofware/
├── backend/
│   ├── app/
│   │   ├── main.py            # instancia FastAPI y healthcheck
│   │   ├── core/              # configuración y seguridad (JWT)
│   │   ├── db/                # engine y sesión de base de datos
│   │   ├── models/            # modelos SQLModel (tablas)
│   │   ├── schemas/           # DTOs Pydantic (entrada/salida)
│   │   ├── routers/           # endpoints por módulo
│   │   └── services/          # lógica de negocio
│   ├── tests/                 # pytest
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── notifier/
│   ├── worker.py              # scheduler de notificaciones
│   ├── requirements.txt
│   └── Dockerfile
├── proxy/
│   └── nginx.conf
├── frontend/                  # Angular (pendiente)
├── docs/                      # documentación y alcance del proyecto
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Puesta en marcha

### Requisitos

- Docker Desktop (Windows) o Docker Engine + Compose plugin (Linux)
- Python 3.12+ (solo si se va a desarrollar el backend fuera de Docker)

### 1. Clonar y configurar variables de entorno

```bash
git clone https://github.com/barucroj/gym-managment-sofware.git
cd gym-managment-sofware
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
docker compose run --rm tests   # correr la suite de tests
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

### 3. Ejecutar los tests

**Con Docker (no requiere Python local):**

```bash
docker compose run --rm tests
```

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

## Estado actual

Estructura base, contenedores y documentación. La lógica de negocio (miembros,
suscripciones, asistencias, autenticación) aún no está implementada.
