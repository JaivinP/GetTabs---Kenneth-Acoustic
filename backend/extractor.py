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
MEASURE_ROW_START = 0.25
MEASURE_ROW_END   = 0.97
MEASURE_COL_START = 0.20
MEASURE_COL_END   = 0.85

# ── Detection thresholds ────────────────────────────────────────────────────
DIFF_THRESHOLD        = 0.028
MIN_PANEL_GAP_SECONDS = 2.5
INTRO_SKIP_SECONDS    = 3.0
MIN_TAB_BRIGHTNESS    = 40     # mean gray (0–255) for tab to count as visible / non-faded
VIDEO_END_FRACTION    = 0.95   # stop scanning here to avoid fade-out panels


def get_video_title(url: str) -> str:
    """Fetch the video title using yt-dlp without downloading."""
    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "--print", "title", url],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


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


def extract_frames(video_path: str, fps: float = 2.0):
    """Yield (sampled_index, frame) one at a time — never loads the full video into RAM."""
    print(f"[extractor] Streaming frames at {fps}fps from {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    video_fps     = cap.get(cv2.CAP_PROP_FPS)
    total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(video_fps / fps))
    end_video_frame = int(total_frames * VIDEO_END_FRACTION)

    sampled_idx   = 0
    video_idx     = 0
    while True:
        ret, frame = cap.read()
        if not ret or video_idx > end_video_frame:
            break
        if video_idx % frame_interval == 0:
            yield sampled_idx, frame
            sampled_idx += 1
        del frame
        video_idx += 1

    cap.release()


def crop_tab_region(frame: np.ndarray) -> np.ndarray:
    """Crop just the tab panel from a frame (full width, bottom portion)."""
    h = frame.shape[0]
    return frame[int(h * TAB_ROW_START):, :]


def crop_measure_number_region(tab_crop: np.ndarray) -> np.ndarray:
    """Crop the staff notation area used for change detection."""
    h, w = tab_crop.shape[:2]
    return tab_crop[int(h * MEASURE_ROW_START):int(h * MEASURE_ROW_END),
                    int(w * MEASURE_COL_START):int(w * MEASURE_COL_END)]


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


def detect_panel_jumps(frames, fps: float = 2.0) -> list:
    """
    Consume a frames generator and return panel image dicts.

    Keeps at most 2 measure crops in memory at any time. Full frames are
    released immediately after the tab crop is extracted. The panel images
    (base64 PNG) are encoded on detection and the raw array discarded.

    The one-measure overlap between consecutive panels is intentional and is
    handled in the editor.
    """
    intro_skip = int(INTRO_SKIP_SECONDS * fps)
    min_gap    = max(1, int(MIN_PANEL_GAP_SECONDS * fps))

    panels             = []
    first_captured     = False
    last_jump          = 0       # sampled index of last detected jump
    pending_capture_at = None    # sampled index at which to capture the settled frame
    prev_measure_crop  = None

    for sampled_idx, frame in frames:
        tab_crop = crop_tab_region(frame)
        del frame   # release full frame immediately

        # ── Pending capture: transition has settled, grab this frame ──────────
        if pending_capture_at is not None and sampled_idx >= pending_capture_at:
            if is_tab_visible(tab_crop):
                panels.append({"id": str(uuid.uuid4()), "image": frame_to_base64(tab_crop)})
                print(f"  Captured panel {len(panels)} at sampled frame {sampled_idx}")
            pending_capture_at = None

        # ── First visible panel after intro ───────────────────────────────────
        if not first_captured and sampled_idx >= intro_skip:
            if is_tab_visible(tab_crop):
                panels.append({"id": str(uuid.uuid4()), "image": frame_to_base64(tab_crop)})
                print(f"  First tab panel at sampled frame {sampled_idx}")
                first_captured = True
                last_jump = 0

        # ── Jump detection: diff consecutive measure crops ────────────────────
        if first_captured:
            curr_measure_crop = crop_measure_number_region(tab_crop)
            if prev_measure_crop is not None and sampled_idx - last_jump >= min_gap:
                diff = frame_diff(prev_measure_crop, curr_measure_crop)
                if diff > DIFF_THRESHOLD and is_tab_visible(tab_crop):
                    last_jump          = sampled_idx
                    pending_capture_at = sampled_idx + 2
                    print(f"  Panel jump at sampled frame {sampled_idx} (diff={diff:.3f})")
            del prev_measure_crop
            prev_measure_crop = curr_measure_crop   # keep only the latest crop

        del tab_crop

    del prev_measure_crop
    print(f"[extractor] Found {len(panels)} panels")
    return panels


def extract_panels(url: str) -> tuple:
    """Full pipeline: download → stream frames → detect jumps → return (panels, title)."""
    title = get_video_title(url)
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        download_video(url, video_path)
        fps = 2.0
        panels = detect_panel_jumps(extract_frames(video_path, fps=fps), fps=fps)
    return panels, title


def extract_panels_from_file(file_bytes: bytes) -> list:
    """File-upload pipeline: save bytes → stream frames → detect jumps → return panel image dicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "upload.mp4")
        with open(video_path, "wb") as f:
            f.write(file_bytes)
        fps = 2.0
        return detect_panel_jumps(extract_frames(video_path, fps=fps), fps=fps)
