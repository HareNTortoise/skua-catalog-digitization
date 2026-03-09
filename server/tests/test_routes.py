import json
from pathlib import Path

from app import models


def test_generate_upload_url_creates_job_and_returns_url(client, db_session):
    resp = client.post(
        "/api/v1/jobs/generate-upload-url",
        json={"store_id": "store-1", "filename": "walkthrough.mp4"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "job_id" in payload
    assert payload["upload_url"].startswith("https://example.test/presigned/")

    job = db_session.get(models.VideoJob, payload["job_id"])
    assert job is not None
    assert job.store_id == "store-1"
    assert job.status == models.JobStatus.PENDING


def test_start_processing_updates_status_and_sends_sqs(client, db_session):
    job = models.VideoJob(
        id="job-123",
        store_id="store-1",
        s3_object_key="uploads/store-1/job-123_test.mp4",
        status=models.JobStatus.PENDING,
    )
    db_session.add(job)
    db_session.commit()

    resp = client.post("/api/v1/jobs/start-processing/job-123")
    assert resp.status_code == 200

    db_session.refresh(job)
    assert job.status == models.JobStatus.PROCESSING

    # Ensure SQS message was sent.
    sent = client.app.state.stub_sqs.messages
    assert len(sent) == 1
    body = json.loads(sent[0]["body"])
    assert body["job_id"] == "job-123"
    assert body["s3_key"] == job.s3_object_key


def test_get_job_status_counts_items(client, db_session):
    job = models.VideoJob(
        id="job-200",
        store_id="store-1",
        s3_object_key="uploads/store-1/job-200_test.mp4",
        status=models.JobStatus.PROCESSING,
    )
    db_session.add(job)
    db_session.commit()

    db_session.add(
        models.SKUItem(
            id="item-1",
            store_id="store-1",
            job_id="job-200",
            product_name="B item",
        )
    )
    db_session.add(
        models.SKUItem(
            id="item-2",
            store_id="store-1",
            job_id="job-200",
            product_name="A item",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/jobs/job-200")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["job_id"] == "job-200"
    assert payload["status"] == "PROCESSING"
    assert payload["items_processed"] == 2


def test_get_job_status_404(client):
    resp = client.get("/api/v1/jobs/does-not-exist")
    assert resp.status_code == 404


def test_catalog_returns_sorted_items(client, db_session):
    db_session.add(
        models.SKUItem(
            id="i1",
            store_id="store-x",
            job_id="j",
            product_name="Zebra",
        )
    )
    db_session.add(
        models.SKUItem(
            id="i2",
            store_id="store-x",
            job_id="j",
            product_name="Apple",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/catalog/store-x")
    assert resp.status_code == 200
    payload = resp.json()
    names = [i["product_name"] for i in payload["items"]]
    assert names == ["Apple", "Zebra"]


def test_upload_and_queue_job_success(client, db_session):
    video_path = Path(__file__).resolve().parents[1] / "media" / "test.mp4"
    assert video_path.exists(), "Expected sample video at server/media/test.mp4"

    with video_path.open("rb") as f:
        resp = client.post(
            "/api/v1/jobs/upload",
            files={"video": ("test.mp4", f, "video/mp4")},
            data={"store_id": "store-vid"},
        )

    assert resp.status_code == 202
    payload = resp.json()
    assert payload["status"] == "PENDING"
    assert "job_id" in payload

    # DB record created.
    job = db_session.get(models.VideoJob, payload["job_id"])
    assert job is not None
    assert job.store_id == "store-vid"
    assert job.status == models.JobStatus.PENDING

    # Upload + SQS send happened.
    assert len(client.app.state.stub_s3.uploads) == 1
    assert len(client.app.state.stub_sqs.messages) == 1


def test_upload_rejects_non_video_content_type(client):
    resp = client.post(
        "/api/v1/jobs/upload",
        files={"video": ("file.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_missing_env_returns_500(tmp_path, monkeypatch):
    # Build an isolated client without required AWS env var.
    import importlib
    import sys
    from fastapi.testclient import TestClient

    server_dir = Path(__file__).resolve().parents[1]
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))

    # Set to empty so `load_dotenv()` won't override it, but `_require_env` still fails.
    monkeypatch.setenv("AWS_S3_BUCKET", "")
    monkeypatch.setenv("AWS_SQS_QUEUE_URL", "https://sqs.test/queue")

    for name in ("app.db", "app.models", "app.routes", "main"):
        if name in sys.modules:
            del sys.modules[name]

    main = importlib.import_module("main")

    with TestClient(main.app) as c:
        resp = c.post(
            "/api/v1/jobs/generate-upload-url",
            json={"store_id": "s", "filename": "x.mp4"},
        )
        assert resp.status_code == 500
