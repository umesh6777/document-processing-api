# Document Processing API

A modular REST API built with **FastAPI** and **SQLAlchemy 2.0** for managing projects and their
PDF/DOCX documents. It supports search, filtering and pagination, and tracks each document through a
simulated background processing workflow.

```
uploaded ──► processing ──► completed
                       └──► failed
```

## Features

- Projects: create, list (paginated) and get details
- Documents: upload (PDF/DOCX, max 10 MB), list, get details and delete
- Search by filename, filter by project and status, pagination on every list endpoint
- File type validation by extension **and** by the file's actual header bytes
- Background processing with `BackgroundTasks` that updates the document status at each stage
- Errors come back in one consistent `{"detail": ...}` shape with correct status codes
  (201, 204, 404, 413, 415, 422)
- All configuration comes from the environment (`.env`)
- Swagger UI at `/docs` and ReDoc at `/redoc`

## Requirements

- Python **3.11+**

## Setup

```bash
git clone https://github.com/umesh6777/document-processing-api.git
cd document-processing-api

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs

The database tables are created automatically on startup.

## Tests

```bash
pytest -v
```

The tests run against a temporary SQLite database and upload folder, with zero processing delay,
so they never touch your local data.

Lint and format checks (PEP 8):

```bash
ruff check . && ruff format --check .
```

## Configuration

| Variable                   | Default                | Description                                    |
|----------------------------|------------------------|------------------------------------------------|
| `APP_NAME`                 | Document Management API| Title shown in Swagger                         |
| `DATABASE_URL`             | `sqlite:///./app.db`   | Any SQLAlchemy URL (SQLite or PostgreSQL)      |
| `UPLOAD_DIR`               | `uploads`              | Where uploaded files are stored                |
| `MAX_UPLOAD_SIZE_MB`       | `10`                   | Maximum upload size                            |
| `PROCESSING_DELAY_SECONDS` | `2`                    | Simulated processing time                      |
| `PROCESSING_FAILURE_RATE`  | `0.0`                  | Share of uploads (0–1) that fail on purpose, to demo `failed` |

To use PostgreSQL, run `pip install "psycopg[binary]"` and set
`DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/documents`.

## API Endpoints

| Method | Path                                | Description                                    | Success |
|--------|-------------------------------------|------------------------------------------------|---------|
| POST   | `/projects`                         | Create a project                               | 201     |
| GET    | `/projects`                         | List projects (`page`, `size`)                 | 200     |
| GET    | `/projects/{project_id}`            | Project details                                | 200     |
| POST   | `/projects/{project_id}/documents`  | Upload a document (multipart `file`)           | 201     |
| GET    | `/documents`                        | List documents (`project_id`, `status`, `search`, `page`, `size`) | 200 |
| GET    | `/documents/{document_id}`          | Document details                               | 200     |
| DELETE | `/documents/{document_id}`          | Delete a document and its file                 | 204     |
| GET    | `/health`                           | Health check                                   | 200     |

To list the documents of one project, call `GET /documents?project_id={id}`. Every filter can be
combined with the others.

## API Examples

### Create a project

```bash
curl -X POST http://127.0.0.1:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Contracts 2026", "description": "Vendor contracts"}'
```

`201 Created`
```json
{"id": 1, "name": "Contracts 2026", "description": "Vendor contracts", "created_at": "2026-11-25T16:42:05.098783Z"}
```

### List projects

```bash
curl "http://127.0.0.1:8000/projects?page=1&size=20"
```

`200 OK`
```json
{"items": [{"id": 1, "name": "Contracts 2026", "description": "Vendor contracts", "created_at": "2026-11-25T16:42:05.098783Z"}],
 "total": 1, "page": 1, "size": 20, "pages": 1}
```

### Upload a document

```bash
curl -X POST http://127.0.0.1:8000/projects/1/documents -F "file=@contract.pdf"
```

`201 Created`. The status starts as `uploaded`, and the background task then moves it forward.
```json
{"id": 1, "project_id": 1, "filename": "contract.pdf", "content_type": "application/pdf",
 "size_bytes": 48213, "status": "uploaded", "error_message": null,
 "created_at": "2026-11-25T16:42:05.133973Z", "updated_at": "2026-11-25T16:42:05.133980Z"}
```

### Search, filter and paginate

```bash
curl "http://127.0.0.1:8000/documents?project_id=1&status=completed&search=contract&page=1&size=10"
```

`200 OK`
```json
{"items": [{"id": 1, "project_id": 1, "filename": "contract.pdf", "status": "completed", "...": "..."}],
 "total": 1, "page": 1, "size": 10, "pages": 1}
```

### Delete a document

```bash
curl -X DELETE http://127.0.0.1:8000/documents/1
```

`204 No Content`

### Error responses

| Case                          | Status | Body                                                   |
|-------------------------------|--------|--------------------------------------------------------|
| Unknown project/document      | 404    | `{"detail": "Project 42 not found"}`                   |
| File larger than limit        | 413    | `{"detail": "File exceeds 10 MB limit"}`               |
| Not PDF/DOCX, or fake content | 415    | `{"detail": "Only PDF and DOCX files are allowed"}`    |
| Invalid input (e.g. `page=0`) | 422    | FastAPI validation error list                          |

## Database Schema

```mermaid
erDiagram
    PROJECTS ||--o{ DOCUMENTS : contains
    PROJECTS {
        int id PK
        string name
        text description "nullable"
        datetime created_at
    }
    DOCUMENTS {
        int id PK
        int project_id FK "indexed, ON DELETE CASCADE"
        string filename "indexed, original name"
        string stored_path "internal, not exposed by API"
        string content_type
        int size_bytes
        enum status "uploaded | processing | completed | failed, indexed"
        string error_message "nullable, set when failed"
        datetime created_at
        datetime updated_at
    }
```

`project_id`, `status` and `filename` are indexed because they are the columns the list endpoints
filter on.

## Project Structure

```
app/
├── main.py                      # App factory: routers, exception handlers, startup
├── core/
│   ├── config.py                # Env-based settings (pydantic-settings)
│   └── exceptions.py            # Domain errors + single HTTP mapping
├── db/
│   ├── base.py                  # Declarative base
│   └── session.py               # Engine, session factory, get_db dependency
├── models/                      # SQLAlchemy ORM models
├── schemas/                     # Pydantic API contracts (incl. generic Page[T])
├── api/routes/                  # HTTP layer only
├── services/                    # Business logic, queries, processing workflow
├── dependencies/common.py       # DB session, pagination, storage, project lookup
└── storage/file_storage.py      # Storage interface + local implementation
tests/                           # Pytest suite (14 tests)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design decisions, the known limitations and the
AI tools used.
