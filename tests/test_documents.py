from app.services import processing_service
from tests.conftest import DOCX_BYTES


def test_upload_pdf_and_docx_returns_201(upload):
    pdf = upload("report.pdf")
    docx = upload("notes.docx", DOCX_BYTES)

    assert pdf.status_code == 201
    assert pdf.json()["status"] == "uploaded"
    assert docx.status_code == 201
    assert docx.json()["content_type"].endswith("wordprocessingml.document")


def test_processing_moves_document_to_completed(client, upload):
    document_id = upload().json()["id"]

    # TestClient runs background tasks right after the response is sent.
    assert client.get(f"/documents/{document_id}").json()["status"] == "completed"


def test_processing_failure_marks_document_failed(client, upload, monkeypatch):
    def broken_sleep(_):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(processing_service.time, "sleep", broken_sleep)
    document_id = upload().json()["id"]

    body = client.get(f"/documents/{document_id}").json()
    assert body["status"] == "failed"
    assert body["error_message"] == "disk on fire"


def test_rejects_unsupported_extension_with_415(upload):
    assert upload("image.png", b"\x89PNG").status_code == 415


def test_rejects_fake_pdf_content_with_415(upload):
    response = upload("evil.pdf", b"MZ this is actually an exe")
    assert response.status_code == 415


def test_rejects_file_over_limit_with_413(upload):
    too_big = b"%PDF" + b"0" * (1024 * 1024)  # limit is 1 MB in tests
    assert upload("big.pdf", too_big).status_code == 413


def test_upload_to_missing_project_returns_404(upload):
    assert upload(pid=9999).status_code == 404


def test_search_filter_and_pagination(client, upload, project_id):
    upload("invoice-jan.pdf")
    upload("invoice-feb.pdf")
    upload("contract.pdf")
    other_project = client.post("/projects", json={"name": "Other"}).json()["id"]
    upload("invoice-other.pdf", pid=other_project)

    body = client.get(
        "/documents",
        params={"project_id": project_id, "search": "INVOICE", "status": "completed", "size": 1},
    ).json()

    assert body["total"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    assert client.get("/documents", params={"status": "failed"}).json()["total"] == 0


def test_search_treats_wildcards_literally(client, upload):
    upload("plan_v1.pdf")
    upload("planv1.pdf")

    body = client.get("/documents", params={"search": "_v1"}).json()

    assert [item["filename"] for item in body["items"]] == ["plan_v1.pdf"]


def test_delete_document_returns_204_then_404(client, upload):
    document_id = upload().json()["id"]

    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert client.delete(f"/documents/{document_id}").status_code == 404
