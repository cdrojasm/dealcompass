import { defineRailway, postgres, preserve, project, service } from "railway/iac";

// Source of truth for the Railway environment. Services use the repository root
// as build context, so both Dockerfiles can be kept under deploy/.
export default defineRailway((ctx) => {
  const production = ctx.environment === "production";
  const db = postgres("postgres");

  const api = service("api", {
    healthcheck: "/health",
    replicas: production ? 2 : 1,
    env: {
      RAILWAY_DOCKERFILE_PATH: "/deploy/backend.Dockerfile",
      DATABASE_URL: db.env.DATABASE_URL,
      FRONTEND_ORIGIN: "*",
    },
  });

  // Jobs live in PostgreSQL; replicas claim work with FOR UPDATE SKIP LOCKED.
  const worker = service("worker", {
    start: "python -m dealcompass_api.workers.runner",
    replicas: production ? 2 : 1,
    env: {
      RAILWAY_DOCKERFILE_PATH: "/deploy/backend.Dockerfile",
      DATABASE_URL: db.env.DATABASE_URL,
      WORKER_POLL_INTERVAL_SECONDS: "2",
      OPENROUTER_API_KEY: preserve(),
      OPENROUTER_MODEL: preserve(),
      GOOGLE_MAPS_API_KEY: preserve(),
      APIFY_TOKEN: preserve(),
      DAPTA_API_KEY: preserve(),
    },
  });

  const app = service("app", {
    healthcheck: "/health",
    env: {
      RAILWAY_DOCKERFILE_PATH: "/deploy/frontend.Dockerfile",
    },
  });

  return project("dealcompass", { resources: [db, api, worker, app] });
});

