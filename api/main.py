import time
import logging
import json
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    ProcessTimeHeaderMiddleware
)
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
from src.monitoring.metrics import (
    record_ask,
    record_ingest_submitted,
    update_vector_store_gauges,
    init_system_info,
    record_ingest_completed
)

# Structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
)
logger = logging.getLogger(__name__)


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({"event": "startup", "version": "2.1.0"}))
    init_system_info(settings)
    update_vector_store_gauges()
    yield
    logger.info(json.dumps({"event": "shutdown"}))


# App
app = FastAPI(
    title="RAG System API",
    description=(
        "Production-grade RAG pipeline. "
        "POST /ingest queues background job via Celery + Redis. "
        "POST /ask retrieves context and generates grounded answer via local LLM."
    ),
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware (order matters — outermost runs first)
app.add_middleware(ProcessTimeHeaderMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus auto-instrumentation
# Instruments all routes automatically, exposes /metrics
Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health", "/nginx-health"]
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# Health

@app.get("/health", response_model=HealthResponse)
def health_check():
    chunk_counts = {}

    # Chroma is local and fast — always check it
    try:
        chunk_counts["chroma"] = count_chunks("chroma")
    except Exception as e:
        chunk_counts["chroma"] = f"error: {str(e)[:40]}"

    # Cloud backends — skip if they're slow, don't block health check
    for provider in ["pinecone", "mongodb"]:
        try:
            chunk_counts[provider] = count_chunks(provider)
        except Exception:
            chunk_counts[provider] = "unavailable"

    update_vector_store_gauges()

    return HealthResponse(
        status="ok",
        default_provider=settings.vector_db_provider,
        default_strategy=settings.chunking_strategy,
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
        chunk_counts=chunk_counts
    )

# Ingest

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
        record_ingest_submitted(provider=provider, strategy=strategy)
        logger.info(json.dumps({
            "event": "ingest_queued",
            "job_id": task.id,
            "provider": provider,
            "strategy": strategy
        }))
        return JobSubmittedResponse(
            job_id=task.id,
            status="queued",
            provider=provider,
            strategy=strategy,
            message=f"Ingestion queued. Poll /jobs/{task.id} for status."
        )
    except Exception as e:
        logger.error(json.dumps({"event": "ingest_queue_failed", "error": str(e)}))
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {e}")


# Job status

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    try:
        task_result = celery_app.AsyncResult(job_id)
        state = task_result.state

        if state == "PENDING":
            return JobStatusResponse(job_id=job_id, status="queued")

        elif state in ("STARTED", "PROGRESS"):
            meta = task_result.info or {}
            return JobStatusResponse(
                job_id=job_id,
                status="running",
                progress={
                    "step": meta.get("step", "processing"),
                    "provider": meta.get("provider", ""),
                    "strategy": meta.get("strategy", "")
                }
            )

        elif state == "SUCCESS":
            result = task_result.result
            record_ingest_completed(
                provider=result.get("provider", "unknown"),
                strategy=result.get("strategy", "unknown"),
                status="success",
                chunks=result.get("chunks_added", 0)
            )
            return JobStatusResponse(
                job_id=job_id,
                status="success",
                result=result
            )

        elif state == "FAILURE":
            error_msg = str(task_result.info) if task_result.info else "Unknown error"
            record_ingest_completed(
                provider="unknown", strategy="unknown", status="failed"
            )
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                error=error_msg
            )

        elif state == "RETRY":
            return JobStatusResponse(
                job_id=job_id,
                status="running",
                progress={"step": "retrying after error"}
            )

        else:
            return JobStatusResponse(
                job_id=job_id,
                status="unknown",
                error=f"Unexpected state: {state}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job status: {e}")


@app.delete("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    try:
        celery_app.control.revoke(job_id, terminate=True, signal="SIGTERM")
        return {
            "job_id": job_id,
            "status": "cancellation_requested",
            "message": "Cancellation signal sent."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel: {e}")


# Ask

@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    provider = request.provider or settings.vector_db_provider
    start = time.time()

    try:
        result = ask(
            question=request.question,
            provider=provider,
            top_k=request.top_k
        )
        latency = time.time() - start
        record_ask(
            provider=provider,
            latency=latency,
            sources=result["sources"]
        )
        logger.info(json.dumps({
            "event": "ask_completed",
            "provider": provider,
            "latency_ms": round(latency * 1000, 2),
            "sources_count": len(result["sources"])
        }))
        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            provider=result["provider"],
            sources=[SourceItem(**s) for s in result["sources"]]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(json.dumps({"event": "ask_failed", "error": str(e)}))
        raise HTTPException(status_code=500, detail=f"Failed: {e}")


# Info

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
            "sentence_window": "One sentence per chunk + surrounding context. Best for Q&A."
        }
    }


@app.get("/")
def root():
    return {
        "message": "RAG System API v2.1.0",
        "docs": "/docs",
        "metrics": "/metrics",
        "endpoints": ["/health", "/ingest", "/jobs/{job_id}", "/ask", "/providers", "/strategies"]
    }

# Upload

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 100 * 1024 * 1024


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    ingest_immediately: bool = Form(default=True),
    provider: Optional[str] = Form(default=None),
    strategy: Optional[str] = Form(default=None),
):
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}"
        )

    save_dir = Path("data/raw")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / file.filename

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        await file.close()

    file_size = os.path.getsize(save_path)
    logger.info(json.dumps({
        "event": "file_uploaded",
        "filename": file.filename,
        "size_bytes": file_size
    }))

    job_id = None
    if ingest_immediately:
        active_provider = provider or settings.vector_db_provider
        active_strategy = strategy or settings.chunking_strategy
        task = ingest_documents_task.apply_async(
            kwargs={
                "provider": active_provider,
                "strategy": active_strategy,
                "reset": False,
                "raw_dir": "data/raw"
            }
        )
        job_id = task.id
        record_ingest_submitted(
            provider=active_provider,
            strategy=active_strategy
        )

    response = {
        "filename": file.filename,
        "saved_to": str(save_path),
        "size_bytes": file_size,
        "message": f"File uploaded successfully."
    }

    if job_id:
        response["job_id"] = job_id
        response["message"] += f" Ingestion queued — poll /jobs/{job_id} for status."

    return response


static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/rag-system", include_in_schema=False)
def serve_ui():
    return FileResponse("static/index.html")