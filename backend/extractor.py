import subprocess
import tempfile
import os
import base64
import uuid
import cv2
import numpy as np
from pathlib import Path


# ── Layout constants (relative to frame height/width) ──────────────────────
TAB_ROW_START = 0.68   # tab panel starts at 68% down the full frame

# ── Diff region (relative to tab crop) ─────────────────────────────────────
# Staff notation area used for change detection. Avoids the chord diagram
# on the far right and the very top banner, but covers the full staff width
# so note content in any section triggers a diff on a real panel refresh.
MEASURE_ROW_START = 0.25
MEASURE_ROW_END   = 0.97
MEASURE_COL_START = 0.20
MEASURE_COL_END   = 0.85

# ── Detection thresholds ────────────────────────────────────────────────────
# Higher than a full-frame diff because the region is mostly white;
# a number swap is a large relative change.
DIFF_THRESHOLD        = 0.028
MIN_PANEL_GAP_SECONDS = 2.5
INTRO_SKIP_SECONDS    = 3.0
MIN_TAB_BRIGHTNESS    = 40     # mean gray (0–255) for tab to count as visible / non-faded
VIDEO_END_FRACTION    = 0.95   # stop scanning here to avoid fade-out panels


def download_video(url: str, output_path: str) -> str:
    """Download YouTube video to output_path using yt-dlp."""
    print(f"[extractor] Downloading: {url}")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]/bestvideo[height<=720]/best[height<=720]",
        "--no-playlist",
        "-o", output_path,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")
    return output_path


def extract_frames(video_path: str, fps: float = 4.0) -> list:
    """Extract frames from video at given fps using OpenCV."""
    print(f"[extractor] Extracting frames at {fps}fps from {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(video_fps / fps))

    frames = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            frames.append(frame)
        frame_idx += 1

    cap.release()
    print(f"[extractor] Extracted {len(frames)} frames")
    return frames


def crop_tab_region(frame: np.ndarray) -> np.ndarray:
    """Crop just the tab panel from a frame (full width, bottom portion)."""
    h = frame.shape[0]
    return frame[int(h * TAB_ROW_START):, :]


def crop_measure_number_region(tab_crop: np.ndarray) -> np.ndarray:
    """Crop the small patch containing the first measure number.

    This region is a digit on a white background and only changes when the
    panel refreshes, making it a highly reliable diff target.
    """
    h, w = tab_crop.shape[:2]
    y1 = int(h * MEASURE_ROW_START)
    y2 = int(h * MEASURE_ROW_END)
    x1 = int(w * MEASURE_COL_START)
    x2 = int(w * MEASURE_COL_END)
    return tab_crop[y1:y2, x1:x2]


def frame_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Return mean absolute difference between two frames, normalized 0–1."""
    ag = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(np.mean(np.abs(ag - bg)) / 255.0)


def is_tab_visible(tab_crop: np.ndarray) -> bool:
    """Return True if the tab region contains enough non-black content."""
    gray = cv2.cvtColor(tab_crop, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) > MIN_TAB_BRIGHTNESS


def frame_to_base64(frame: np.ndarray) -> str:
    """Encode a BGR frame as base64 PNG string."""
    success, buf = cv2.imencode(".png", frame)
    if not success:
        raise RuntimeError("Failed to encode frame as PNG")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def detect_panel_jumps(frames: list, fps: float = 4.0) -> list:
    """
    Scan frames and return indices where the tab panel jumps to a new set of measures.

    Diffs only the tiny measure-number region (first digit above the staff).
    This patch is static between jumps and changes dramatically on a real
    panel refresh, regardless of highlights, banners, or chord diagrams.

    The one-measure overlap between consecutive panels is intentional and is
    handled in the editor.
    """
    print(f"[extractor] Scanning {len(frames)} frames for panel jumps...")

    intro_skip = int(INTRO_SKIP_SECONDS * fps)
    min_gap    = max(1, int(MIN_PANEL_GAP_SECONDS * fps))

    tab_crops    = [crop_tab_region(f) for f in frames]
    number_crops = [crop_measure_number_region(tc) for tc in tab_crops]

    # Find first frame after the intro where the tab overlay is visible
    first_idx = None
    for i in range(intro_skip, len(frames)):
        if is_tab_visible(tab_crops[i]):
            first_idx = i
            break

    if first_idx is None:
        raise RuntimeError("No tab panel found in video after intro skip")

    print(f"  First tab panel at frame {first_idx}")
    jump_indices = [first_idx]
    last_jump = 0  # don't debounce against the first capture

    end_frame = int(len(number_crops) * VIDEO_END_FRACTION)
    for i in range(first_idx + 1, end_frame):
        if i - last_jump < min_gap:
            continue
        diff = frame_diff(number_crops[i - 1], number_crops[i])
        if diff > DIFF_THRESHOLD and is_tab_visible(tab_crops[i]):
            capture = min(i + 2, len(frames) - 1)
            jump_indices.append(capture)
            last_jump = i
            print(f"  Panel jump at frame {i} (diff={diff:.3f}), capturing frame {capture}")

    print(f"[extractor] Found {len(jump_indices)} panels")
    return jump_indices


def extract_panels(url: str) -> list:
    """
    Full pipeline: download → frames → detect jumps → return panel images.
    Returns list of {id, image} dicts with base64 PNG of the full tab crop.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        download_video(url, video_path)
        fps = 4.0
        frames = extract_frames(video_path, fps=fps)

    if not frames:
        raise RuntimeError("No frames extracted from video")

    jump_indices = detect_panel_jumps(frames, fps=fps)

    panels = []
    for idx in jump_indices:
        tab_crop = crop_tab_region(frames[idx])
        panels.append({
            "id": str(uuid.uuid4()),
            "image": frame_to_base64(tab_crop),
        })

    return panels
