import logging
from celery import states
from celery.exceptions import Ignore, SoftTimeLimitExceeded
from src.worker.celery_app import celery_app
from src.pipeline import ingest

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.ingest_documents",
    max_retries=2,
    soft_time_limit=600,
    time_limit=660
)
def ingest_documents_task(
    self,
    provider: str,
    strategy: str,
    reset: bool,
    raw_dir: str = "data/raw"
):
    """
    Background ingestion task.

    States:
        PENDING  -> queued, not yet picked up
        STARTED  -> worker picked it up
        PROGRESS -> actively running (pushed manually)
        SUCCESS  -> finished, result in Redis
        FAILURE  -> crashed, error in Redis
    """
    logger.info(
        f"[Task {self.request.id}] Starting | "
        f"provider={provider} strategy={strategy} reset={reset}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "running",
                "step": "loading documents",
                "provider": provider,
                "strategy": strategy
            }
        )

        result = ingest(
            raw_dir=raw_dir,
            provider=provider,
            strategy=strategy,
            reset=reset
        )

        logger.info(f"[Task {self.request.id}] Complete: {result}")

        return {
            "status": "success",
            "provider": provider,
            "strategy": strategy,
            "documents_loaded": result.get("documents_loaded", 0),
            "chunks_created": result.get("chunks_created", 0),
            "chunks_added": result.get("chunks_added", 0),
            "total_chunks_in_store": result.get("total_chunks_in_store", 0)
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[Task {self.request.id}] Soft time limit exceeded")
        self.update_state(
            state=states.FAILURE,
            meta={
                "status": "failed",
                "error": "Task exceeded 10 minute time limit",
                "provider": provider,
                "strategy": strategy
            }
        )
        raise Ignore()

    except Exception as exc:
        logger.error(f"[Task {self.request.id}] Failed: {exc}", exc_info=True)
        raise self.retry(
            exc=exc,
            countdown=2 ** self.request.retries
        )