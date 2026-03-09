import json
import os
import uuid
from typing import Annotated

import boto3
from anyio import to_thread
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, serializers
from .db import get_db

router = APIRouter(prefix="/api/v1")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing required environment variable: {name}")
    return value


def _default_store_id() -> str:
    return os.getenv("DEFAULT_STORE_ID", "hackathon-store")


def _make_boto3_client(service: str):
    region = os.getenv("AWS_REGION")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    if region and endpoint_url:
        return boto3.client(service, region_name=region, endpoint_url=endpoint_url)
    if region:
        return boto3.client(service, region_name=region)
    if endpoint_url:
        return boto3.client(service, endpoint_url=endpoint_url)
    return boto3.client(service)


s3_client = _make_boto3_client("s3")
sqs_client = _make_boto3_client("sqs")


@router.post(
    "/jobs/upload",
    status_code=202,
    response_model=serializers.UploadAndQueueResponse,
    responses={
        415: {"description": "Unsupported media type"},
        500: {"description": "Missing required configuration"},
    },
)
async def upload_and_queue_job(
    video: Annotated[UploadFile, File(description="Raw walkthrough video")],
    db: Annotated[Session, Depends(get_db)],
    store_id: Annotated[str | None, Form()] = None,
    notify_email: Annotated[str | None, Form()] = None,
):
    """
    Phase 1 (single-call): client uploads the raw video to FastAPI.
    FastAPI streams it to S3, pushes an SQS message, and returns 202 with a job_id.
    """
    bucket_name = _require_env("AWS_S3_BUCKET")
    queue_url = _require_env("AWS_SQS_QUEUE_URL")

    content_type = (video.content_type or "").lower()
    if content_type and not content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Unsupported media type; expected a video")

    resolved_store_id = (store_id or "").strip() or _default_store_id()
    resolved_notify_email = (notify_email or "").strip() or None

    job_id = str(uuid.uuid4())
    safe_name = os.path.basename(video.filename or "walkthrough.mp4")
    s3_key = f"uploads/{resolved_store_id}/{job_id}_{safe_name}"

    job = models.VideoJob(
        id=job_id,
        store_id=resolved_store_id,
        s3_object_key=s3_key,
        notify_email=resolved_notify_email,
        status=models.JobStatus.PENDING,
    )
    db.add(job)
    db.commit()

    try:
        await to_thread.run_sync(
            s3_client.upload_fileobj,
            video.file,
            bucket_name,
            s3_key,
            {"ContentType": video.content_type or "video/mp4"},
        )

        message = {
            "job_id": job_id,
            "store_id": resolved_store_id,
            "s3_bucket": bucket_name,
            "s3_key": s3_key,
            "s3_uri": f"s3://{bucket_name}/{s3_key}",
        }
        await to_thread.run_sync(
            lambda: sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
            )
        )

        return {
            "job_id": job_id,
            "status": models.JobStatus.PENDING.value,
            "message": "Upload received. Processing in background; you will be notified when complete.",
        }
    except Exception:
        job.status = models.JobStatus.FAILED
        db.add(job)
        db.commit()
        raise


@router.post(
    "/jobs/generate-upload-url",
    response_model=serializers.PresignedUrlResponse,
    responses={500: {"description": "Missing required configuration"}},
)
async def generate_upload_url(
    request: serializers.PresignedUrlRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Step 1: Client requests permission to upload a video.
    Returns a secure S3 URL so the client uploads directly to AWS, bypassing FastAPI.
    """
    bucket_name = _require_env("AWS_S3_BUCKET")

    store_id = (request.store_id or "").strip() or _default_store_id()
    resolved_notify_email = (request.notify_email or "").strip() or None

    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{store_id}/{job_id}_{request.filename}"

    # Generate Presigned URL
    presigned_url = s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket_name, 'Key': s3_key, 'ContentType': 'video/mp4'},
        ExpiresIn=3600
    )

    job = models.VideoJob(
        id=job_id,
        store_id=store_id,
        s3_object_key=s3_key,
        notify_email=resolved_notify_email,
        status=models.JobStatus.PENDING,
    )
    db.add(job)
    db.commit()

    return {"job_id": job_id, "upload_url": presigned_url}


@router.post(
    "/jobs/start-processing/{job_id}",
    responses={
        404: {"description": "Job not found"},
        500: {"description": "Missing required configuration"},
    },
)
async def start_processing(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Step 2: Client calls this after the S3 upload finishes.
    This pushes the task to Amazon SQS for the background worker.
    """
    queue_url = _require_env("AWS_SQS_QUEUE_URL")
    bucket_name = _require_env("AWS_S3_BUCKET")

    job: models.VideoJob | None = db.get(models.VideoJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    s3_key = job.s3_object_key

    # Push to SQS
    message = {
        "job_id": job_id,
        "s3_bucket": bucket_name,
        "s3_key": s3_key
    }
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )

    # Update DB status to PROCESSING
    job.status = models.JobStatus.PROCESSING
    db.add(job)
    db.commit()
    return {"message": "Video queued for processing successfully"}


@router.get(
    "/jobs/{job_id}",
    response_model=serializers.JobStatusResponse,
    responses={404: {"description": "Job not found"}},
)
async def get_job_status(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Step 3: Client polls this to see if the AI is done.
    """
    job: models.VideoJob | None = db.get(models.VideoJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    items_processed = (
        db.query(func.count(models.SKUItem.id))
        .filter(models.SKUItem.job_id == job_id)
        .scalar()
        or 0
    )

    status_value = job.status.value if isinstance(job.status, models.JobStatus) else str(job.status)
    return {"job_id": job_id, "status": status_value, "items_processed": int(items_processed)}


@router.get("/catalog/{store_id}", response_model=serializers.CatalogResponse)
async def get_store_catalog(
    store_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Step 4: Returns the fully structured ONDC catalog for the UI.
    """
    # Fetch all SKUItems for store_id from DB
    items = (
        db.query(models.SKUItem)
        .filter(models.SKUItem.store_id == store_id)
        .order_by(models.SKUItem.product_name.asc())
        .all()
    )

    return {"items": [serializers.SKUItemResponse.model_validate(i, from_attributes=True) for i in items]}
