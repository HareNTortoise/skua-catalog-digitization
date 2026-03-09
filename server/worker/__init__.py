"""Worker package.

This package contains the background worker pipeline:
- quality gate (brightness/blur)
- barcode extraction
- OpenFoodFacts answer key
- optional multimodal LLM step (Bedrock via langchain-aws)
- dedupe + persistence

The leading-underscore helpers are intentionally re-exported for tests.
"""

from .barcodes import extract_barcodes_from_video as _extract_barcodes_from_video
from .open_food_facts import open_food_facts_lookup as _open_food_facts_lookup

__all__ = [
    "_extract_barcodes_from_video",
    "_open_food_facts_lookup",
]
