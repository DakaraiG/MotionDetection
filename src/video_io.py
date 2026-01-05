from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import cv2

@dataclass
class VideoMeta:
    fps: float
    width: int
    height: int
    frame_count: int

def open_video(path: Path) -> tuple[cv2.VideoCapture, VideoMeta]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    meta = VideoMeta(fps=fps, width=width, height=height, frame_count=frame_count)
    return cap, meta

def make_writer(path: Path, fps: float, width: int, height: int) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # cross-platform safe
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create VideoWriter: {path}")
    return writer
