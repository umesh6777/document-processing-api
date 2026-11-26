from fastapi import APIRouter, BackgroundTasks, UploadFile, status

from app.dependencies.common import DbSession, PaginationDep, ProjectDep, StorageDep
from app.models import Document, Project
from app.schemas.common import Page
from app.schemas.document import DocumentRead
from app.schemas.project import ProjectCreate, ProjectRead
from app.services import document_service, project_service
from app.services.processing_service import process_document

router = APIRouter(prefix="/projects", tags=["Projects"])

NOT_FOUND = {404: {"description": "Project not found"}}


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: DbSession) -> Project:
    return project_service.create_project(db, data)


@router.get("", response_model=Page[ProjectRead])
def list_projects(db: DbSession, pagination: PaginationDep) -> Page[ProjectRead]:
    items, total = project_service.list_projects(db, pagination.offset, pagination.size)
    return Page.build(items, total, pagination.page, pagination.size)


@router.get("/{project_id}", response_model=ProjectRead, responses=NOT_FOUND)
def get_project(project: ProjectDep) -> Project:
    return project


@router.post(
    "/{project_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND,
        413: {"description": "File too large"},
        415: {"description": "Only PDF and DOCX are accepted"},
    },
)
def upload_document(
    project: ProjectDep,
    file: UploadFile,
    db: DbSession,
    storage: StorageDep,
    background_tasks: BackgroundTasks,
) -> Document:
    document = document_service.create_document(db, storage, project.id, file)
    background_tasks.add_task(process_document, document.id)
    return document
