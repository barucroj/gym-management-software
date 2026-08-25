# Contexto de build: la RAIZ del repo (no ./backend), porque la imagen
# necesita instalar el paquete compartido gym_core.
#
#   docker compose build api

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Paquete compartido primero: cambia menos seguido que el codigo del API,
# asi la capa se reaprovecha entre builds.
COPY gym_core/ ./gym_core/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./gym_core

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------
# Stage dev: agrega dependencias y suite de tests.
#   docker compose run --rm tests
# ---------------------------------------------------------------
FROM base AS dev

COPY backend/requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY backend/tests ./tests

CMD ["pytest", "-v"]
