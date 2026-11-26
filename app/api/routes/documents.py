from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies.common import DbSession, PaginationDep, StorageDep
from app.models import Document, DocumentStatus
from app.schemas.common import Page
from app.schemas.document import DocumentRead
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])

NOT_FOUND = {404: {"description": "Document not found"}}


@router.get("", response_model=Page[DocumentRead])
def list_documents(
    db: DbSession,
    pagination: PaginationDep,
    project_id: int | None = None,
    status: DocumentStatus | None = None,
    search: Annotated[str | None, Query(max_length=255, description="Filename contains")] = None,
) -> Page[DocumentRead]:
    items, total = document_service.list_documents(
        db, pagination.offset, pagination.size, project_id, status, search
    )
    return Page.build(items, total, pagination.page, pagination.size)


@router.get("/{document_id}", response_model=DocumentRead, responses=NOT_FOUND)
def get_document(document_id: int, db: DbSession) -> Document:
    return document_service.get_document(db, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_document(document_id: int, db: DbSession, storage: StorageDep) -> None:
    document_service.delete_document(db, storage, document_id)
