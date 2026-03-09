import os

import pytest


@pytest.mark.integration
def test_open_food_facts_lookup_real_api():
    """Opt-in integration test against the real OpenFoodFacts API.

    Enable with:
      RUN_OPENFOODFACTS_INTEGRATION_TESTS=1 pytest -q -m integration

    Optionally override barcodes:
      OFF_TEST_BARCODES=code1,code2,...

    Notes:
    - This is a real network call and may fail if OFF is down or the network is blocked.
    - Run with `-s` (or `--capture=tee-sys`) to see printed product info.
    """

    if os.getenv("RUN_OPENFOODFACTS_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_OPENFOODFACTS_INTEGRATION_TESTS=1 to enable")

    try:
        from worker import _open_food_facts_lookup
    except Exception as exc:
        pytest.fail(f"Could not import worker._open_food_facts_lookup: {exc}")

    default_barcodes = [
        # Barcodes detected from server/media/test.mp4 in our barcode scan tests.
        "8901030916236",
        "8904091121441",
        # Commonly present EANs (fallbacks). Not guaranteed, but often available.
        "5449000000996",  # Coca-Cola (example)
        "3017620422003",  # Nutella (example)
    ]

    env_barcodes = os.getenv("OFF_TEST_BARCODES", "").strip()
    if env_barcodes:
        candidates = [b.strip() for b in env_barcodes.split(",") if b.strip()]
    else:
        candidates = default_barcodes

    def _non_empty(value: object) -> str:
        return (str(value) if value is not None else "").strip()

    successes: list[tuple[str, dict]] = []
    last_result = None

    for barcode in candidates:
        result = _open_food_facts_lookup(barcode)
        last_result = result
        if result is None:
            print(f"[openfoodfacts] barcode={barcode} -> not found / api error")
            continue

        assert isinstance(result, dict)
        product_name = _non_empty(result.get("product_name"))
        brand = _non_empty(result.get("manufacturer_brand"))
        categories = _non_empty(result.get("categories"))
        image_url = _non_empty(result.get("image_url"))

        print(f"[openfoodfacts] barcode={barcode}")
        print(f"  product_name: {product_name or '(empty)'}")
        print(f"  brand: {brand or '(empty)'}")
        print(f"  categories: {categories[:200] + ('…' if len(categories) > 200 else '') if categories else '(empty)'}")
        print(f"  image_url: {image_url or '(empty)'}")

        # Require at least some non-empty signal coming back.
        if any([product_name, brand, categories, image_url]):
            successes.append((barcode, result))

    assert successes, (
        "OpenFoodFacts lookup did not return a product for any candidate barcode. "
        "This could mean the API/network is unavailable, or the chosen barcodes are missing."
        f" Last result: {last_result}"
    )
