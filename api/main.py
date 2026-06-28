from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AskRequest, AskResponse, SourceItem,
    IngestRequest, IngestResponse,
    HealthResponse
)
from src.pipeline import ask, raw_ingest
from src.vectorstore.store import get_vector_store
from src.config import settings

app = FastAPI(
    title="RAG System API",
    description="A basic Retrieval-Augmented Generation system for document Q&A",
    version="1.0.0"
)

# Allow local frontend / testing tools to call this freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Basic health check, also confirms vector store is reachable."""
    try:
        store = get_vector_store()
        return HealthResponse(
            status="ok",
            vector_store_chunks=store.count(),
            embedding_model=settings.embedding_model,
            llm_model=settings.llm_model
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


@app.post("/ingest", response_model=IngestResponse)
def ingest_documents(request: IngestRequest):
    """
    Ingests all documents from data/raw/ into the vector store.
    Set reset=true to wipe the existing collection first.
    """
    try:
        result = raw_ingest(reset=request.reset)
        return IngestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """
    Retrieves relevant context for the question and generates a grounded answer.
    """
    try:
        result = ask(request.question, top_k=request.top_k)
        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            sources=[SourceItem(**s) for s in result["sources"]]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {e}")


@app.get("/")
def root():
    return {
        "message": "RAG System API is running",
        "docs": "/docs",
        "endpoints": ["/health", "/ingest", "/ask"]
    }