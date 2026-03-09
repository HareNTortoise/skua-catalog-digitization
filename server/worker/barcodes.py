from __future__ import annotations

import cv2
from pyzbar.pyzbar import decode as zbar_decode


def decode_barcodes_from_frame(frame) -> set[str]:
    if frame is None:
        return set()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Barcodes in real-world video frames are often small, blurred, or low-contrast.
    # Try a few lightweight variants for better reliability.
    variants = [gray]
    try:
        up = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        variants.append(up)
        thr = cv2.adaptiveThreshold(
            up,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )
        variants.append(thr)
    except Exception:
        pass

    results: set[str] = set()
    for img in variants:
        for item in zbar_decode(img):
            try:
                value = item.data.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if value:
                results.add(value)
    return results


def extract_barcodes_from_video(video_path: str, sample_fps: float) -> set[str]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Could not open video file")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    duration_s = (frame_count / fps) if fps > 0 else 0.0

    barcodes: set[str] = set()

    if duration_s <= 0:
        for _ in range(30):
            ok, frame = cap.read()
            if not ok:
                break
            barcodes.update(decode_barcodes_from_frame(frame))
        cap.release()
        return barcodes

    step_s = 1.0 / max(sample_fps, 0.1)
    t = 0.0
    while t <= duration_s:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            t += step_s
            continue
        barcodes.update(decode_barcodes_from_frame(frame))
        t += step_s

    cap.release()
    return barcodes
