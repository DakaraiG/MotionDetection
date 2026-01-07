from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import sys

import cv2


@dataclass
class LiveFeedConfig:
    camera_index: int = 0
    target_fps: int = 25
    flip_horizontal: bool = False


class LiveFeedController:
    def __init__(self, cfg: LiveFeedConfig):
        self.cfg = cfg
        self.cap: Optional[cv2.VideoCapture] = None

    def startFeed(self) -> None:
        if self.cap is not None:
            return

        # macOS: prefer AVFoundation backend
        if sys.platform == "darwin":
            cap = cv2.VideoCapture(self.cfg.camera_index, cv2.CAP_AVFOUNDATION)
        else:
            cap = cv2.VideoCapture(self.cfg.camera_index)

        if not cap.isOpened():
            cap.release()
            raise RuntimeError(
                "Could not open camera.\n\n"
                "macOS: System Settings → Privacy & Security → Camera\n"
                "Enable access for the app you are running under (VS Code / Terminal / PyCharm).\n"
                "Also close Zoom/Teams/Chrome tabs that may be using the camera."
            )

        # Force a first frame read (helps surface issues early)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            raise RuntimeError(
                "Camera opened but no frames were received.\n\n"
                "This is usually permissions or another app using the camera."
            )

        self.cap = cap

    def stopFeed(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def readFrameRgb(self):
        """
        Returns an RGB frame as a numpy array (H, W, 3), or None if unavailable.
        """
        if self.cap is None:
            return None

        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None

        if self.cfg.flip_horizontal:
            frame = cv2.flip(frame, 1)

        # OpenCV gives BGR; GUI expects RGB
        frameRgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frameRgb

    def getDelayMs(self) -> int:
        fps = max(1, int(self.cfg.target_fps))
        return int(1000 / fps)

