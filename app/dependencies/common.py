from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project
from app.services import project_service
from app.storage.file_storage import FileStorage, get_storage


@dataclass(frozen=True)
class Pagination:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(page=page, size=size)


DbSession = Annotated[Session, Depends(get_db)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]
StorageDep = Annotated[FileStorage, Depends(get_storage)]


def get_project_or_404(project_id: int, db: DbSession) -> Project:
    return project_service.get_project(db, project_id)


ProjectDep = Annotated[Project, Depends(get_project_or_404)]
