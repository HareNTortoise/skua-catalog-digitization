from __future__ import annotations

from dataclasses import dataclass

import cv2


@dataclass(frozen=True)
class VideoQualityReport:
    sampled_frames: int
    max_mean_brightness: float
    max_laplacian_variance: float
    passed: bool
    reason: str


def quality_gate_video(
    video_path: str,
    *,
    sample_fps: float = 1.0,
    min_mean_brightness: float = 18.0,
    min_laplacian_variance: float = 45.0,
    max_frames: int = 60,
) -> VideoQualityReport:
    """Fast gate to stop processing pitch-black or completely blurry videos.

    - Brightness: max(mean(gray)) over sampled frames
    - Blur: max(var(Laplacian(gray))) over sampled frames
    """

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return VideoQualityReport(
            sampled_frames=0,
            max_mean_brightness=0.0,
            max_laplacian_variance=0.0,
            passed=False,
            reason="Could not open video",
        )

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    duration_s = (frame_count / fps) if fps > 0 else 0.0

    step_s = 1.0 / max(sample_fps, 0.1)
    t = 0.0
    frames = 0
    max_mean = 0.0
    max_var = 0.0

    while frames < max_frames and (duration_s <= 0.0 or t <= duration_s):
        if duration_s > 0.0:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            t += step_s
            if duration_s <= 0.0:
                break
            continue

        frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(gray.mean())
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        max_mean = max(max_mean, mean_brightness)
        max_var = max(max_var, lap_var)
        t += step_s

    cap.release()

    if frames == 0:
        return VideoQualityReport(
            sampled_frames=0,
            max_mean_brightness=0.0,
            max_laplacian_variance=0.0,
            passed=False,
            reason="No readable frames",
        )

    if max_mean < min_mean_brightness:
        return VideoQualityReport(
            sampled_frames=frames,
            max_mean_brightness=max_mean,
            max_laplacian_variance=max_var,
            passed=False,
            reason="Video too dark",
        )

    if max_var < min_laplacian_variance:
        return VideoQualityReport(
            sampled_frames=frames,
            max_mean_brightness=max_mean,
            max_laplacian_variance=max_var,
            passed=False,
            reason="Video too blurry",
        )

    return VideoQualityReport(
        sampled_frames=frames,
        max_mean_brightness=max_mean,
        max_laplacian_variance=max_var,
        passed=True,
        reason="OK",
    )
