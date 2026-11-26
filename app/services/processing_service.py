import logging
import random
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentStatus

logger = logging.getLogger(__name__)


def _set_status(document_id: int, status: DocumentStatus, error: str | None = None) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:  # deleted while processing
            return
        document.status = status
        document.error_message = error
        db.commit()


def process_document(document_id: int) -> None:
    """Simulated pipeline: uploaded -> processing -> completed | failed.

    Runs after the response is sent, so it opens its own DB session
    (the request's session is already closed by then).
    """
    _set_status(document_id, DocumentStatus.PROCESSING)
    try:
        settings = get_settings()
        time.sleep(settings.processing_delay_seconds)  # stand-in for real work (OCR, AI, ...)
        if random.random() < settings.processing_failure_rate:
            raise RuntimeError("Simulated processing failure")
        _set_status(document_id, DocumentStatus.COMPLETED)
    except Exception as exc:
        logger.exception("Processing failed for document %s", document_id)
        _set_status(document_id, DocumentStatus.FAILED, str(exc)[:500])
