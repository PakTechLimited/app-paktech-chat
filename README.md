# app-paktech-chat

Real-time WebSocket chat application, taken from a laptop to a hardened Azure Kubernetes platform.
This is the application, Terraform and CI repository of the **PakTech Chat** DevSecOps portfolio project.

**Stack:** FastAPI · WebSockets · Redis Pub/Sub · PostgreSQL · Next.js · Terraform · AKS · Argo CD · GitHub Actions · Trivy · OPA Gatekeeper · Falco · Prometheus · Grafana
**Domain:** paktechlimited.chat (dev, staging and prod environments)
**GitOps repo:** [gitops-paktech-chat](https://github.com/PakTechLimited/gitops-paktech-chat) (Helm chart, Argo CD apps, policies, monitoring)

> **Guided walkthrough:** each phase has its own page with the goal, commands, workflow, issues and
> trade-offs: [alihaidry-devops.website/tech-series/paktech-chat](https://alihaidry-devops.website/tech-series/paktech-chat).
> The summary post is [here](https://alihaidry-devops.website/blog/paktech-chat-devsecops-aks).
> The lab cluster is stopped between working sessions to control cost, so the live site is up only while it is in use.

## What this project shows

| Phase | What it delivered |
|-------|-------------------|
| 1 | The app, hardened: in-memory access token with a rotating httpOnly refresh cookie, CSRF and Origin checks, authenticated WebSockets, Alembic migrations, 122 tests (about 96% coverage), non-root containers |
| 2 | Terraform: AKS with three node pools, ACR, Key Vault, Workload Identity, GitHub OIDC, Azure DNS, remote state |
| 3 | GitOps with Argo CD (app of apps), Envoy Gateway (Gateway API), cert-manager, one Helm chart for three environments |
| 4 | CI/CD: parallel quality and security gates, builds in ACR Tasks, Trivy scan by digest, digest committed to the GitOps repo, approval gate and manual sync for prod, rehearsed rollback |
| 5 | Runtime security in five layers: API server IP allow-list, Gatekeeper admission (7 constraints, all `deny`), hardened pods pinned by digest, egress network policies, Falco and Trivy Operator |
| 6 | Observability: kube-prometheus-stack, application metrics, dashboards in Git, alert rules routed to Slack |

## Architecture

```
Browser (Next.js)
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

## Delivery path

```
git push -> GitHub Actions (this repo)
   pull request:  backend (tests, Bandit, pip-audit) | semgrep | frontend (lint, build, npm audit) | iac (Terraform validate, Checkov, Trivy config)
   push:          build (OIDC login, ACR Tasks build, Trivy scan of repo@digest)
                  gitops (commits the new digest to gitops-paktech-chat)
-> Argo CD syncs: dev and staging automatically, prod after approval and a manual sync
```

- **No stored cloud credentials.** GitHub authenticates to Azure with a short-lived OIDC token.
- **Images are built in ACR Tasks**, never on the runner, and deployed by digest, so the bytes that were scanned are the bytes that run.
- **Promotion is a pull request:** `develop` (dev) -> `staging` -> `main` (prod). `promote.yml` and `rollback.yml` are the manual workflows.
- Workflows: `.github/workflows/ci.yml`, `promote.yml`, `rollback.yml`; Dependabot is configured in `.github/dependabot.yml`.

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
frontend/             Next.js client (chat, wall, AI) + Dockerfile
tests/                API, auth, rooms, messages, admin, migrations
terraform/            Azure infrastructure, see below
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

## Infrastructure (Terraform)

Applied to Azure (`rg-paktech-prod`, East US). State lives in a storage account
(`paktechtfstateprod`) with Azure AD auth; created once by `terraform/bootstrap/bootstrap-state.sh`.

```
terraform/
  bootstrap/           one-time script: state storage account + role assignment
  modules/
    network/           VNet 10.10.0.0/16, AKS subnet
    acr/               Azure Container Registry (paktechacr)
    keyvault/          Key Vault (kv-paktech-prod), RBAC mode
    aks/               AKS cluster + three node pools
    workload-identity/ user-assigned identity + federated credentials (dev/staging/prod)
    github-oidc/       Azure AD app for GitHub Actions (no stored secrets)
    dns/               Azure DNS zone, apex A record, www CNAME
  envs/prod/           wires the modules together
```

- **AKS** (`aks-paktech-prod`): Azure CNI Overlay with Cilium, OIDC issuer and
  Workload Identity, Key Vault CSI driver, AcrPull for the kubelet identity.
- **Node pools:** `system` (1 node, `CriticalAddonsOnly` taint), `apps` (autoscaling 1-3,
  `workload=apps`), `monitoring` (1 node, `workload=monitoring:NoSchedule`) for Prometheus, Grafana and the scanners.
- **Workload Identity:** `id-paktech-chat-prod` is trusted by service account `paktech-chat`
  in the `paktech-chat-dev`, `-staging` and `-prod` namespaces, with read access to Key Vault secrets.
- **GitHub OIDC:** `sp-github-paktech-cicd` trusts the repo's `develop`, `staging` and `main`
  branches, pull requests and the `prod` environment; it can push to ACR and get AKS credentials.
- **DNS:** `paktechlimited.chat` is delegated from the registrar to Azure DNS; records are managed by Terraform.

```bash
cd terraform/envs/prod
cp terraform.tfvars.example terraform.tfvars   # fill in your values
terraform init && terraform plan -out tfplan && terraform apply tfplan
$(terraform output -raw get_credentials_command)
```

Never commit `terraform.tfvars` or saved plans (`tfplan`); both are git-ignored.
The cluster costs roughly $8-9/day running; pause it when idle:

```bash
az aks stop  -g rg-paktech-prod -n aks-paktech-prod
az aks start -g rg-paktech-prod -n aks-paktech-prod
```

## Security highlights

- Application: tokens in memory only, rotating httpOnly refresh cookie, CSRF header plus Origin allow-list, WebSocket auth on the first frame, bcrypt password hashing, rate limiting.
- Pipeline: Bandit, Semgrep, Checkov, Trivy (image scan by digest and config scan), pip-audit and npm audit, run on every pull request.
- Cluster (policies live in the GitOps repo): Gatekeeper `deny` rules for privileged containers, privilege escalation, capabilities, read-only root filesystem, allowed registries, resource requests and image digests; egress network policies; no mounted Kubernetes API token; Falco runtime detection; Trivy Operator reports.

## Metrics

The API exposes `/metrics` (request count and latency by route template, active WebSocket connections,
messages, WebSocket connection attempts by result). It runs in prometheus-client multiprocess mode because
gunicorn starts several workers (`PROMETHEUS_MULTIPROC_DIR`, hooks in `gunicorn.conf.py`). The gateway only
routes `/api` and `/ws`, so `/metrics` is never reachable from the internet. Scraping is enabled per
environment by the chart flag `metrics.enabled` in the GitOps repo.

## Related

- Guided phase pages: <https://alihaidry-devops.website/tech-series/paktech-chat>
- Summary blog post: <https://alihaidry-devops.website/blog/paktech-chat-devsecops-aks>
- GitOps repository: <https://github.com/PakTechLimited/gitops-paktech-chat>
