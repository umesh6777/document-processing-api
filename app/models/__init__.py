# Importing here registers every model on Base.metadata (needed for create_all).
from app.models.document import Document, DocumentStatus
from app.models.project import Project

__all__ = ["Document", "DocumentStatus", "Project"]
