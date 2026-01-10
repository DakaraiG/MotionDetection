from dataclasses import dataclass, field
import os
from pathlib import Path

def _default_output_dir() -> Path:
    env = os.getenv("MOTIONDETECTION_OUTPUT_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "MotionDetection" / "output"

@dataclass
class AppConfig:
    # Motion detection
    diff_threshold: int = 25          # pixel intensity threshold
    min_contour_area: int = 800       # reject tiny blobs
    blur_kernel: int = 5              # Gaussian blur kernel size (odd)
    dilate_iters: int = 2
    erode_iters: int = 1

    # Event segmentation
    pre_roll_frames: int = 10         # include frames before motion starts
    post_roll_frames: int = 15        # include frames after motion ends
    min_event_frames: int = 8         # ignore very short events

    # Output
    output_dir: Path = field(default_factory=_default_output_dir)
    events_dirname: str = "events"
    highlight_name: str = "highlight.mp4"
    events_csv_name: str = "events.csv"
