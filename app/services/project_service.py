from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    return project


def list_projects(db: Session, offset: int, limit: int) -> tuple[list[Project], int]:
    total = db.scalar(select(func.count()).select_from(Project)) or 0
    items = db.scalars(select(Project).order_by(Project.id).offset(offset).limit(limit)).all()
    return list(items), total


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project
