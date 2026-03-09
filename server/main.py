import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

# Import after loading env (DB engine + AWS clients are initialized at import time).
from app import models  # noqa: E402
from app.db import engine  # noqa: E402
from app.routes import router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DB startup: create_all() begin")
    try:
        models.Base.metadata.create_all(bind=engine)
        models.ensure_video_job_notify_email_column(engine)
    except OperationalError as exc:
        if _sqlite_fallback_enabled():
            logger.warning(
                "DB startup: Postgres unreachable; falling back to SQLite for local dev. "
                "Set DB_FALLBACK_TO_SQLITE=0 to disable."
            )
            from app import db as db_module

            db_module.use_sqlite_for_local_dev(sqlite_path=os.getenv("SQLITE_DB_PATH", "./dev.db"))
            models.Base.metadata.create_all(bind=db_module.engine)
            models.ensure_video_job_notify_email_column(db_module.engine)
        else:
            logger.exception("DB startup: connection/DDL failed")
            raise RuntimeError(
                "Database startup failed (cannot connect or run migrations). "
                "If you are using RDS, confirm your network can reach the endpoint on port 5432 "
                "(security group / public accessibility / VPN or SSM tunnel). "
                "For local dev, you can switch DATABASE_URL to sqlite:///./dev.db or set DB_FALLBACK_TO_SQLITE=1."
            ) from exc
    logger.info("DB startup: create_all() done")

    yield


app = FastAPI(title="SKUA Catalog Digitization API", lifespan=lifespan)

logger = logging.getLogger("skua")


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER") == "1"


def _sqlite_fallback_enabled() -> bool:
    # If DEBUG is explicitly disabled, never fall back: fail fast to match prod behavior.
    debug_raw = os.getenv("DEBUG")
    if debug_raw is not None and debug_raw.strip().lower() in {"0", "false", "no", "off"}:
        return False

    # Default behavior: allow fallback on host-local dev, but not in Docker.
    raw = os.getenv("DB_FALLBACK_TO_SQLITE")
    if raw is None:
        return not _running_in_docker()
    return raw.strip().lower() in {"1", "true", "yes", "on"}


app.include_router(router)
