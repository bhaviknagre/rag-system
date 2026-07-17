from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Ingestion metrics
INGEST_JOBS_SUBMITTED = Counter(
    "rag_ingest_jobs_submitted_total",
    "Total ingestion jobs submitted",
    ["provider", "strategy"]
)

INGEST_JOBS_COMPLETED = Counter(
    "rag_ingest_jobs_completed_total",
    "Total ingestion jobs completed",
    ["provider", "strategy", "status"]
)

INGEST_CHUNKS_CREATED = Counter(
    "rag_ingest_chunks_created_total",
    "Total chunks created across all ingestion jobs",
    ["provider", "strategy"]
)

# Retrieval metrics
ASK_REQUESTS = Counter(
    "rag_ask_requests_total",
    "Total /ask requests",
    ["provider"]
)

ASK_LATENCY = Histogram(
    "rag_ask_latency_seconds",
    "End-to-end latency for /ask requests",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

RETRIEVAL_SCORES = Histogram(
    "rag_retrieval_top1_score",
    "Top-1 relevance score from vector store",
    ["provider"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

EMPTY_RETRIEVALS = Counter(
    "rag_empty_retrievals_total",
    "Queries that returned zero chunks from the vector store",
    ["provider"]
)

# Vector store metrics
VECTOR_STORE_CHUNKS = Gauge(
    "rag_vector_store_chunks",
    "Current number of chunks in each vector store",
    ["provider"]
)

# LLM metrics
LLM_LATENCY = Histogram(
    "rag_llm_generation_latency_seconds",
    "Time spent waiting for LLM to generate answer",
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

LLM_ERRORS = Counter(
    "rag_llm_errors_total",
    "Total LLM generation errors (connection refused, timeout, etc.)"
)

# System info
SYSTEM_INFO = Info(
    "rag_system",
    "Static info about the RAG system configuration"
)


def record_ask(provider: str, latency: float, sources: list):
    ASK_REQUESTS.labels(provider=provider).inc()
    ASK_LATENCY.labels(provider=provider).observe(latency)

    if sources:
        top_score = sources[0].get("score", 0)
        RETRIEVAL_SCORES.labels(provider=provider).observe(top_score)
    else:
        EMPTY_RETRIEVALS.labels(provider=provider).inc()


def record_ingest_submitted(provider: str, strategy: str):
    INGEST_JOBS_SUBMITTED.labels(provider=provider, strategy=strategy).inc()


def record_ingest_completed(provider: str, strategy: str, status: str, chunks: int = 0):
    INGEST_JOBS_COMPLETED.labels(
        provider=provider, strategy=strategy, status=status
    ).inc()
    if chunks > 0:
        INGEST_CHUNKS_CREATED.labels(
            provider=provider, strategy=strategy
        ).inc(chunks)


def update_vector_store_gauges():
    from src.vectorstore.store import count_chunks
    for provider in ["chroma", "pinecone", "mongodb"]:
        try:
            count = count_chunks(provider)
            if count >= 0:
                VECTOR_STORE_CHUNKS.labels(provider=provider).set(count)
        except Exception:
            pass


def init_system_info(settings):
    SYSTEM_INFO.info({
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model,
        "default_provider": settings.vector_db_provider,
        "default_strategy": settings.chunking_strategy,
        "version": "2.1.0"
    })