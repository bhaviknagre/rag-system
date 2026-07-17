# API Endpoints

Base URL: `http://localhost` (via Nginx) or `http://localhost:8000` (direct)

## Authentication

`POST /ingest`, `POST /upload`, `POST /ask`, `GET /jobs/{job_id}`, and
`DELETE /jobs/{job_id}/cancel` require an `X-API-Key` header matching the
`API_KEY` environment variable:

```bash
curl -X POST http://localhost/ask \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

Missing or incorrect key returns `401 Unauthorized`. If `API_KEY` is unset,
auth is skipped (local/dev convenience) and a warning is logged once at
first request — see [Security Guide](../guides/security.md). `/health`,
`/providers`, `/strategies`, `/metrics`, and the web UI itself are not
gated.

---

## GET /health

System status and chunk counts across all vector store backends.

**Response**

```json
{
  "status": "ok",
  "default_provider": "chroma",
  "default_strategy": "recursive",
  "embedding_model": "all-MiniLM-L6-v2",
  "llm_model": "llama3.2:1b",
  "chunk_counts": {
    "chroma": 32,
    "pinecone": 32,
    "mongodb": 32
  }
}
```

---

## POST /ingest

Queue an ingestion job. Returns `job_id` immediately (HTTP 202).

**Request**

```json
{
  "provider": "chroma",
  "strategy": "recursive",
  "reset": true
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `provider` | string | env default | `chroma` \| `pinecone` \| `mongodb` |
| `strategy` | string | env default | `recursive` \| `semantic` \| `sentence_window` |
| `reset` | boolean | `false` | Wipe collection before ingesting |

**Response (HTTP 202)**

```json
{
  "job_id": "a3f8c2d1-4b5e-...",
  "status": "queued",
  "provider": "chroma",
  "strategy": "recursive",
  "message": "Ingestion queued. Poll /jobs/a3f8c2d1-... for status."
}
```

---

## GET /jobs/{job_id}

Poll background ingestion job status.

**Job states:** `queued` → `running` → `success` / `failed`

**Response (success)**

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

---

## POST /ask

Retrieve context and generate a grounded answer.

**Request**

```json
{
  "question": "What is this document about?",
  "provider": "chroma",
  "top_k": 5
}
```

**Response**

```json
{
  "question": "What is this document about?",
  "answer": "The document covers...",
  "provider": "chroma",
  "sources": [
    {
      "doc_id": "report.pdf",
      "source": "data/raw/report.pdf",
      "score": 0.87,
      "strategy": "recursive"
    }
  ]
}
```

---

## POST /upload

Upload a document file and optionally trigger ingestion immediately.

**Request (multipart/form-data)**

| Field | Type | Description |
|---|---|---|
| `file` | File | `.pdf`, `.docx`, or `.txt` (max 100MB) |
| `ingest_immediately` | bool | Queue ingestion after upload |
| `provider` | string | Vector DB backend |
| `strategy` | string | Chunking strategy |

---

## GET /providers

List all vector DB backends with connection status.

## GET /strategies

List all chunking strategies with descriptions.

## GET /metrics

Prometheus metrics endpoint (scraped by Prometheus every 15s).

## GET /rag-system

Full RAG web UI — drag-and-drop upload + question answering interface
(serves `static/index.html`).