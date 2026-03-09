from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session


def persist_items_from_barcodes_only(db: Session, job, *, barcodes: set[str], open_food_facts_lookup) -> int:
    """Deterministic-only persist (when ENABLE_LLM=0)."""

    inserted = 0
    for barcode in sorted(barcodes):
        off = open_food_facts_lookup(barcode)

        product_name = (off or {}).get("product_name") or f"Unknown product ({barcode})"
        manufacturer_brand = (off or {}).get("manufacturer_brand") or None
        image_url = (off or {}).get("image_url") or None
        categories = (off or {}).get("categories") or None

        # Import models lazily here to avoid importing app.* at module import-time.
        from app import models

        item = models.SKUItem(
            id=str(uuid.uuid4()),
            store_id=job.store_id,
            job_id=job.id,
            product_name=product_name,
            barcode=barcode,
            manufacturer_brand=manufacturer_brand,
            image_url=image_url,
            categories=categories,
            requires_review=(off is None or not (off.get("product_name") if off else None)),
        )
        db.add(item)
        inserted += 1

    db.commit()
    return inserted


def persist_llm_items(
    db: Session,
    job,
    *,
    extracted_items: list[dict[str, Any]],
    answer_key_by_barcode: dict[str, dict[str, Any]],
) -> int:
    inserted = 0

    from app import models

    for raw in extracted_items:
        barcode = (raw.get("barcode") or "").strip() or None
        answer = answer_key_by_barcode.get(barcode) if barcode else None

        product_name = (raw.get("product_name") or "").strip()
        if not product_name and answer:
            product_name = (answer.get("name") or "").strip()
        if not product_name:
            product_name = f"Unknown product ({barcode})" if barcode else "Unknown product"

        manufacturer_brand = (raw.get("manufacturer_brand") or "").strip() or None
        if not manufacturer_brand and answer:
            manufacturer_brand = (answer.get("manufacturer_brand") or "").strip() or None

        categories_list = raw.get("categories") or []
        if isinstance(categories_list, str):
            categories_list = [c.strip() for c in categories_list.split(",") if c.strip()]
        categories = ",".join([str(c).strip() for c in categories_list if str(c).strip()]) or None
        if not categories and answer:
            categories = (answer.get("categories") or "").strip() or None

        image_url = (raw.get("image_url") or "").strip() or None
        if not image_url and answer:
            image_url = (answer.get("image_url") or "").strip() or None

        item = models.SKUItem(
            id=str(uuid.uuid4()),
            store_id=job.store_id,
            job_id=job.id,
            product_name=product_name,
            description=(raw.get("description") or None),
            mrp=(raw.get("mrp") or None),
            selling_price=(raw.get("selling_price") or None),
            quantity=(raw.get("quantity") or None),
            categories=categories,
            net_weight=(raw.get("net_weight") or None),
            unit_of_measurement=(raw.get("unit_of_measurement") or None),
            colour=(raw.get("colour") or None),
            size=(raw.get("size") or None),
            packaging_type=(raw.get("packaging_type") or None),
            barcode=barcode,
            sku_id=(raw.get("sku_id") or None),
            manufacturer_brand=manufacturer_brand,
            manufacturing_date=(raw.get("manufacturing_date") or None),
            expiration_date=(raw.get("expiration_date") or None),
            image_url=image_url,
            requires_review=bool(raw.get("requires_review")),
        )
        db.add(item)
        inserted += 1

    db.commit()
    return inserted
