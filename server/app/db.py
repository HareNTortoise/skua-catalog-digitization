import os
import shlex
from collections.abc import Generator
from os.path import expandvars
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _load_env_if_present() -> None:
    """Best-effort loading of `server/.env` for local/dev.

    In production, environment variables should be injected by the runtime (ECS/EC2/etc.).
    `load_dotenv` does not override already-set env vars by default.
    """

    if load_dotenv is None:
        return

    # db.py lives at: server/app/db.py -> server/.env is 1 level up from server/app
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


Base = declarative_base()


def _parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_debug() -> bool:
    # Default to non-debug unless explicitly enabled.
    return _parse_bool_env("DEBUG", default=False)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_libpq_dsn(dsn: str) -> URL:
    """Parse libpq-style DSN: 'host=... port=... dbname=... user=... password=...'."""
    tokens = shlex.split(dsn)
    parts: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            parts[key] = value

    username = parts.get("user") or parts.get("username")
    password = parts.get("password")
    host = parts.get("host")
    port = int(parts["port"]) if parts.get("port") else None
    database = parts.get("dbname") or parts.get("database")

    query: dict[str, str] = {}
    for k, v in parts.items():
        if k in {"user", "username", "password", "host", "port", "dbname", "database"}:
            continue
        query[k] = v

    return URL.create(
        drivername="postgresql+psycopg2",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        query=query or None,
    )


def _normalize_database_url(raw: str) -> URL:
    expanded = expandvars(raw)
    value = expanded.strip().strip('"').strip("'")
    if "://" in value:
        return make_url(value)
    return _parse_libpq_dsn(value)


def _ensure_sslrootcert(url: URL) -> URL:
    if url.drivername.startswith("sqlite"):
        return url

    query = dict(url.query or {})
    sslmode = query.get("sslmode")
    sslrootcert = query.get("sslrootcert")
    if sslmode in {"verify-full", "verify-ca"} and sslrootcert:
        if os.path.exists(sslrootcert):
            return url

        # Common mismatch: local dev uses conda (no /certs mount), but docker-compose
        # mounts ./server/certs to /certs. If the user provided /certs/<bundle>,
        # fall back to the repo's server/certs/<bundle> when available.
        local_bundle = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "certs", os.path.basename(sslrootcert))
        )
        if os.path.exists(local_bundle):
            new_query = {**query, "sslrootcert": local_bundle}
            return url.set(query=new_query)

        raise RuntimeError(
            "DATABASE_URL requests SSL verification "
            f"(sslmode={sslmode}) but sslrootcert was not found at: {sslrootcert}. "
            "If running via docker-compose, ensure ./server/certs is mounted to /certs and "
            "contains the CA bundle (e.g. global-bundle.pem). For local dev (conda), "
            "set sslrootcert to the on-disk path under server/certs."
        )

    return url


def _build_engine() -> tuple[Engine, bool]:
    _load_env_if_present()
    if _is_debug():
        sqlite_path = os.getenv("SQLITE_DB_PATH", "./dev.db").strip() or "./dev.db"
        url = make_url(f"sqlite:///{sqlite_path}")
        is_sqlite = True
    else:
        raw = _require_env("DATABASE_URL")
        url = _normalize_database_url(raw)
        is_sqlite = url.drivername.startswith("sqlite")

    connect_args: dict[str, object] = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False
    else:
        url = _ensure_sslrootcert(url)
        # Avoid hanging indefinitely when RDS is unreachable.
        # psycopg2 interprets this as seconds.
        connect_args["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))

    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    return engine, is_sqlite


engine, _IS_SQLITE = _build_engine()


# Keep SessionLocal re-bindable so the app can fall back to SQLite for local dev.
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
SessionLocal.configure(bind=engine)


def _set_engine(new_engine: Engine) -> None:
    global engine
    engine = new_engine
    SessionLocal.configure(bind=engine)


def use_sqlite_for_local_dev(sqlite_path: str = "./dev.db") -> None:
    """Switch the global engine/sessionmaker to SQLite (best-effort local fallback)."""
    sqlite_url = make_url(f"sqlite:///{sqlite_path}")
    new_engine = create_engine(
        sqlite_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
    _set_engine(new_engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
