import logging

from fastapi import Header, HTTPException
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

_warned_open_mode = False


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Gate mutating/compute-heavy endpoints behind a shared API key.

    If API_KEY is unset, auth is skipped (local/dev convenience) but a
    warning is logged once so an open deployment is never silent. Set
    API_KEY in the environment to enforce it.
    """
    global _warned_open_mode

    if not settings.api_key:
        if not _warned_open_mode:
            logger.warning(
                "API_KEY is not set — /ingest, /upload, /ask and /jobs are "
                "running WITHOUT authentication. Set API_KEY before exposing "
                "this service beyond a trusted network."
            )
            _warned_open_mode = True
        return

    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")
