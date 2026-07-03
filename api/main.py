import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AskRequest, AskResponse, SourceItem,
    IngestRequest, IngestResponse,
    HealthResponse
)
from src.pipeline import ingest, ask
from src.vectorstore.store import count_chunks
from src.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings()

app = FastAPI(
    title="RAG System API — v2",
    description=(
        "Production-grade Retrieval-Augmented Generation pipeline. "
        "Supports Chroma / Pinecone / MongoDB Atlas as vector backends "
        "and Recursive / Semantic / Sentence-Window chunking strategies."
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health]
@app.get("/health", response_model=HealthResponse)
def health_check():
    chunk_counts = {}
    for provider in ["chroma", "pinecone", "mongodb"]:
        try:
            chunk_counts[provider] = count_chunks(provider)
        except Exception as e:
            chunk_counts[provider] = f"error: {str(e)[:60]}"

    return HealthResponse(
        status="ok",
        default_provider=settings.vector_db_provider,
        default_strategy=settings.chunking_strategy,
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
        chunk_counts=chunk_counts
    )


# Ingest
@app.post("/ingest", response_model=IngestResponse)
def ingest_documents(request: IngestRequest):
    try:
        result = ingest(
            provider=request.provider,
            strategy=request.strategy,
            reset=request.reset
        )
        return IngestResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# Ask
@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    try:
        result = ask(
            question=request.question,
            provider=request.provider,
            top_k=request.top_k
        )
        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            provider=result["provider"],
            sources=[SourceItem(**s) for s in result["sources"]]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}")


# Info endpoints
@app.get("/providers")
def list_providers():
    statuses = {}
    for provider in ["chroma", "pinecone", "mongodb"]:
        try:
            count = count_chunks(provider)
            statuses[provider] = {
                "status": "connected",
                "chunks": count
            }
        except Exception as e:
            statuses[provider] = {
                "status": "unavailable",
                "error": str(e)[:100]
            }
    return {
        "default": settings.vector_db_provider,
        "providers": statuses
    }


@app.get("/strategies")
def list_strategies():
    return {
        "default": settings.chunking_strategy,
        "strategies": {
            "recursive": "Structure-aware splitting. Fast, general purpose. Best default choice.",
            "semantic": "Embedding-based splitting at meaning boundaries. Slowest, most accurate.",
            "sentence_window": "One sentence per chunk with surrounding context in metadata. Best for Q&A."
        }
    }


@app.get("/")
def root():
    return {
        "message": "RAG System API v2 is running",
        "docs": "/docs",
        "endpoints": ["/health", "/ingest", "/ask", "/providers", "/strategies"]
    }



"""
Endpoints:
    GET  /health          -> system info + chunk counts across all backends
    POST /ingest          -> ingest docs with chosen provider + strategy
    POST /ask             -> ask a question against chosen provider
    GET  /providers       -> list available vector DB backends
    GET  /strategies      -> list available chunking strategies
"""

