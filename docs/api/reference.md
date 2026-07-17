# API Schemas

All request and response models are defined using Pydantic v2.
Every field is validated automatically — invalid input returns HTTP 422.

---

## Request Schemas

### IngestRequest

```python
class IngestRequest(BaseModel):
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = None
    strategy: Optional[Literal["recursive", "semantic", "sentence_window"]] = None
    reset: bool = False
```

| Field | Type | Default | Description |
|---|---|---|---|
| `provider` | string | `VECTOR_DB_PROVIDER` env | Vector DB backend |
| `strategy` | string | `CHUNKING_STRATEGY` env | Chunking strategy |
| `reset` | boolean | `false` | Wipe collection before ingesting |

---

### AskRequest

```python
class AskRequest(BaseModel):
    question: str          # min_length=1
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = None
    top_k: Optional[int] = None  # ge=1, le=20
```

| Field | Type | Default | Description |
|---|---|---|---|
| `question` | string | required | Must be non-empty |
| `provider` | string | `VECTOR_DB_PROVIDER` env | Backend to query |
| `top_k` | integer | `TOP_K` env (5) | Chunks to retrieve (1-20) |

---

### UploadRequest (multipart/form-data)

| Field | Type | Default | Description |
|---|---|---|---|
| `file` | File | required | `.pdf`, `.docx`, `.txt` — max 100MB |
| `ingest_immediately` | boolean | `true` | Queue ingestion after upload |
| `provider` | string | env default | Vector DB backend |
| `strategy` | string | env default | Chunking strategy |

---

## Response Schemas

### JobSubmittedResponse

Returned by `POST /ingest` and `POST /upload` when `ingest_immediately=true`.

```json
{
  "job_id": "a3f8c2d1-4b5e-4b3a-8d6e-1234567890ab",
  "status": "queued",
  "provider": "chroma",
  "strategy": "recursive",
  "message": "Ingestion queued. Poll /jobs/a3f8c2d1-... for status."
}
```

---

### JobStatusResponse

Returned by `GET /jobs/{job_id}`.

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

| `status` | `result` | `error` | `progress` |
|---|---|---|---|
| `queued` | null | null | null |
| `running` | null | null | `{"step": "loading documents"}` |
| `success` | ingestion summary | null | null |
| `failed` | null | error message | null |

---

### AskResponse

```json
{
  "question": "What is this document about?",
  "answer": "The document covers Terraform infrastructure management...",
  "provider": "chroma",
  "sources": [
    {
      "doc_id": "sample.pdf",
      "source": "data/raw/sample.pdf",
      "score": 0.8733,
      "strategy": "recursive"
    }
  ]
}
```

!!! note "Score interpretation"
    Score values differ by backend:

    - **Chroma** — cosine distance (lower = more similar, 0 = perfect match)
    - **Pinecone** — cosine similarity (higher = more similar, 1 = perfect match)
    - **MongoDB Atlas** — cosine similarity (higher = more similar)

---

### HealthResponse

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

## HTTP Status Codes

| Code | Meaning | When |
|---|---|---|
| `200 OK` | Success | `GET` requests, `/ask`, `/health` |
| `202 Accepted` | Job queued | `POST /ingest`, `POST /upload` |
| `400 Bad Request` | Validation error | Empty question, bad provider |
| `422 Unprocessable Entity` | Schema error | Missing required field, wrong type |
| `401 Unauthorized` | Missing/invalid API key | `X-API-Key` header absent or wrong, and `API_KEY` is set on the server |
| `429 Too Many Requests` | Rate limited | Nginx rate limit exceeded |
| `500 Internal Server Error` | Server error | LLM unavailable, vector store error |

---

## Error Response Format

```json
{
  "detail": "Question cannot be empty"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "question"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```