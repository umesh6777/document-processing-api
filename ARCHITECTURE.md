# Architecture Note

## Layers

```
HTTP request
   │
   ▼
api/routes        HTTP only: parse input, call a service, return a schema
   │  uses
   ▼
dependencies      reusable injectables: DB session, pagination, storage, "project or 404"
   │
   ▼
services          business rules and queries; raise domain errors (no HTTP knowledge)
   │         │
   ▼         ▼
models     storage   ORM tables / file persistence behind an interface
   │
   ▼
db                engine + session factory, built from core/config settings
```

Each layer depends only on the layers below it. Routes never write SQL, and services never build
HTTP responses.

## Key decisions

- **Domain exceptions, one handler.** Services raise `NotFoundError`, `FileTooLargeError` and
  `UnsupportedFileTypeError`, and each error class carries its own status code. A single handler in
  `core/exceptions.py` turns all of them into `{"detail": ...}`, the same shape FastAPI uses for its
  own errors. Adding a new error type takes a 2-line class.
- **Models are separate from schemas.** The ORM `Document` includes `stored_path`, but the API
  schema `DocumentRead` leaves it out, so internal file paths never leak to clients.
- **Generic `Page[T]`.** Every list endpoint returns the same pagination envelope, and the
  pagination query parameters come from one shared dependency.
- **One query builder for documents.** `document_service.list_documents` takes optional
  `project_id`, `status` and `search` filters. Listing by project, filtering by status, and any new
  combination (for example "failed documents across all projects") reuse it without new query code.
- **Storage behind a `Protocol`.** `FileStorage` defines `save` and `delete`.
  `LocalFileStorage` is injected through `get_storage()`, so moving to S3 means one new class and
  one changed line. Stored files get UUID names, so a client-supplied filename such as
  `../../etc/passwd` can never become a file path.
- **Background tasks open their own DB session.** The request's session is closed once the
  response is sent, so `processing_service` opens a fresh session for each status update.

## File validation and its limits

1. **Size:** Starlette spools the upload to a temporary file, and the service seeks to the end to
   measure it without loading it into memory. Over the limit returns 413. An empty file returns 415.
2. **Type:** the extension must be `.pdf` or `.docx`. The first bytes must then match the format's
   signature (`%PDF`, or `PK\x03\x04` for the ZIP container used by DOCX). The client-sent
   `Content-Type` is ignored, because anyone can set it.

Limitations:
- The request body has already been received by the time the size is checked. In production you
  would also cap the body size at the proxy (nginx `client_max_body_size`) or reject early on
  `Content-Length`.
- The signature check confirms the container format, not that the whole file is valid. Any ZIP
  renamed to `.docx` passes. Full validation would parse the file (`pypdf`, `python-docx`) and
  ideally run a malware scan, during processing rather than during the request.

## Reliability of background processing

`BackgroundTasks` runs in the same process after the response is sent. If the server crashes or
restarts mid-task, the work is lost and the document stays in `uploaded` or `processing`
permanently. Nothing retries it.

Production approach:
- Use a **durable job queue** such as Celery, RQ or Dramatiq with Redis or RabbitMQ, or a managed
  queue like SQS. The API commits the row and then enqueues the job. Workers run as separate
  processes, can be scaled on their own, and acknowledge a job only after it finishes, so a crash
  causes a redelivery instead of a lost job.
- To avoid "row saved but job never queued", use the **transactional outbox** pattern: write the
  job to an outbox table in the same DB transaction, and a relay publishes it to the queue.
- Make processing **idempotent** and add **retries with backoff**. Track `attempts` and
  `last_error`, and mark `failed` after N attempts.
- Run a **recovery sweeper** that re-queues documents stuck in `processing` longer than a timeout.

## Production notes (out of scope here)

- Use **Alembic migrations** instead of `create_all` on startup.
- SQLite does not store timezones, so timestamps read back from it lose their `Z`. PostgreSQL
  (`timestamptz`) keeps them.
- Add authentication and authorization, and rate limiting on uploads.

## AI tools used

This project was built with the help of **Claude (Anthropic)** as a coding assistant, which the
assignment allows. I reviewed every part of the design and implementation and can explain and
change any of it.
