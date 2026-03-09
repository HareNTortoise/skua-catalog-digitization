from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone

from .aws import make_boto3_client
from .barcodes import extract_barcodes_from_video
from .dedupe import dedupe_extracted_items
from .env import load_env, parse_bool_env, require_env
from .llm import invoke_llm_with_full_video
from .notify import send_quality_gate_email
from .open_food_facts import build_answer_key
from .persist import persist_items_from_barcodes_only, persist_llm_items
from .quality import quality_gate_video

# Critical: load env before importing app.* (DB engine init at import time).
load_env()

from app import models  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402


# Best-effort schema patch so existing DBs don't break after adding new columns.
models.ensure_video_job_notify_email_column(engine)


def process_one_message() -> bool:
    queue_url = require_env("AWS_SQS_QUEUE_URL")

    sqs = make_boto3_client("sqs")
    s3 = make_boto3_client("s3")

    resp = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20,
        VisibilityTimeout=int(os.getenv("SQS_VISIBILITY_TIMEOUT_SECONDS", "600")),
    )
    messages = resp.get("Messages") or []
    if not messages:
        return False

    msg = messages[0]
    receipt = msg.get("ReceiptHandle")
    body = msg.get("Body")
    if not receipt or not body:
        if receipt:
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        return True

    try:
        payload = json.loads(body)
    except Exception:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        return True

    job_id = payload.get("job_id")
    bucket = payload.get("s3_bucket")
    key = payload.get("s3_key")
    if not job_id or not bucket or not key:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        return True

    db = SessionLocal()
    try:
        job: models.VideoJob | None = db.get(models.VideoJob, job_id)
        if job is None:
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            return True

        started_at = time.monotonic()

        job.status = models.JobStatus.PROCESSING
        db.add(job)
        db.commit()

        barcode_sample_fps = float(os.getenv("FRAME_SAMPLE_FPS", "1"))
        quality_sample_fps = float(os.getenv("QUALITY_GATE_SAMPLE_FPS", "1"))
        min_brightness = float(os.getenv("QUALITY_MIN_MEAN_BRIGHTNESS", "18"))
        min_blur = float(os.getenv("QUALITY_MIN_LAPLACIAN_VARIANCE", "45"))

        with tempfile.TemporaryDirectory(prefix="shelfie_worker_") as tmpdir:
            local_path = os.path.join(tmpdir, f"{job_id}.mp4")
            s3.download_file(bucket, key, local_path)

            report = quality_gate_video(
                local_path,
                sample_fps=quality_sample_fps,
                min_mean_brightness=min_brightness,
                min_laplacian_variance=min_blur,
            )
            if not report.passed:
                try:
                    send_quality_gate_email(
                        to_email=getattr(job, "notify_email", None),
                        processing_time_seconds=time.monotonic() - started_at,
                        items_processed=0,
                    )
                except Exception:
                    pass

                job.status = models.JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                db.add(job)
                db.commit()

                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                return True

            barcodes = extract_barcodes_from_video(local_path, sample_fps=barcode_sample_fps)
            answer_key, answer_key_by_barcode = build_answer_key(barcodes)
            answer_key_json = json.dumps(answer_key, ensure_ascii=False)

            inserted = 0

            if parse_bool_env("ENABLE_LLM", default=False):
                result = invoke_llm_with_full_video(video_path=local_path, answer_key_json=answer_key_json)
                extracted_items = [i.model_dump() for i in (result.items or [])]
                deduped_items = dedupe_extracted_items(extracted_items)
                inserted = persist_llm_items(
                    db,
                    job,
                    extracted_items=deduped_items,
                    answer_key_by_barcode=answer_key_by_barcode,
                )
            else:
                from .open_food_facts import open_food_facts_lookup

                inserted = persist_items_from_barcodes_only(
                    db,
                    job,
                    barcodes=barcodes,
                    open_food_facts_lookup=open_food_facts_lookup,
                )

            try:
                send_quality_gate_email(
                    to_email=getattr(job, "notify_email", None),
                    processing_time_seconds=time.monotonic() - started_at,
                    items_processed=int(inserted),
                )
            except Exception:
                pass

        job.status = models.JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()

        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        return True
    except Exception:
        try:
            job = db.get(models.VideoJob, job_id) if job_id else None
            if job is not None:
                job.status = models.JobStatus.FAILED
                db.add(job)
                db.commit()
        except Exception:
            pass
        return True
    finally:
        db.close()


def main() -> None:
    print("Shelfie worker started. Waiting for SQS messages...")
    while True:
        handled = process_one_message()
        if not handled:
            time.sleep(float(os.getenv("WORKER_IDLE_SLEEP_SECONDS", "1")))
