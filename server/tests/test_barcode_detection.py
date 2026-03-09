import os
from pathlib import Path

import pytest


def test_sample_video_barcode_count():
    """Scans the bundled sample video and prints how many unique barcodes were detected.

    Run with `-s` (or `--capture=tee-sys`) to see the printed count.
    """

    video_path = Path(__file__).resolve().parents[1] / "media" / "test.mp4"
    if not video_path.exists():
        pytest.skip("No sample video found at server/media/test.mp4")

    try:
        from worker import _extract_barcodes_from_video
    except Exception as exc:
        pytest.skip(f"worker/cv2/pyzbar not available: {exc}")

    sample_fps = float(os.getenv("BARCODE_TEST_SAMPLE_FPS", "1"))
    barcodes = _extract_barcodes_from_video(str(video_path), sample_fps=sample_fps)

    # Print for visibility in test output.
    sorted_codes = sorted(barcodes)
    print(f"[barcode-scan] sample_fps={sample_fps} unique_barcodes={len(sorted_codes)}")
    if sorted_codes:
        print("[barcode-scan] barcodes:")
        for code in sorted_codes:
            print(f"  - {code}")

    assert isinstance(barcodes, set)
