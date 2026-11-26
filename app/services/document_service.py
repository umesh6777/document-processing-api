from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, NotFoundError, UnsupportedFileTypeError
from app.models import Document, DocumentStatus
from app.storage.file_storage import FileStorage

# extension -> (expected content type, leading "magic" bytes of a real file of that type)
ALLOWED_TYPES: dict[str, tuple[str, bytes]] = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK\x03\x04",  # DOCX is a ZIP archive
    ),
}


def _validate_type(file: UploadFile) -> str:
    """Check extension, then the file's real header bytes (the client's content type can lie)."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise UnsupportedFileTypeError("Only PDF and DOCX files are allowed")
    content_type, magic = ALLOWED_TYPES[extension]
    header = file.file.read(len(magic))
    file.file.seek(0)
    if header != magic:
        raise UnsupportedFileTypeError(f"File content is not a valid {extension} file")
    return content_type


def _validate_size(file: UploadFile) -> int:
    # Starlette spools the upload to a temp file, so we can measure it without loading it in memory.
    size = file.file.seek(0, 2)
    file.file.seek(0)
    if size > get_settings().max_upload_size_bytes:
        raise FileTooLargeError(f"File exceeds {get_settings().max_upload_size_mb} MB limit")
    if size == 0:
        raise UnsupportedFileTypeError("File is empty")
    return size


def create_document(
    db: Session, storage: FileStorage, project_id: int, file: UploadFile
) -> Document:
    size = _validate_size(file)
    content_type = _validate_type(file)
    filename = Path(file.filename or "").name
    stored_path = storage.save(file.file, filename)

    document = Document(
        project_id=project_id,
        filename=filename,
        stored_path=stored_path,
        content_type=content_type,
        size_bytes=size,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        storage.delete(stored_path)  # don't leave orphan files if the DB write fails
        raise
    return document


def list_documents(
    db: Session,
    offset: int,
    limit: int,
    project_id: int | None = None,
    status: DocumentStatus | None = None,
    search: str | None = None,
) -> tuple[list[Document], int]:
    """Single query builder behind every document list endpoint; all filters are optional."""
    query = select(Document)
    if project_id is not None:
        query = query.where(Document.project_id == project_id)
    if status is not None:
        query = query.where(Document.status == status)
    if search:
        # autoescape: "%" and "_" in the search text are matched literally, not as wildcards.
        query = query.where(Document.filename.icontains(search, autoescape=True))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Document.id.desc()).offset(offset).limit(limit)).all()
    return list(items), total


def get_document(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    return document


def delete_document(db: Session, storage: FileStorage, document_id: int) -> None:
    document = get_document(db, document_id)
    db.delete(document)
    db.commit()
    # Delete the file only after the commit, so a failed commit never leaves
    # a DB row pointing at a missing file.
    storage.delete(document.stored_path)
