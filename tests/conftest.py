import os
import tempfile
from collections.abc import Iterator

import pytest

# Configure an isolated environment BEFORE the app (and its settings) is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["PROCESSING_DELAY_SECONDS"] = "0"
os.environ["MAX_UPLOAD_SIZE_MB"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

PDF_BYTES = b"%PDF-1.4\n%fake pdf body\n"
DOCX_BYTES = b"PK\x03\x04fake docx body"
PDF_TYPE = "application/pdf"


@pytest.fixture
def client() -> Iterator[TestClient]:
    Base.metadata.drop_all(bind=engine)  # fresh schema per test -> no test depends on another
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def project_id(client: TestClient) -> int:
    return client.post("/projects", json={"name": "Test project"}).json()["id"]


@pytest.fixture
def upload(client: TestClient, project_id: int):
    def _upload(name: str = "report.pdf", content: bytes = PDF_BYTES, pid: int = project_id):
        return client.post(f"/projects/{pid}/documents", files={"file": (name, content, PDF_TYPE)})

    return _upload
