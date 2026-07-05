# RAG System

A production-grade Retrieval-Augmented Generation (RAG) pipeline for document
ingestion and question answering. Built with a microservices mindset —
FastAPI handles HTTP, Celery + Redis manage heavy ingestion jobs as
non-blocking background tasks, LangChain abstracts the vector store layer
so Chroma, Pinecone, and MongoDB Atlas are all switchable without touching
pipeline logic, and Ollama runs the LLM locally with no API cost. The entire
stack is containerized with Docker Compose (five services: API, Celery worker,
Flower monitor, Redis, Ollama) and data pipelines are versioned and
reproducible via DVC.


---

## Architecture
``` bash
Documents (PDF/DOCX/TXT)
│
▼
[ Loader ]  ──── src/ingestion/loader.py
│
▼
[ Chunker ]  ─── recursive | semantic | sentence_window
│
▼
[ Embedder ] ─── all-MiniLM-L6-v2 (local, HuggingFace)
│
▼
[ Vector Store ] ── Chroma (local) | Pinecone | MongoDB Atlas
│
(at query time)
│
▼
[ Retriever ] ── top-k similarity search
│
▼
[ Generator ] ── Ollama llama3.2:1b (local, free)
│
▼
[ Answer ]
POST /ingest
│
▼
[ FastAPI ] ──── returns job_id immediately (HTTP 202)
│
▼
[ Redis Queue ]
│
▼
[ Celery Worker ] ──── runs ingestion in background
│
▼
GET /jobs/{job_id} ──── poll: queued → running → success/failed
```
---

## Tech Stack

```
| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Background Jobs | Celery + Redis |
| Job Monitoring | Flower |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Ollama (llama3.2:1b — local, free) |
| Vector DB | Chroma / Pinecone / MongoDB Atlas (switchable) |
| LLM Framework | LangChain |
| Data Versioning | DVC |
| Containerization | Docker + docker-compose |
| Config | pydantic-settings + .env |

```
---

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Background Jobs | Celery + Redis |
| Job Monitoring | Flower |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Ollama (llama3.2:1b — local, free) |
| Vector DB | Chroma / Pinecone / MongoDB Atlas (switchable) |
| LLM Framework | LangChain |
| Data Versioning | DVC |
| Containerization | Docker + docker-compose |
| Config | pydantic-settings + .env |

---

## Quickstart (Local)

```bash
# 1. Clone and create virtual environment
git clone <your-repo-url>
cd rag-system
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add Pinecone key and MongoDB URI if using those backends

# 4. Start Redis (separate terminal)
docker run -d -p 6379:6379 redis:7.2-alpine

# 5. Start Ollama (separate terminal)
ollama serve
ollama pull llama3.2:1b

# 6. Start Celery worker (separate terminal)
celery -A src.worker.celery_app worker --loglevel=info --concurrency=2

# 7. Drop documents into data/raw/
cp your_docs/*.pdf data/raw/

# 8. Run DVC pipeline (ingest + evaluate)
dvc repro

# 9. Start the API
uvicorn api.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for Swagger UI.
Open **http://localhost:5555** for Flower job monitoring (start with `celery -A src.worker.celery_app flower`).

---

## Quickstart (Docker)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — add Pinecone key and MongoDB URI

# 2. Drop documents into data/raw/
cp your_docs/*.pdf data/raw/

# 3. Start all services
docker compose up --build

# 4. Submit an ingestion job
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"provider": "chroma", "strategy": "recursive", "reset": true}'

# 5. Poll job status (replace <job_id>)
curl http://localhost:8000/jobs/<job_id>

# 6. Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "provider": "chroma"}'
```

Services started by docker compose:

| Service | URL | Description |
|---|---|---|
| rag-api | http://localhost:8000 | FastAPI application |
| rag-worker | — | Celery background worker |
| rag-flower | http://localhost:5555 | Celery job monitoring UI |
| rag-redis | localhost:6379 | Redis broker + result backend |
| rag-ollama | localhost:11434 | Local LLM server |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System status + chunk counts per backend |
| POST | `/ingest` | Queue ingestion as background job → returns `job_id` |
| GET | `/jobs/{job_id}` | Poll background job status |
| DELETE | `/jobs/{job_id}/cancel` | Cancel a queued or running job |
| POST | `/ask` | Ask a question, get a grounded answer |
| GET | `/providers` | List vector DB backends + connection status |
| GET | `/strategies` | List chunking strategies + descriptions |
| GET | `/docs` | Interactive Swagger UI |

### POST /ingest
Returns immediately with a `job_id`. Ingestion runs in the background.

```json
{
  "provider": "chroma",
  "strategy": "recursive",
  "reset": true
}
```

Response (HTTP 202):
```json
{
  "job_id": "a3f8c2d1-...",
  "status": "queued",
  "provider": "chroma",
  "strategy": "recursive",
  "message": "Ingestion job queued. Poll /jobs/a3f8c2d1-... for status."
}
```

### GET /jobs/{job_id}
Poll this until `status` is `success` or `failed`.

```json
{
  "job_id": "a3f8c2d1-...",
  "status": "success",
  "result": {
    "documents_loaded": 3,
    "chunks_created": 96,
    "chunks_added": 96,
    "total_chunks_in_store": 96
  },
  "error": null,
  "progress": null
}
```

Possible status values: `queued` → `running` → `success` / `failed`

### POST /ask

```json
{
  "question": "What is this document about?",
  "provider": "chroma",
  "top_k": 4
}
```

---

## Chunking Strategies

| Strategy | How it works | Best for |
|---|---|---|
| `recursive` | Splits by paragraph → sentence → word boundary | General purpose, fast |
| `semantic` | Splits at embedding similarity boundaries | Long docs with topic shifts |
| `sentence_window` | One sentence per chunk + surrounding context in metadata | Precise Q&A |

---

## Vector DB Backends

| Backend | Type | Setup needed |
|---|---|---|
| `chroma` | Local file-persisted | None — works out of the box |
| `pinecone` | Managed cloud | API key + index (dim=384, cosine) |
| `mongodb` | MongoDB Atlas Vector Search | URI + Atlas vector search index |

---

## DVC Pipeline

```bash
dvc repro           # run full pipeline (ingest → evaluate)
dvc metrics show    # view ingestion + retrieval quality metrics
dvc params diff     # see what params changed vs last run
dvc dag             # visualize the pipeline graph
```

Pipeline stages defined in `dvc.yaml`:

| Stage | Script | Reruns when |
|---|---|---|
| `ingest` | `scripts/ingest.py` | `data/raw` or ingestion code changes |
| `evaluate` | `scripts/evaluate.py` | Ingest output or retrieval params change |

Metrics tracked per run:

| Metric | Description |
|---|---|
| `documents_loaded` | Number of source documents ingested |
| `chunks_created` | Total chunks after splitting |
| `avg_top1_score` | Average relevance score of best chunk per query |
| `avg_top_k_score` | Average relevance score across all retrieved chunks |

---

## Project Structure
```
rag-system/
├── api/
│   ├── main.py          # FastAPI app + endpoints
│   └── schemas.py       # Pydantic request/response models
├── src/
│   ├── config.py        # Centralized settings (pydantic-settings)
│   ├── ingestion/
│   │   ├── loader.py    # PDF/DOCX/TXT document loader
│   │   └── chunker.py   # Recursive/Semantic/Sentence-window chunking
│   ├── embeddings/
│   │   └── embedder.py  # HuggingFace embeddings (LangChain interface)
│   ├── vectorstore/
│   │   └── store.py     # Multi-backend factory (Chroma/Pinecone/MongoDB)
│   ├── retrieval/
│   │   └── retriever.py # Top-k retrieval wrapper
│   ├── generation/
│   │   └── generator.py # Ollama LLM generation
|   ├── worker/
│   │   ├── celery_app.py    # Celery app + configuration
│   │   └── tasks.py         # ingest_documents_task (background job)
│   └── pipeline.py      # ingest() + ask() — main entry points
├── workers/
│   ├── tasks.py        
│   └── celery_app.py  
├── scripts/
│   ├── ingest.py        # DVC-tracked ingestion script
│   └── evaluate.py      # DVC-tracked retrieval evaluation
├── data/
│   ├── raw/             # Source documents (DVC tracked)
│   ├── processed/       # DVC outputs (metrics, summaries)
│   └── vectorstore/     # Chroma persistence (volume mounted)
├── params.yaml          # DVC experiment parameters
├── dvc.yaml             # DVC pipeline definition
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── CHANGELOG.md
```
---

## Versions

| Version | Branch | Description |
|---|---|---|
| v1.0.0 | `main` (tagged) | Basic RAG — Chroma + Ollama + FastAPI + DVC |
| v2.0.0 | `main` (current) | LangChain + Pinecone + MongoDB + advanced chunking |

---

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VECTOR_DB_PROVIDER` | No | Default backend: `chroma` / `pinecone` / `mongodb` |
| `CHUNKING_STRATEGY` | No | Default strategy: `recursive` / `semantic` / `sentence_window` |
| `PINECONE_API_KEY` | Pinecone only | From https://app.pinecone.io |
| `PINECONE_INDEX_NAME` | Pinecone only | Must exist with dim=384, metric=cosine |
| `MONGODB_ATLAS_URI` | MongoDB only | `mongodb+srv://...` connection string |
| `OLLAMA_BASE_URL` | No | Default: `http://localhost:11434` |
| `EMBEDDING_MODEL` | No | Default: `all-MiniLM-L6-v2` |
| `LLM_MODEL` | No | Default: `llama3.2:1b` |
| `TOP_K` | No | Default: `4` |
| `REDIS_URL` | No | Default: `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | No | Default: `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | No | Default: `redis://localhost:6379/0` |

---

## Versions

| Version | Tag | Description |
|---|---|---|
| v1.0.0 | `v1.0.0` | Basic RAG — Chroma + Ollama + FastAPI + DVC |
| v2.0.0 | `v2.0.0` | LangChain + Pinecone + MongoDB + advanced chunking |
| v2.1.0 | `v2.1.0` | Celery + Redis background jobs + Flower monitoring |

Step 5 — Final commit and tags
bashgit add README.md CHANGELOG.md
git commit -m "docs: add README, CHANGELOG for v2.0.0 release"

# Retag v2.0.0 on this final commit
git tag -d v2.0.0
git tag -a v2.0.0 -m "v2.0.0 - Production RAG with multi-DB, LangChain, DVC pipeline"

Step 6 — Push to GitHub (if you have a remote)
bashgit remote add origin https://github.com/<your-username>/rag-system.git
git push -u origin main
git push origin release/v2.0.0
git push origin --tags

Final verification checklist
bash# Confirm both version tags exist
git tag -l
# Expected: v1.0.0  v2.0.0

# Confirm branch structure
git branch -a
# Expected: main, v2-langchain-multidb, release/v2.0.0

# Confirm DVC pipeline is clean
dvc status
# Expected: Data and pipelines are up to date

# Confirm full pipeline runs
dvc repro

# Confirm metrics
dvc metrics show

# Confirm API starts
uvicorn api.main:app --reload --port 8000

