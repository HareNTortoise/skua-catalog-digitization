from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def open_food_facts_lookup(barcode: str) -> dict[str, str] | None:
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        with urlopen(url, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except URLError:
        return None
    except Exception:
        return None

    if payload.get("status") != 1:
        return None

    product = payload.get("product") or {}
    return {
        "product_name": (product.get("product_name") or "").strip(),
        "manufacturer_brand": (product.get("brands") or "").strip(),
        "image_url": (product.get("image_front_url") or product.get("image_url") or "").strip(),
        "categories": (product.get("categories") or "").strip(),
    }


def build_answer_key(barcodes: set[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (answer_key_list, by_barcode)."""
    answer_key: list[dict[str, Any]] = []
    by_barcode: dict[str, dict[str, Any]] = {}

    for barcode in sorted(barcodes):
        off = open_food_facts_lookup(barcode) or {}
        entry = {
            "barcode": barcode,
            "name": (off.get("product_name") or "").strip() or None,
            "manufacturer_brand": (off.get("manufacturer_brand") or "").strip() or None,
            "categories": (off.get("categories") or "").strip() or None,
            "image_url": (off.get("image_url") or "").strip() or None,
        }
        answer_key.append(entry)
        by_barcode[barcode] = entry

    return answer_key, by_barcode
