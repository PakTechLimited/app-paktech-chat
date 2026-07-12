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
static/
  index.html          Single-page HTML/JS chat client
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

# 3. Open browser
open http://localhost:8000

# 4. API docs (dev only)
open http://localhost:8000/docs
```

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
