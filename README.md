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

---

## Architecture
``` bash
Ingestion Flow (async):
POST /ingest → Nginx → API → Redis Queue → Celery Worker
→ Loader → Chunker → Embedder → Vector Store
GET /jobs/{id} → poll status: queued → running → success
```
```bash
Query Flow (sync):
POST /ask → Nginx → API → Vector Store (top-k)
→ Ollama (generate) → Answer + Sources
```
```bash
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
| API Server | FastAPI + Gunicorn + Uvicorn | HTTP endpoints, multi-process serving |
| Background Jobs | Celery 5.3 | Async ingestion task queue |
| Message Broker | Redis 7.2 | Job queue + result backend |
| Job Monitoring | Flower | Real-time Celery task dashboard |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, free, 384-dim vectors |
| LLM | Ollama (llama3.2:1b) | Local inference, no API cost |
| Vector DB | Chroma / Pinecone / MongoDB Atlas | Switchable backends |
| LLM Framework | LangChain | Vector store abstraction layer |
| Metrics | Prometheus + Grafana | System + business metrics |
| Data Versioning | DVC | Reproducible data pipelines |
| Containerization | Docker + Docker Compose | Full stack orchestration |
| Config | pydantic-settings + .env | Type-safe environment config |



## Project Structure
 ``` bash
---
rag-system/
├── api/
│   ├── main.py              # FastAPI app, all endpoints, Prometheus metrics
│   ├── middleware.py        # RequestID, Timing, ProcessTime middleware
│   └── schemas.py           # Pydantic request/response models
│
├── src/
│   ├── config.py            # Centralized settings via pydantic-settings
│   ├── pipeline.py          # ingest() + ask() — core entry points
│   │
│   ├── ingestion/
│   │   ├── loader.py        # PDF / DOCX / TXT document loader
│   │   └── chunker.py       # Recursive / Semantic / Sentence-window chunking
│   │
│   ├── embeddings/
│   │   └── embedder.py      # HuggingFace embeddings (LangChain interface)
│   │
│   ├── vectorstore/
│   │   └── store.py         # Multi-backend factory (Chroma/Pinecone/MongoDB)
│   │
│   ├── retrieval/
│   │   └── retriever.py     # Top-k retrieval wrapper
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
├── CHANGELOG.md             # Version history
└── .env.example             # Environment variable template
```
---

## Quickstart (Local)

# 1. Clone and create virtual environment
```bash
git clone <your-repo-url>
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
```
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
| http://localhost:5555 | Flower (Celery monitoring) |


---

## Quickstart (Docker — Full Production Stack)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env

# 2. Add documents
cp your_docs/*.pdf data/raw/

# 3. Start all 10 services
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
| GET | `/providers` | List vector DB backends + connection status |
| GET | `/strategies` | List chunking strategies + descriptions |
| GET | `/metrics` | Prometheus metrics endpoint |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |

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
| `MONGODB_ATLAS_URI` | MongoDB only | — | `mongodb+srv://...` |
| `MONGODB_DB_NAME` | No | `rag_system` | Atlas database name |
| `MONGODB_COLLECTION_NAME` | No | `document_chunks` | Atlas collection name |
| `MONGODB_VECTOR_INDEX_NAME` | No | `vector_index` | Atlas vector search index name |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/0` | Celery result store |
| `CHUNK_SIZE` | No | `500` | Words per chunk |
| `CHUNK_OVERLAP` | No | `50` | Overlap between chunks |
| `TOP_K` | No | `4` | Chunks retrieved per query |

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

## Versions

| Version | Tag | Description |
|---|---|---|
| v1.0.0 | `v1.0.0` | Basic RAG — Chroma + Ollama + FastAPI + DVC |
| v2.0.0 | `v2.0.0` | LangChain + Pinecone + MongoDB + advanced chunking |
| v2.1.0 | `v2.1.0` | Celery + Redis background jobs + Flower |
| v2.2.0 | `v2.2.0` | Nginx LB + Prometheus + Grafana + Gunicorn + auto-scaling |

---

