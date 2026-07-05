# RAG System

A production-grade Retrieval-Augmented Generation pipeline built for
document ingestion and question answering. Supports multiple vector
database backends and advanced chunking strategies, exposed via a
FastAPI service and containerized with Docker.

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
```
---

## Tech Stack

```
| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Ollama (llama3.2:1b — local, free) |
| Vector DB | Chroma / Pinecone / MongoDB Atlas (switchable) |
| LLM Framework | LangChain |
| Data Versioning | DVC |
| Containerization | Docker + docker-compose |
| Config | pydantic-settings + .env |
```
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
# 🔧 Edit .env — add Pinecone key and MongoDB URI if using those backends

# 4. Start Ollama (separate terminal)
ollama serve
ollama pull llama3.2:1b

# 5. Drop documents into data/raw/
cp your_docs/*.pdf data/raw/

# 6. Ingest + run the pipeline
dvc repro

# 7. Start the API
uvicorn api.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Quickstart (Docker)

```bash
# 1. Configure environment
cp .env.example .env
# 🔧 Edit .env — add Pinecone key and MongoDB URI

# 2. Drop documents into data/raw/
cp your_docs/*.pdf data/raw/

# 3. Start everything
docker compose up --build

# 4. Ingest via API
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"provider": "chroma", "strategy": "recursive", "reset": true}'
```

---

## API Reference
```
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System status + chunk counts per backend |
| POST | `/ingest` | Ingest docs with chosen provider + strategy |
| POST | `/ask` | Ask a question, get a grounded answer |
| GET | `/providers` | List vector DB backends + connection status |
| GET | `/strategies` | List chunking strategies + descriptions |
| GET | `/docs` | Interactive Swagger UI |
```
### POST /ingest

```json
{
  "provider": "chroma",
  "strategy": "recursive",
  "reset": true
}
```

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
| `recursive` | Splits by paragraph → sentence → word | General purpose, fast |
| `semantic` | Splits at embedding similarity boundaries | Long docs with topic shifts |
| `sentence_window` | One sentence per chunk + surrounding context in metadata | Precise Q&A |

---

## Vector DB Backends

| Backend | Type | Setup needed |
|---|---|---|
| `chroma` | Local file-persisted | None — works out of the box |
| `pinecone` | Managed cloud | API key + index (dim=384, cosine) |
| `mongodb` | MongoDB Atlas Vector Search | URI + vector search index |

---

## DVC Pipeline

```bash
dvc repro          # run full pipeline (ingest → evaluate)
dvc metrics show   # view ingestion + retrieval quality metrics
dvc params diff    # see what params changed vs last run
dvc dag            # visualize the pipeline graph
```

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

