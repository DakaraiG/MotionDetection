from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

import cv2
import numpy as np


@dataclass
class LiveMotionConfig:
    # Sensitivity controls
    diff_threshold: int = 25           # 0–255 grayscale levels
    min_contour_area: int = 800        # px^2
    blur_ksize: int = 21               # must be odd
    morph_iters: int = 2

    # Background model (running average)
    alpha: float = 0.05                # higher = adapts faster
    warmup_frames: int = 15            # ignore motion until background stabilizes


@dataclass
class MotionResult:
    hasMotion: bool
    boxes: List[Tuple[int, int, int, int]]  # x, y, w, h
    motionScore: float                      # 0..1 fraction of mask pixels


class LiveMotionDetector:
    def __init__(self, cfg: LiveMotionConfig):
        self.cfg = cfg
        self.bg: Optional[np.ndarray] = None
        self.frameCount = 0

    def reset(self):
        self.bg = None
        self.frameCount = 0

    def update(self, frameRgb: np.ndarray) -> MotionResult:
        """
        frameRgb: RGB numpy array (H, W, 3)
        returns MotionResult with bounding boxes in image coordinates.
        """
        self.frameCount += 1

        frameGray = cv2.cvtColor(frameRgb, cv2.COLOR_RGB2GRAY)

        k = int(self.cfg.blur_ksize)
        if k % 2 == 0:
            k += 1
        frameGray = cv2.GaussianBlur(frameGray, (k, k), 0)

        if self.bg is None:
            self.bg = frameGray.astype("float32")
            return MotionResult(False, [], 0.0)

        # Running average background
        cv2.accumulateWeighted(frameGray, self.bg, self.cfg.alpha)
        bgUint8 = cv2.convertScaleAbs(self.bg)

        diff = cv2.absdiff(frameGray, bgUint8)

        _, mask = cv2.threshold(diff, int(self.cfg.diff_threshold), 255, cv2.THRESH_BINARY)
        mask = cv2.dilate(mask, None, iterations=int(self.cfg.morph_iters))
        mask = cv2.erode(mask, None, iterations=max(1, int(self.cfg.morph_iters) - 1))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: List[Tuple[int, int, int, int]] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < int(self.cfg.min_contour_area):
                continue
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))

        motionScore = float(np.count_nonzero(mask)) / float(mask.size)

        # Ignore motion during warmup
        if self.frameCount < int(self.cfg.warmup_frames):
            return MotionResult(False, [], motionScore)

        return MotionResult(len(boxes) > 0, boxes, motionScore)
