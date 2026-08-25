# Contexto de build: la RAIZ del repo (no ./notifier), para instalar gym_core.
#
#   docker compose build notifier

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY gym_core/ ./gym_core/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./gym_core

COPY notifier/worker.py .

CMD ["python", "worker.py"]
