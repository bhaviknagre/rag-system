# Deployment

---

## Local (Python)

```bash
# Clone + venv
git clone https://github.com/bhaviknagre/rag-system.git
cd rag-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Config
cp .env.example .env

# Services
docker run -d -p 6379:6379 redis:7.2-alpine
ollama serve &
ollama pull llama3.2:1b

# Worker (separate terminal)
celery -A src.worker.celery_app worker --loglevel=info -E

# Or use the all-in-one script
bash scripts/start_local.sh

# Add docs + ingest
cp your_docs/*.pdf data/raw/
dvc repro

# API
uvicorn api.main:app --reload --port 8000
```

---

## Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
bash scripts/healthcheck.sh
```

### Services

| Container | Port | Purpose |
|---|---|---|
| `rag-nginx` | 80 | Load balancer — main entry |
| `rag-api` | 8000 (internal) | FastAPI + Gunicorn |
| `rag-worker` | — | Celery worker |
| `rag-flower` | 5555 | Celery monitoring |
| `rag-redis` | 6379 | Broker + result backend |
| `rag-ollama` | 11434 | Local LLM |
| `rag-prometheus` | 9090 | Metrics |
| `rag-grafana` | 3000 | Dashboards |

### Scaling with Docker Compose

```bash
# Scale to 3 API + 3 workers
bash scripts/scale.sh up

# Back to 1 each
bash scripts/scale.sh down
```

---

## Kubernetes

```bash
# Build image inside Minikube
bash k8s/scripts/build-images.sh

# Deploy all 7 phases
bash k8s/scripts/deploy.sh

# Set up hostname
sudo bash k8s/scripts/setup-hosts.sh

# Start tunnel (keep running)
minikube tunnel
```

### Zero-downtime rollout

After code changes:

```bash
# Rebuilds image + rolls API and worker with kubectl set image
bash k8s/scripts/rollout.sh
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VECTOR_DB_PROVIDER` | No | `chroma` | Default backend |
| `CHUNKING_STRATEGY` | No | `recursive` | Default strategy |
| `PINECONE_API_KEY` | Pinecone | — | From app.pinecone.io |
| `PINECONE_INDEX_NAME` | Pinecone | `rag-system-index` | dim=384, cosine |
| `MONGODB_ATLAS_URI` | MongoDB | — | `mongodb+srv://...` |
| `MONGODB_DB_NAME` | No | `rag_system` | Atlas database |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server |
| `LLM_MODEL` | No | `llama3.2:1b` | Ollama model name |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | HuggingFace model |
| `CHUNK_SIZE` | No | `500` | Words per chunk |
| `CHUNK_OVERLAP` | No | `50` | Overlap words |
| `TOP_K` | No | `4` | Chunks per query |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/0` | Job results |