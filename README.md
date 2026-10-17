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

La infraestructura se define en `.railway/railway.ts`. Despliega cuatro recursos: PostgreSQL, API FastAPI, worker Python y `app` como estáticos servidos por Nginx. `app` es el único servicio público; publica el frontend en `/app` y pasa `/api` a la API por la red privada.

Para habilitar Serverless en la API, después del primer despliegue abre el servicio `api` en Railway y activa **Settings → Deploy → Serverless**. Railway aplica el cambio al siguiente despliegue. La API usa Python 3.12 y puede dormir entre solicitudes; la primera solicitud puede tardar más mientras despierta. Serverless es un ajuste del servicio de Railway y no está disponible como propiedad en la referencia actual de IaC.

El `worker` ejecuta el polling continuo de la cola PostgreSQL, así que debe permanecer activo para procesar trabajos sin demora. Define como secretos del servicio `worker`: `OPENROUTER_API_KEY`, `GOOGLE_MAPS_API_KEY`, `APIFY_TOKEN` y `DAPTA_API_KEY`.
