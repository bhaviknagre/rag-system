import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AskRequest, AskResponse, SourceItem,
    IngestRequest, JobSubmittedResponse, JobStatusResponse,
    HealthResponse
)
from src.pipeline import ask
from src.vectorstore.store import count_chunks
from src.config import settings
from src.worker.celery_app import celery_app
from src.worker.tasks import ingest_documents_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG System API — v2",
    description=(
        "Production-grade RAG pipeline with background ingestion via Celery + Redis. "
        "POST /ingest returns a job_id immediately. Poll GET /jobs/{job_id} for status."
    ),
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ───────────────────────────────────

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


# ── Ingest (background job) ──────────────────

@app.post("/ingest", response_model=JobSubmittedResponse, status_code=202)
def ingest_documents(request: IngestRequest):
    provider = request.provider or settings.vector_db_provider
    strategy = request.strategy or settings.chunking_strategy

    try:
        task = ingest_documents_task.apply_async(
            kwargs={
                "provider": provider,
                "strategy": strategy,
                "reset": request.reset,
                "raw_dir": "data/raw"
            }
        )

        logger.info(f"Ingestion job queued | job_id={task.id} | provider={provider}")

        return JobSubmittedResponse(
            job_id=task.id,
            status="queued",
            provider=provider,
            strategy=strategy,
            message=f"Ingestion job queued. Poll /jobs/{task.id} for status."
        )

    except Exception as e:
        logger.error(f"Failed to queue ingestion job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue ingestion job: {e}"
        )


# ── Job status ───────────────────────────────

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    try:
        task_result = celery_app.AsyncResult(job_id)
        celery_state = task_result.state
        if celery_state == "PENDING":
            return JobStatusResponse(
                job_id=job_id,
                status="queued",
                result=None,
                error=None,
                progress=None
            )

        elif celery_state == "STARTED" or celery_state == "PROGRESS":
            meta = task_result.info or {}
            return JobStatusResponse(
                job_id=job_id,
                status="running",
                result=None,
                error=None,
                progress={
                    "step": meta.get("step", "processing"),
                    "provider": meta.get("provider", ""),
                    "strategy": meta.get("strategy", "")
                }
            )

        elif celery_state == "SUCCESS":
            return JobStatusResponse(
                job_id=job_id,
                status="success",
                result=task_result.result,
                error=None,
                progress=None
            )

        elif celery_state == "FAILURE":
            error_info = task_result.info
            error_msg = str(error_info) if error_info else "Unknown error"
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                result=None,
                error=error_msg,
                progress=None
            )

        elif celery_state == "RETRY":
            return JobStatusResponse(
                job_id=job_id,
                status="running",
                result=None,
                error=None,
                progress={"step": "retrying after error"}
            )

        else:
            return JobStatusResponse(
                job_id=job_id,
                status="unknown",
                result=None,
                error=f"Unexpected Celery state: {celery_state}",
                progress=None
            )

    except Exception as e:
        logger.error(f"Failed to fetch job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch job status: {e}"
        )


@app.delete("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """
    Attempts to cancel a queued or running job.
    Queued jobs are cancelled cleanly.
    Running jobs receive a termination signal — may not stop instantly.
    """
    try:
        celery_app.control.revoke(job_id, terminate=True, signal="SIGTERM")
        return {
            "job_id": job_id,
            "status": "cancellation_requested",
            "message": "Cancellation signal sent. Job may take a moment to stop."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {e}")

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

@app.get("/providers")
def list_providers():
    statuses = {}
    for provider in ["chroma", "pinecone", "mongodb"]:
        try:
            count = count_chunks(provider)
            statuses[provider] = {"status": "connected", "chunks": count}
        except Exception as e:
            statuses[provider] = {"status": "unavailable", "error": str(e)[:100]}
    return {"default": settings.vector_db_provider, "providers": statuses}


@app.get("/strategies")
def list_strategies():
    return {
        "default": settings.chunking_strategy,
        "strategies": {
            "recursive": "Structure-aware splitting. Fast, general purpose.",
            "semantic": "Embedding-based splitting at meaning boundaries. Slowest, most accurate.",
            "sentence_window": "One sentence per chunk + surrounding context in metadata. Best for Q&A."
        }
    }


@app.get("/")
def root():
    return {
        "message": "RAG System API v2.1.0 is running",
        "docs": "/docs",
        "endpoints": ["/health", "/ingest", "/jobs/{job_id}", "/ask", "/providers", "/strategies"]
    }


"""
Endpoints:
    GET  /health              -> system status + chunk counts
    POST /ingest              -> queue ingestion as background job, returns job_id
    GET  /jobs/{job_id}       -> poll ingestion job status
    GET  /jobs/{job_id}/cancel -> cancel a queued/running job
    POST /ask                 -> ask a question (synchronous)
    GET  /providers           -> list vector DB backends
    GET  /strategies          -> list chunking strategies
"""