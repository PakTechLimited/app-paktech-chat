#checkov:skip=CKV_DOCKER_2: Kubernetes ignores HEALTHCHECK; the Helm chart defines readiness and liveness probes on /api/v1/health.
FROM python:3.11-slim

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y setuptools wheel

COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY gunicorn.conf.py .

RUN mkdir -p /tmp && chown appuser:appgroup /tmp

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--config", "gunicorn.conf.py", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--log-level", "info"]
