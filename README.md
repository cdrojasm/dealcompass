# DealCompass

Plataforma que descubre empresas (leads), las contacta y las envía a calificación.
Reemplaza la prospección manual (investigación + primer contacto).

## Estructura

```text
src/dealcompass_api/
  domain/       # Entidades puras (Search, Lead)
  application/  # Casos de uso y puertos
  infra/
    entrypoint/ # HTTP/FastAPI
    factory/    # Composition root
    db/         # SQLAlchemy y modelos
    repositories/
  workers/      # Worker de jobs (cola en PostgreSQL, SKIP LOCKED) y handlers
app/            # React + Vite
deploy/         # Dockerfiles, Nginx e IaC de Railway
db/             # Esquema de referencia
```

Servicios: `app` (Nginx + React, único público) → `api` (FastAPI) → `postgres` ← `worker`.
Una sola DB; la cola de trabajo es la tabla `jobs`.

## Local

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
PYTHONPATH=src uvicorn dealcompass_api.main:app --reload --port 8000
PYTHONPATH=src python -m dealcompass_api.workers.runner   # otra terminal
cd app && npm install && npm run dev
```

## Railway

```bash
railway link
railway config plan
railway config apply
```

Define como secretos del servicio `worker`: `OPENROUTER_API_KEY`, `GOOGLE_MAPS_API_KEY`, `APIFY_TOKEN`, `DAPTA_API_KEY`.
