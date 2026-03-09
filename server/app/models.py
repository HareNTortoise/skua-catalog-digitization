import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, text

from .db import Base


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    store_id = Column(String, index=True)
    s3_object_key = Column(String)
    notify_email = Column(String, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


def ensure_video_job_notify_email_column(engine) -> None:
    """Best-effort schema patch for existing DBs.

    This project currently uses `metadata.create_all()`, which does not add columns to
    existing tables. Adding this helper avoids breaking dev/prod DBs that already have
    a `video_jobs` table without `notify_email`.
    """

    try:
        dialect = getattr(getattr(engine, "dialect", None), "name", None)
        dialect = dialect or getattr(getattr(getattr(engine, "engine", None), "dialect", None), "name", None)

        if dialect == "sqlite":
            with engine.begin() as conn:
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(video_jobs)")).fetchall()]
                if "notify_email" not in cols:
                    conn.execute(text("ALTER TABLE video_jobs ADD COLUMN notify_email VARCHAR"))
            return

        # Postgres (and most other SQL dialects we might use)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS notify_email VARCHAR"))
    except Exception:
        # Best-effort only; never block startup if this fails.
        return


class SKUItem(Base):
    __tablename__ = "sku_items"

    id = Column(String, primary_key=True, index=True)  # UUID
    store_id = Column(String, index=True)
    job_id = Column(String, ForeignKey("video_jobs.id"))

    # Standard Attributes
    product_name = Column(String, nullable=False)
    description = Column(String)
    mrp = Column(Float)
    selling_price = Column(Float)
    quantity = Column(Float)
    categories = Column(String)  # Stored as comma-separated or JSON
    net_weight = Column(Float)
    unit_of_measurement = Column(String)
    colour = Column(String)
    size = Column(String)
    packaging_type = Column(String)
    barcode = Column(String, index=True)
    sku_id = Column(String, index=True)
    manufacturer_brand = Column(String)
    manufacturing_date = Column(String)
    expiration_date = Column(String)
    image_url = Column(String)

    # Audit
    requires_review = Column(Boolean, default=False)
