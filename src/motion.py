from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import cv2
import numpy as np

@dataclass
class MotionResult:
    motion: bool
    mask: np.ndarray                 # binary motion mask
    boxes: List[Tuple[int, int, int, int]]  # (x, y, w, h)
    score: float                     # simple motion score

def detect_motion(
    prev_bgr: np.ndarray,
    curr_bgr: np.ndarray,
    diff_threshold: int,
    min_contour_area: int,
    blur_kernel: int,
    erode_iters: int,
    dilate_iters: int,
) -> MotionResult:
    # Convert to gray for robustness
    prev = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY)
    curr = cv2.cvtColor(curr_bgr, cv2.COLOR_BGR2GRAY)

    # Frame differencing
    diff = cv2.absdiff(prev, curr)

    # Blur -> threshold -> morphology
    k = blur_kernel if blur_kernel % 2 == 1 else blur_kernel + 1
    diff = cv2.GaussianBlur(diff, (k, k), 0)

    _, th = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)

    if erode_iters > 0:
        th = cv2.erode(th, None, iterations=erode_iters)
    if dilate_iters > 0:
        th = cv2.dilate(th, None, iterations=dilate_iters)

    # Contours
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_contour_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        boxes.append((x, y, w, h))

    # Motion score = % of pixels flagged
    score = float(np.mean(th > 0))

    return MotionResult(
        motion=len(boxes) > 0,
        mask=th,
        boxes=boxes,
        score=score,
    )
