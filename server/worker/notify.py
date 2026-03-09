import os
from typing import Any

from brevo.client import Brevo
from brevo.transactional_emails import SendTransacEmailRequestToItem

from .env import load_env


def send_quality_gate_email(
    *,
    to_email: str | None,
    processing_time_seconds: float,
    items_processed: int,
) -> None:
    """Best-effort email via Brevo transactional template.

    The API stores a per-job `notify_email` on `VideoJob` (passed in here as `to_email`).
    If it's missing, this becomes a no-op.

    Template: Brevo template id 4
    Params: processingTime, itemsProcessed
    """

    # Make this function robust even if called from a different entrypoint.
    load_env()

    resolved_to = (to_email or "").strip()
    if not resolved_to:
        return

    api_key = (os.getenv("BREVO_API_KEY") or "").strip()
    if not api_key:
        return

    params: dict[str, Any] = {
        "processingTime": round(float(processing_time_seconds), 2),
        "itemsProcessed": int(items_processed),
    }

    client = Brevo(api_key=api_key)
    client.transactional_emails.send_transac_email(
        template_id=4,
        to=[SendTransacEmailRequestToItem(email=resolved_to)],
        params=params,
    )
