from __future__ import annotations

import re
from typing import Any


def _normalize_key(value: str) -> str:
    v = (value or "").strip().lower()
    v = re.sub(r"\s+", " ", v)
    v = re.sub(r"[^a-z0-9 ]+", "", v)
    return v.strip()


def dedupe_extracted_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate products scanned/mentioned multiple times in the same video."""

    merged: dict[str, dict[str, Any]] = {}

    def key_for(item: dict[str, Any]) -> str:
        barcode = (item.get("barcode") or "").strip()
        if barcode:
            return f"barcode:{barcode}"
        return f"name:{_normalize_key(str(item.get('product_name') or ''))}"

    def prefer(a: Any, b: Any) -> Any:
        if b is None:
            return a
        if isinstance(b, str) and not b.strip():
            return a
        return b

    for item in items:
        k = key_for(item)
        if k not in merged:
            merged[k] = dict(item)
            continue

        cur = merged[k]
        for field in [
            "product_name",
            "barcode",
            "manufacturer_brand",
            "selling_price",
            "quantity",
            "packaging_type",
            "net_weight",
            "unit_of_measurement",
            "colour",
            "size",
            "description",
            "manufacturing_date",
            "expiration_date",
            "timestamp_mentioned",
        ]:
            cur[field] = prefer(cur.get(field), item.get(field))

        cats_a = cur.get("categories") or []
        cats_b = item.get("categories") or []
        if isinstance(cats_a, str):
            cats_a = [c.strip() for c in cats_a.split(",") if c.strip()]
        if isinstance(cats_b, str):
            cats_b = [c.strip() for c in cats_b.split(",") if c.strip()]
        cur["categories"] = sorted({c for c in list(cats_a) + list(cats_b) if str(c).strip()})

        cur["requires_review"] = bool(cur.get("requires_review")) or bool(item.get("requires_review"))

    out = [v for v in merged.values() if str(v.get("product_name") or "").strip()]
    return out
