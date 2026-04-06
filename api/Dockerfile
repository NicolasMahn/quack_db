FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/data

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/quack.db

COPY pyproject.toml /app/
COPY src /app/src
COPY api /app/api

RUN pip install --no-cache-dir pip \
    && pip install --no-cache-dir -e .

# Must match azure-deploy.yml target-port (ACA sends traffic here).
EXPOSE 8001

ENV API_PORT=8001
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${API_PORT}"]
