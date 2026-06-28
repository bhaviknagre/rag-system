# RAG System — Document Q&A with Local LLM

A basic but complete Retrieval-Augmented Generation (RAG) system that ingests documents,
stores them in a vector database, and answers natural language questions grounded in
their content — using a fully local, free LLM (no API costs).

Built end-to-end with proper data engineering and MLOps practices: DVC for data/pipeline
versioning, FastAPI for serving, and Docker for containerized deployment.

---

## Features

- **Multi-format ingestion**: `.txt`, `.pdf`, `.docx`
- **Chunking** with configurable size/overlap to preserve context across boundaries
- **Local embeddings** via `sentence-transformers` (no API key required)
- **Vector storage** with ChromaDB (persistent, on-disk)
- **Local LLM generation** via Ollama (`llama3.2:1b`) — completely free, no external API calls
- **REST API** via FastAPI with auto-generated Swagger docs
- **Containerized** with Docker Compose (API + Ollama as separate services)
- **Data versioning** with DVC — reproducible ingestion pipeline

---

## Architecture

```
data/raw/  (.txt, .pdf, .docx)
     │
     ▼
  Loader          extracts plain text
     │
     ▼
  Chunker         splits into overlapping chunks
     │
     ▼
  Embedder        sentence-transformers (local)
     │
     ▼
 ChromaDB         persistent vector store
     │
     ├──────────────────┐
     ▼                  ▼
  Retriever         FastAPI
     │               /ask
     ▼               /ingest
  Generator         /health
  (Ollama)
```


**Flow for `/ask`:** question → embed query → similarity search in Chroma → retrieve top-k
chunks → build context → pass to local LLM via Ollama → return grounded answer + sources.

**Flow for `/ingest`:** load files from `data/raw/` → chunk → embed → upsert into Chroma.

---

## Tech Stack

| Layer            | Technology                          |
|-------------------|--------------------------------------|
| Document parsing  | `pypdf`, `python-docx`               |
| Embeddings        | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector store      | ChromaDB (persistent client)         |
| LLM               | Ollama (`llama3.2:1b`) — local, free |
| API               | FastAPI + Uvicorn                    |
| Config            | `pydantic-settings` + `.env`         |
| Data versioning   | DVC                                  |
| Containerization  | Docker + Docker Compose              |

---

## Project Structure

```
rag-system/
├── data/
│   ├── raw/                    # source documents (DVC-tracked)
│   ├── processed/              # reserved for intermediate artifacts
│   └── vectorstore/            # ChromaDB persistent storage
├── src/
│   ├── config.py               # centralized settings (.env-driven)
│   ├── ingestion/
│   │   ├── loader.py           # multi-format document loading
│   │   └── chunker.py          # text chunking with overlap
│   ├── embeddings/
│   │   └── embedder.py         # sentence-transformers wrapper
│   ├── vectorstore/
│   │   └── store.py            # ChromaDB add/query/reset
│   ├── retrieval/
│   │   └── retriever.py        # retrieval + context formatting
│   ├── generation/
│   │   └── generator.py        # Ollama-based answer generation
│   └── pipeline.py             # orchestrates ingest() + ask()
├── api/
│   ├── main.py                 # FastAPI app: /health /ingest /ask
│   └── schemas.py              # Pydantic request/response models
├── scripts/
│   └── ingest.py               # CLI ingestion entrypoint
├── dvc.yaml                    # DVC pipeline definition
├── dvc.lock                    # DVC pipeline state (auto-generated)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd rag-system
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

`.env` contents:
```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=llama3.2:1b
OLLAMA_BASE_URL=http://localhost:11434
CHROMA_PERSIST_DIR=./data/vectorstore
CHROMA_COLLECTION_NAME=rag_documents
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=4
```

No API keys required — everything runs locally.

### 3. Install and run Ollama

```bash
# Install from https://ollama.com/download
ollama pull llama3.2:1b
ollama serve   # usually runs automatically after install
```

### 4. Add documents

Drop `.txt`, `.pdf`, or `.docx` files into `data/raw/`.

---

## Usage

### Ingest documents

```bash
python scripts/ingest.py            # incremental
python scripts/ingest.py --reset    # wipe and rebuild vector store
```

### Run the API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

**Endpoints:**

| Method | Path       | Description                              |
|--------|-----------|-------------------------------------------|
| GET    | `/health` | Health check + system info                |
| POST   | `/ingest` | Ingest documents from `data/raw/`          |
| POST   | `/ask`    | Ask a question, get a grounded answer      |

**Example:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "top_k": 3}'
```

### Run via Docker Compose

```bash
docker compose up --build
docker exec -it rag-ollama ollama pull llama3.2:1b   # one-time, inside container
```

Then visit `http://localhost:8000/docs` as before.

---

## Data Versioning with DVC

This project uses DVC to track raw data and pipeline reproducibility, separate from git
(which tracks only code and small pointer files).

```bash
dvc repro       # run the ingestion pipeline if inputs changed
dvc status      # check if pipeline is up to date
dvc dag         # visualize the pipeline graph
```

`data/raw` is tracked via `data/raw.dvc`; `dvc.yaml` defines the ingestion stage with its
dependencies (loader/chunker/store code + raw data) and output (`data/vectorstore`).

---

## Design Decisions

- **Local LLM over OpenAI**: avoids API costs and keys for a learning/demo project, while
  still demonstrating real LLM integration patterns (prompt templating, grounded generation).
- **ChromaDB over a managed vector DB**: lightweight, file-based, zero infra to stand up,
  while still using a real ANN-based similarity search engine (cosine distance, HNSW index).
- **Word-count-based chunking**: simple, dependency-light, and easy to reason about — chosen
  over heavier semantic chunking for transparency in this version.
- **Singleton patterns** for embedder/vector store/generator: avoids reloading expensive
  models (embedding model, Chroma client) on every request.

---

## Known Limitations / Next Steps

- No authentication on API endpoints (fine for local/demo use, not production-ready as-is)
- No automated tests yet
- Chunking is character/word-based rather than semantic
- Single-node Chroma, no horizontal scaling
- No CI/CD pipeline yet
