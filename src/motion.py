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

def detectMotion(
    prevBgr: np.ndarray,
    currBgr: np.ndarray,
    diffThreshold: int,
    minContourArea: int,
    blurKernel: int,
    erodeIters: int,
    dilateIters: int,
) -> MotionResult:
    # Convert to gray for robustness
    prev = cv2.cvtColor(prevBgr, cv2.COLOR_BGR2GRAY)
    curr = cv2.cvtColor(currBgr, cv2.COLOR_BGR2GRAY)

    # Frame differencing
    diff = cv2.absdiff(prev, curr)

    # Blur -> threshold -> morphology
    k = blurKernel if blurKernel % 2 == 1 else blurKernel + 1
    diff = cv2.GaussianBlur(diff, (k, k), 0)

    _, th = cv2.threshold(diff, diffThreshold, 255, cv2.THRESH_BINARY)

    if erodeIters > 0:
        th = cv2.erode(th, None, iterations=erodeIters)
    if dilateIters > 0:
        th = cv2.dilate(th, None, iterations=dilateIters)

    # Contours
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < minContourArea:
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
