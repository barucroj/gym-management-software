# ---------------------------------------------------------------
# Stage base: imagen de runtime que se usa en ejecucion normal.
# ---------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------
# Stage dev: agrega dependencias y suite de tests.
# Se construye solo bajo demanda:  docker compose run --rm tests
# ---------------------------------------------------------------
FROM base AS dev

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests ./tests

CMD ["pytest", "-v"]
