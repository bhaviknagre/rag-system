# RAG System

A production-grade Retrieval-Augmented Generation (RAG) pipeline for document
ingestion and question answering. Built with a microservices mindset —
FastAPI handles HTTP, Celery + Redis manage heavy ingestion jobs as
non-blocking background tasks, LangChain abstracts the vector store layer
so Chroma, Pinecone, and MongoDB Atlas are all switchable without touching
pipeline logic, Nginx load balances across multiple API replicas, and Ollama
runs the LLM locally with zero API cost. The entire stack is containerized
with Docker Compose, monitored via Prometheus + Grafana, and data pipelines
are versioned and reproducible via DVC.

**Full documentation, including visual architecture and flow diagrams,
is published at [rag-documentation.github.io/rag-system](https://rag-documentation.github.io/rag-system/).**

---

## Architecture

See [Architecture Diagrams](https://rag-documentation.github.io/rag-system/architecture/diagrams/)
for the full visual reference (system topology, ingestion/query sequence
diagrams, monitoring flow, vector store factory, and Kubernetes topology).
Summary:

```
Ingestion Flow (async):
POST /ingest → Nginx → API → Redis Queue → Celery Worker
→ Loader → Chunker → Embedder → Vector Store
GET /jobs/{id} → poll status: queued → running → success

Query Flow (sync):
POST /ask → Nginx → API → Vector Store (top-k)
→ Ollama (generate) → Answer + Sources

Monitoring:
API /metrics → Prometheus → Grafana Dashboards
Redis        → redis-exporter → Prometheus
Nginx        → nginx-exporter → Prometheus
Celery       → Flower (port 5555)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Load Balancer | Nginx 1.27 | Rate limiting, reverse proxy, load balancing |
| API Server | FastAPI 0.139 + Gunicorn + Uvicorn | HTTP endpoints, multi-process serving |
| Background Jobs | Celery 5.3 | Async ingestion task queue |
| Message Broker | Redis 7.2 | Job queue + result backend |
| Job Monitoring | Flower | Real-time Celery task dashboard |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, free, 384-dim vectors |
| LLM | Ollama (llama3.2:1b) | Local inference, no API cost |
| Vector DB | Chroma / Pinecone / MongoDB Atlas | Switchable backends |
| LLM Framework | LangChain 0.3.x | Vector store abstraction layer |
| Metrics | Prometheus + Grafana | System + business metrics |
| Data Versioning | DVC | Reproducible data pipelines |
| Containerization | Docker + Docker Compose | Full stack orchestration |
| Config | pydantic-settings + .env | Type-safe environment config |

Dependency versions are pinned in `requirements.txt` and audited with
`pip-audit`; see the [Security guide](https://rag-documentation.github.io/rag-system/guides/security/)
for current status and any deliberately deferred items.

## Project Structure
```
rag-system/
├── api/
│   ├── main.py              # FastAPI app, all endpoints, Prometheus metrics
│   ├── middleware.py        # RequestID, Timing, ProcessTime middleware
│   └── schemas.py           # Pydantic request/response models
├── k8s/
│   ├── namespace.yaml
│   ├── configmap/configmap.yaml
│   ├── secrets/secrets.yaml
│   ├── redis/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── ollama/
│   │   ├── statefulset.yaml
│   │   └── service.yaml
│   ├── api/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── worker/
│   │   ├── deployment.yaml
│   │   └── keda-scaledobject.yaml
│   ├── flower/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── monitoring/
│   │   ├── servicemonitor.yaml
│   │   ├── prometheus-rules.yaml
│   │   └── grafana-dashboard-configmap.yaml
│   ├── ingress/
│   │   ├── ingress.yaml
│   │   └── grafan-config.yaml   # Grafana /grafana subpath asset fix
│   └── scripts/
│       ├── build-images.sh
│       ├── deploy.sh
│       ├── rollout.sh
│       └── setup-hosts.sh
├── src/
│   ├── config.py            # Centralized settings via pydantic-settings
│   ├── pipeline.py          # ingest() + ask() — core entry points
│   │
│   ├── ingestion/
│   │   ├── loader.py        # PDF / DOCX / TXT document loader
│   │   └── chunker.py       # Recursive / Semantic / Sentence-window chunking
│   │
│   ├── embedings/           # (sic — pre-existing typo, kept to avoid an import-path rename)
│   │   └── embedder.py      # HuggingFace embeddings (LangChain interface)
│   │
│   ├── vectorstore/
│   │   └── store.py         # Multi-backend factory (Chroma/Pinecone/MongoDB)
│   │
│   ├── retrieval/
│   │   └── retriever.py     # Not on the live request path — see docs/components/retrieval.md
│   │
│   ├── generation/
│   │   └── generator.py     # Ollama LLM generation
│   │
│   ├── worker/
│   │   ├── celery_app.py    # Celery app config (broker, backend, serializer)
│   │   └── tasks.py         # ingest_documents_task (async background job)
│   │
│   └── monitoring/
│       └── metrics.py       # Prometheus counters, histograms, gauges
│
├── nginx/
│   ├── Dockerfile           # Nginx image
│   └── nginx.conf           # Rate limiting, load balancing, routing
│
├── prometheus/
│   ├── prometheus.yml       # Scrape config (API, Redis, Nginx, Celery)
│   └── alerts.yml           # Alert rules (latency, errors, downtime)
│
├── grafana/
│   └── provisioning/
│       ├── datasources/     # Auto-provisioned Prometheus datasource
│       └── dashboards/      # Auto-provisioned dashboard config
│
├── scripts/
│   ├── ingest.py            # DVC-tracked ingestion CLI (synchronous)
│   ├── evaluate.py          # DVC-tracked retrieval evaluation
│   ├── scale.sh             # Scale API + workers up/down
│   ├── healthcheck.sh       # Full system health check across all services
│   └── start_local.sh       # Start full local stack in one command
│
├── data/
│   ├── raw/                 # Source documents (DVC tracked)
│   ├── processed/           # DVC stage outputs (metrics, summaries)
│   └── vectorstore/         # Chroma persistence (Docker volume)
│
├── params.yaml              # DVC experiment parameters
├── dvc.yaml                 # DVC pipeline (ingest + evaluate stages)
├── Dockerfile               # Single image for API, worker, flower
├── docker-compose.yml       # Full production stack (10 services)
├── requirements.txt         # Pinned Python dependencies
└── .env.example             # Environment variable template
```
---

## Quickstart (Local)

# 1. Clone and create virtual environment
```bash
git clone https://github.com/bhaviknagre/rag-system.git
cd rag-system
python -m venv .venv && source .venv/bin/activate
```

# 2. Install dependencies
```
pip install -r requirements.txt
```

# 3. Configure environment
```
cp .env.example .env
# Edit .env — fill in Pinecone key and MongoDB URI if using those backends
```

# 4. Add documents
```bash
cp your_docs/*.pdf data/raw/
```

# 5. Start everything in one command
```
chmod +x scripts/start_local.sh
./scripts/start_local.sh
```

This starts Redis (Docker), Ollama, Celery worker, Flower, and FastAPI together.

| URL | Service |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/rag-system | Web UI |
| http://localhost:5555 | Flower (Celery monitoring) |


---

## Quickstart (Docker — Full Production Stack)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env

# 2. Add documents
cp your_docs/*.pdf data/raw/

# 3. Start all services
docker compose up --build -d

# 4. Verify everything is healthy
bash scripts/healthcheck.sh

# 5. Ingest documents (returns job_id immediately)
curl -X POST http://localhost/ingest \
  -H "Content-Type: application/json" \
  -d '{"provider": "chroma", "strategy": "recursive", "reset": true}'

# 6. Poll job status
curl http://localhost/jobs/<job_id>

# 7. Ask a question
curl -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "provider": "chroma"}'
```

> **Disk space:** the full image build (PyTorch + sentence-transformers +
> the LangChain stack) pulls several GB of layers. Make sure Docker Desktop
> has real free disk headroom before building — `docker system df` shows
> current usage, and `docker system prune` (safe: only removes stopped
> containers, dangling images, and build cache, never volumes) reclaims
> space if a build fails with I/O or "no space left on device" errors.

---

## Scaling

```bash
# Scale to 3 API instances + 3 Celery workers
./scripts/scale.sh up

# Scale back to 1 of each
./scripts/scale.sh down

# Check current counts
./scripts/scale.sh status
```

Nginx automatically load balances across all API replicas using
least-connections strategy. No config change needed.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System status + chunk counts per backend |
| POST | `/ingest` | Queue ingestion job → returns `job_id` (HTTP 202) |
| GET | `/jobs/{job_id}` | Poll job: queued → running → success / failed |
| DELETE | `/jobs/{job_id}/cancel` | Cancel a queued or running job |
| POST | `/ask` | Retrieve context + generate grounded answer |
| POST | `/upload` | Upload a file, optionally queue ingestion immediately |
| GET | `/providers` | List vector DB backends + connection status |
| GET | `/strategies` | List chunking strategies + descriptions |
| GET | `/metrics` | Prometheus metrics endpoint |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/rag-system` | Web UI (drag-and-drop upload + Q&A) |

### POST /ingest
Returns immediately with `job_id`. Ingestion runs in background via Celery.

```json
// Request
{
  "provider": "chroma",
  "strategy": "recursive",
  "reset": true
}

// Response (HTTP 202)
{
  "job_id": "a3f8c2d1-4b5e-...",
  "status": "queued",
  "provider": "chroma",
  "strategy": "recursive",
  "message": "Ingestion queued. Poll /jobs/a3f8c2d1-... for status."
}
```

### GET /jobs/{job_id}
Poll until `status` is `success` or `failed`.

```json
// While running
{
  "job_id": "a3f8c2d1-...",
  "status": "running",
  "progress": { "step": "loading documents", "provider": "chroma" }
}

// On success
{
  "job_id": "a3f8c2d1-...",
  "status": "success",
  "result": {
    "documents_loaded": 3,
    "chunks_created": 96,
    "chunks_added": 96,
    "total_chunks_in_store": 96
  }
}
```

### POST /ask
```json
// Request
{
  "question": "What are the main topics in this document?",
  "provider": "chroma",
  "top_k": 4
}

// Response
{
  "question": "What are the main topics in this document?",
  "answer": "The document covers...",
  "provider": "chroma",
  "sources": [
    { "doc_id": "report.pdf", "source": "data/raw/report.pdf",
      "score": 0.87, "strategy": "recursive" }
  ]
}
```

> `/ask` always returns `200 OK` with a valid JSON body even if the LLM is
> unreachable — check the *content* of `answer` for an `"Error: ..."`
> prefix, not just the HTTP status.

---

## Chunking Strategies

| Strategy | How it works | Best for | Speed |
|---|---|---|---|
| `recursive` | Splits by paragraph → sentence → word boundary | General purpose | Fast |
| `semantic` | Splits at embedding similarity boundaries | Long docs with topic shifts | Slow |
| `sentence_window` | One sentence per chunk + surrounding context in metadata | Precise Q&A | Medium |

Switch strategy per ingestion request — no restart needed:
```json
{ "provider": "chroma", "strategy": "sentence_window", "reset": true }
```

---

## Vector DB Backends

| Backend | Type | Best for | Setup |
|---|---|---|---|
| `chroma` | Local file-persisted | Dev, testing, offline | None |
| `pinecone` | Managed serverless cloud | Production, demos | API key + index (dim=384, cosine) |
| `mongodb` | MongoDB Atlas Vector Search | Existing Mongo users | URI + Atlas vector search index |

Switch backend per request — the same API, same embeddings, different store:
```json
{ "provider": "pinecone", "strategy": "recursive" }
```

Only the backend actually selected needs credentials — `chroma` requires
none, and the `pinecone` / `mongodb` clients are built lazily on first use,
not at process startup.

---

## DVC Pipeline

DVC handles reproducible, versioned data pipelines separately from the
async API ingestion. This is intentional — DVC runs synchronously for
experiment tracking, Celery runs asynchronously for API non-blocking responses.

```bash
dvc repro           # run full pipeline: ingest → evaluate
dvc metrics show    # compare ingestion + retrieval metrics across runs
dvc params diff     # see what changed vs last run
dvc dag             # visualize pipeline dependency graph
```

Pipeline stages:

| Stage | Reruns when |
|---|---|
| `ingest` | `data/raw` changes, ingestion code changes, params change |
| `evaluate` | Ingest output changes, retrieval params change |

Tracked metrics per run:

| Metric | Description |
|---|---|
| `documents_loaded` | Source documents ingested |
| `chunks_created` | Total chunks after splitting |
| `chunks_added` | Chunks successfully stored |
| `avg_top1_score` | Average best-chunk relevance score |
| `avg_top_k_score` | Average relevance across all retrieved chunks |
| `queries_with_results` | Queries returning at least one chunk |

---

## Monitoring

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | admin / ragadmin |
| Prometheus | http://localhost:9090 | — |
| Flower | http://localhost:5555 | — |
| API metrics | http://localhost/metrics | — |

> Change the Grafana admin password (`GF_SECURITY_ADMIN_PASSWORD` in
> `docker-compose.yml`) before any real deployment — `ragadmin` is a
> local-dev default only.

### Prometheus metrics (custom)

| Metric | Type | Description |
|---|---|---|
| `rag_ask_requests_total` | Counter | Total /ask requests by provider |
| `rag_ask_latency_seconds` | Histogram | End-to-end /ask latency |
| `rag_retrieval_top1_score` | Histogram | Top-1 relevance score distribution |
| `rag_empty_retrievals_total` | Counter | Queries returning zero chunks |
| `rag_ingest_jobs_submitted_total` | Counter | Jobs queued by provider + strategy |
| `rag_ingest_jobs_completed_total` | Counter | Jobs completed by status |
| `rag_ingest_chunks_created_total` | Counter | Total chunks ingested |
| `rag_vector_store_chunks` | Gauge | Current chunk count per backend |
| `rag_llm_generation_latency_seconds` | Histogram | Ollama response time |
| `rag_llm_errors_total` | Counter | LLM connection/timeout errors |

### Active alerts

| Alert | Condition | Severity |
|---|---|---|
| `APIHighLatency` | p95 /ask latency > 30s for 2min | Warning |
| `HighEmptyRetrievals` | >50% queries return no chunks | Warning |
| `LLMErrors` | LLM error rate > 0.1/s | Critical |
| `APIDown` | API unreachable for 30s | Critical |
| `WorkerDown` | Celery worker unreachable for 1min | Critical |
| `RedisDown` | Redis unreachable for 30s | Critical |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VECTOR_DB_PROVIDER` | No | `chroma` | Default backend |
| `CHUNKING_STRATEGY` | No | `recursive` | Default chunking strategy |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | HuggingFace model name |
| `LLM_MODEL` | No | `llama3.2:1b` | Ollama model name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `PINECONE_API_KEY` | Pinecone only | — | From https://app.pinecone.io |
| `PINECONE_INDEX_NAME` | Pinecone only | `rag-system-index` | Must exist, dim=384, cosine |
| `MONGODB_ATLAS_URI` | MongoDB only | — | `mongodb+srv://...` — leave unset unless using this backend |
| `MONGODB_DB_NAME` | No | `rag_system` | Atlas database name |
| `MONGODB_COLLECTION_NAME` | No | `document_chunks` | Atlas collection name |
| `MONGODB_VECTOR_INDEX_NAME` | No | `vector_index` | Atlas vector search index name |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/0` | Celery result store |
| `CHUNK_SIZE` | No | `500` | Words per chunk |
| `CHUNK_OVERLAP` | No | `50` | Overlap between chunks |
| `TOP_K` | No | `4` | Chunks retrieved per query |

> Never hardcode credentials as field defaults in `src/config.py` — every
> secret-shaped field must default to `""` and fail loudly (see
> `_get_mongo_client()` in `src/vectorstore/store.py`) if unset, rather than
> silently falling back to a real value.

---

## Services (Docker Compose)

| Service | Port | Description |
|---|---|---|
| `nginx` | 80 | Load balancer — main entry point |
| `rag-api` | 8000 (internal) | FastAPI + Gunicorn (scale with --scale) |
| `rag-worker` | — | Celery worker (scale with --scale) |
| `flower` | 5555 | Celery job monitoring UI |
| `redis` | 6379 | Message broker + result backend |
| `redis-exporter` | 9121 | Redis → Prometheus metrics |
| `ollama` | 11434 | Local LLM server |
| `prometheus` | 9090 | Metrics collection + alerting |
| `grafana` | 3000 | Metrics dashboards |
| `nginx-exporter` | 9113 | Nginx → Prometheus metrics |

---

## Kubernetes Deployment (Minikube)

The full stack runs on Kubernetes with auto-scaling, queue-based worker
scaling, and path-based ingress routing — all on a local Minikube cluster.
See [Kubernetes docs](https://rag-documentation.github.io/rag-system/kubernetes/overview/)
for the full 7-phase build and topology diagram.

### Prerequisites

```bash
brew install minikube kubectl helm
minikube start --driver=docker --cpus=4 --memory=6144 --disk-size=20g
minikube addons enable ingress
minikube addons enable metrics-server
```

### One-command deploy

```bash
# Build image inside Minikube
bash k8s/scripts/build-images.sh

# Deploy all phases
bash k8s/scripts/deploy.sh

# Add rag.local to /etc/hosts
sudo bash k8s/scripts/setup-hosts.sh

# Start Minikube tunnel (keep running)
minikube tunnel
```

### Access URLs

| URL | Service |
|---|---|
| http://rag.local | RAG API |
| http://rag.local/docs | Swagger UI |
| http://rag.local/rag-system | Web UI |
| http://rag.local/flower | Flower — Celery task monitor |
| http://rag.local/grafana | Grafana — dashboards (admin/ragadmin) |
| http://rag.local/prometheus | Prometheus — metrics |

### Scaling commands

```bash
# Scale API manually
kubectl scale deployment/rag-api --replicas=4 -n rag-system

# Watch KEDA auto-scale workers when jobs submitted
kubectl get pods -n rag-system -w

# Check HPA status
kubectl get hpa -n rag-system

# Check KEDA ScaledObject
kubectl get scaledobject -n rag-system

# Zero-downtime rollout after code change
bash k8s/scripts/rollout.sh
```

### K8s resource inventory

| Resource | Kind | Namespace | Purpose |
|---|---|---|---|
| `rag-system` | Namespace | — | Isolates all RAG resources |
| `rag-config` | ConfigMap | rag-system | Non-sensitive env config |
| `rag-secrets` | Secret | rag-system | API keys + DB URIs |
| `redis` | Deployment | rag-system | Celery broker + result store |
| `redis-service` | Service (ClusterIP) | rag-system | Internal Redis DNS |
| `ollama` | StatefulSet | rag-system | LLM serving (model persisted) |
| `ollama-service` | Service (Headless) | rag-system | Stable pod DNS |
| `rag-api` | Deployment | rag-system | FastAPI + Gunicorn |
| `rag-api-service` | Service (ClusterIP) | rag-system | Internal API routing |
| `rag-api-hpa` | HPA | rag-system | CPU/memory auto-scaling |
| `rag-worker` | Deployment | rag-system | Celery workers |
| `rag-worker-scaledobject` | ScaledObject (KEDA) | rag-system | Queue-depth scaling |
| `flower` | Deployment | rag-system | Celery monitoring UI |
| `rag-ingress` | Ingress | rag-system | Path-based routing |
| `grafana-ini-override` | ConfigMap | monitoring | Grafana `/grafana` subpath asset fix |
| `rag-api-monitor` | ServiceMonitor | rag-system | Prometheus scrape config |
| `rag-alerts` | PrometheusRule | rag-system | Alert rules |
| Prometheus + Grafana | Helm release | monitoring | Full observability stack |

---

## Documentation

Full docs, including the visual architecture/flow diagrams, live at
**[rag-documentation.github.io/rag-system](https://rag-documentation.github.io/rag-system/)**
and are built from the `docs/` folder with MkDocs Material. To preview locally:

```bash
pip install mkdocs-material==9.7.6 mkdocs-minify-plugin==0.8.0
mkdocs serve
```
