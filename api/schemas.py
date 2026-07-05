from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any


# ── Ingest ───────────────────────────────────

class IngestRequest(BaseModel):
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = Field(
        None,
        description="Vector DB backend. Defaults to VECTOR_DB_PROVIDER in .env"
    )
    strategy: Optional[Literal["recursive", "semantic", "sentence_window"]] = Field(
        None,
        description="Chunking strategy. Defaults to CHUNKING_STRATEGY in .env"
    )
    reset: bool = Field(
        False,
        description="Wipe existing collection before ingesting"
    )


class IngestResponse(BaseModel):
    status: str
    provider: str
    strategy: str
    documents_loaded: int
    chunks_created: int = 0
    chunks_added: int = 0
    total_chunks_in_store: int = 0


# ── Ask ──────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = Field(None)
    top_k: Optional[int] = Field(None, ge=1, le=20)


class SourceItem(BaseModel):
    doc_id: str
    source: str
    score: float
    strategy: str


class AskResponse(BaseModel):
    question: str
    answer: str
    provider: str
    sources: List[SourceItem]


# ── Health ───────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    default_provider: str
    default_strategy: str
    embedding_model: str
    llm_model: str
    chunk_counts: dict


# ── Jobs (Celery background tasks) ───────────

class JobSubmittedResponse(BaseModel):
    job_id: str = Field(..., description="Use this ID to poll /jobs/{job_id}")
    status: str = Field("queued", description="Initial status — always 'queued'")
    provider: str
    strategy: str
    message: str = "Ingestion job queued. Poll /jobs/{job_id} for status."


class JobStatusResponse(BaseModel):
    job_id: str
    status: str = Field(
        ...,
        description="queued | running | success | failed"
    )
    result: Optional[Any] = Field(
        None,
        description="Populated when status=success. Contains ingestion summary."
    )
    error: Optional[str] = Field(
        None,
        description="Populated when status=failed. Contains error message."
    )
    progress: Optional[dict] = Field(
        None,
        description="Populated when status=running. Contains current step."
    )