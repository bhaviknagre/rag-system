from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# Ingest
class IngestRequest(BaseModel):
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = Field(
        None,
        description="Vector DB backend to use. Defaults to VECTOR_DB_PROVIDER in .env"
    )
    strategy: Optional[Literal["recursive", "semantic", "sentence_window"]] = Field(
        None,
        description="Chunking strategy. Defaults to CHUNKING_STRATEGY in .env"
    )
    reset: bool = Field(
        False,
        description="If true, wipe the existing collection before ingesting"
    )


class IngestResponse(BaseModel):
    status: str
    provider: str
    strategy: str
    documents_loaded: int
    chunks_created: int = 0
    chunks_added: int = 0
    total_chunks_in_store: int = 0


# Ask
class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The question to ask the RAG system"
    )
    provider: Optional[Literal["chroma", "pinecone", "mongodb"]] = Field(
        None,
        description="Vector DB backend to query. Defaults to VECTOR_DB_PROVIDER in .env"
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve. Defaults to TOP_K in .env"
    )


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


# Health

class HealthResponse(BaseModel):
    status: str
    default_provider: str
    default_strategy: str
    embedding_model: str
    llm_model: str
    chunk_counts: dict