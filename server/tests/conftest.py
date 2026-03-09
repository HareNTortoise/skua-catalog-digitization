import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))


class _StubS3:
    def __init__(self):
        self.uploads = []
        self.presigned = []

    def upload_fileobj(self, fileobj, bucket, key, extra_args=None):
        # Consume the file so callers can pass real file handles.
        fileobj.read(1024)
        self.uploads.append({"bucket": bucket, "key": key, "extra_args": extra_args or {}})

    def generate_presigned_url(self, client_method, Params, ExpiresIn):
        self.presigned.append({"client_method": client_method, "params": Params, "expires_in": ExpiresIn})
        return f"https://example.test/presigned/{Params['Bucket']}/{Params['Key']}"


class _StubSQS:
    def __init__(self):
        self.messages = []

    def send_message(self, QueueUrl, MessageBody):
        self.messages.append({"queue_url": QueueUrl, "body": MessageBody})
        return {"MessageId": "test-message-id"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Creates an isolated app + sqlite db + stubbed AWS clients per test."""

    # Force local DB behavior.
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))

    # Provide required AWS env vars for endpoints.
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
    monkeypatch.setenv("AWS_SQS_QUEUE_URL", "https://sqs.test/queue")

    # Import fresh modules so they pick up env vars.
    for name in ("app.db", "app.models", "app.routes", "main"):
        if name in sys.modules:
            del sys.modules[name]

    main = importlib.import_module("main")
    routes = importlib.import_module("app.routes")

    # Stub AWS clients and thread helper.
    stub_s3 = _StubS3()
    stub_sqs = _StubSQS()
    monkeypatch.setattr(routes, "s3_client", stub_s3, raising=True)
    monkeypatch.setattr(routes, "sqs_client", stub_sqs, raising=True)

    async def _run_sync(func, *args, limiter=None, **kwargs):
        # FastAPI/AnyIO may pass a `limiter=` kwarg to run_sync; ignore it.
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.to_thread, "run_sync", _run_sync, raising=True)

    with TestClient(main.app) as test_client:
        # Store on the ASGI app state (TestClient doesn't expose `.state`).
        test_client.app.state.stub_s3 = stub_s3
        test_client.app.state.stub_sqs = stub_sqs
        yield test_client


@pytest.fixture()
def db_session(client):
    # Import after `client` fixture so app/db has correct engine binding.
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
