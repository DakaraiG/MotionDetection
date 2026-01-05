from dataclasses import dataclass
from pathlib import Path

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
    output_dir: Path = Path("output")
    events_dirname: str = "events"
    highlight_name: str = "highlight.mp4"
    events_csv_name: str = "events.csv"
