import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Load `server/.env` if present.

    Must happen before importing `app.*` modules because `app.db` initializes the
    SQLAlchemy engine at import-time.
    """

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)


def parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
