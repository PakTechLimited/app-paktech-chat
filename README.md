# app-paktech-chat

Real-time WebSocket chat application — PakTech DevSecOps portfolio project.

**Stack:** FastAPI · Redis Pub/Sub · PostgreSQL · HTML/JS frontend
**GitOps repo:** [gitops-paktech-chat](https://github.com/PakTechLimited/gitops-paktech-chat)

---

## Architecture

```
Browser (HTML/JS)
     │  WebSocket ws://host/ws/{room_id}?username=alice
     ▼
FastAPI (Uvicorn/Gunicorn)
     │  publish event
     ▼
Redis Pub/Sub  ──────►  All FastAPI pods (fan-out)
                              │  fan-out to connected clients
                              ▼
                       WebSocket connections

FastAPI ──► PostgreSQL  (message persistence, user/room models)
```

## Project structure

```
app/
  api/v1/endpoints/   health · rooms · messages · websocket
  core/               config (pydantic-settings) · logging
  db/                 async SQLAlchemy session + Base
  models/             User · Room · Message (ORM)
  schemas/            Pydantic I/O schemas + WS event types
  services/           ConnectionManager · RedisService
  main.py             FastAPI app factory + lifespan hooks
alembic/              Migration environment + versions/
frontend/               Next.js client (chat, wall, AI)
tests/
  test_health.py      Health endpoint smoke tests
Dockerfile
docker-compose.yml    Local full-stack (app + postgres + redis)
.pre-commit-config.yaml  Bandit · Semgrep · Black · isort
```

## Local development

```bash
# 1. Clone and copy env
cp .env.example .env

# 2. Start full stack
docker compose up --build

# 3. Open the web client (the `web` service; migrations run first, then api + web)
open http://localhost:3000
#    For hot reload instead: cd frontend && npm install && npm run dev

# 4. API docs (dev only)
open http://localhost:8000/docs
```

## Frontend container

`frontend/Dockerfile` is a multi-stage build (deps → build → runtime) that ships
only Next's `standalone` server as a non-root user (~40 MB of app files).
`NEXT_PUBLIC_API_URL` is inlined into the browser bundle at **build time**:

| Build arg value          | Meaning                                                        |
| ------------------------ | -------------------------------------------------------------- |
| `http://localhost:8000`  | local Compose: the browser calls the published API port        |
| *(empty)*                | same origin: an ingress routes `/api` and `/ws` to the backend |

In the same-origin setup, add the public site URL to the API's `ALLOWED_ORIGINS`
(CORS, the CSRF Origin check and the WebSocket origin check all use it).
Fonts are self-hosted from npm packages, so builds never call Google.

## Database migrations (Alembic)

The schema is owned by Alembic, never by the app at startup. In Compose a
one-shot `migrate` service runs `alembic upgrade head` and the app waits for it
(in Kubernetes this becomes a Job / init container).

```bash
# apply migrations (outside Docker, with the same POSTGRES_* env vars)
alembic upgrade head

# after changing a model: generate, review, then commit the new file
alembic revision --autogenerate -m "describe the change"

alembic downgrade -1      # step back one revision
```

A database created by the old `create_all` startup hook upgrades as-is: the
baseline skips tables that already exist. `tests/test_migrations.py` checks
fresh installs, legacy upgrades and that migrations match the models.

## Pre-commit setup

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # first-time scan
```

## WebSocket protocol

```
# Client → Server
{"type": "message",      "content": "hello"}
{"type": "typing"}
{"type": "typing_stop"}

# Server → Client
{"type": "message",    "room_id": 1, "username": "alice",
 "content": "hello",   "timestamp": "2025-01-01T10:00:00Z"}
{"type": "user_joined", "room_id": 1, "username": "alice", ...}
{"type": "user_left",   "room_id": 1, "username": "alice", ...}
{"type": "typing",      "room_id": 1, "username": "alice", ...}
{"type": "typing_stop", "room_id": 1, "username": "alice", ...}
```

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Local dev, pre-commit, Docker Compose |
| 2 | ⏳ | Terraform — AKS, ACR, Key Vault, Workload Identity |
| 3 | ⏳ | GitOps — Argo CD ApplicationSets (dev/staging/prod) |
| 4 | ⏳ | CI/CD — GitHub Actions + DevSecOps pipeline |
| 5 | ⏳ | Runtime Security — Falco, OPA Gatekeeper, Trivy Operator |
| 6 | ⏳ | Observability — Prometheus, Grafana, AlertManager → Slack |
