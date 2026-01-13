from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import csv
from pathlib import Path
from PIL import Image, ImageTk

from live_feed import LiveFeedController, LiveFeedConfig

import cv2
from live_motion import LiveMotionDetector, LiveMotionConfig
from events import EventBuilder
from config import AppConfig


class LiveFeedWindow(tk.Toplevel):
    def __init__(self, parent, cfg: AppConfig, logFn=None):
        super().__init__(parent)
        self.title("Live Video Feed")
        self.geometry("900x600")

        self.logFn = logFn
        self.cfg = cfg
        self.outputDir = Path(self.cfg.output_dir)

        # Controller
        self.liveCfg = LiveFeedConfig(camera_index=0, target_fps=25, flip_horizontal=False)
        self.liveController = LiveFeedController(self.liveCfg)

        # Motion detector (defaults syncs from main GUI settings)
        self.motionCfg = LiveMotionConfig(diff_threshold=25, min_contour_area=800)
        self.motionDetector = LiveMotionDetector(self.motionCfg)
        self.motionEnabled = tk.BooleanVar(value=True)

        self.liveEventBuilder: EventBuilder | None = None
        self.liveFrameIdx = 0
        self.liveSessionActive = False
        self.liveEventsCsvPath: Path | None = None

        self.liveAfterId = None
        self.liveTkImage = None

        # Top bar
        topBar = ttk.Frame(self, padding=10)
        topBar.pack(fill="x")

        self.liveStatus = tk.StringVar(value="Stopped")
        ttk.Label(topBar, textvariable=self.liveStatus).pack(side="left")

        self.startBtn = ttk.Button(topBar, text="Start", command=self.startLiveFeed)
        self.startBtn.pack(side="left", padx=8)

        self.stopBtn = ttk.Button(topBar, text="Stop", command=self.stopLiveFeed, state="disabled")
        self.stopBtn.pack(side="left")

        # mirror toggle
        self.flipVar = tk.BooleanVar(value=self.liveCfg.flip_horizontal)
        flipChk = ttk.Checkbutton(topBar, text="Mirror", variable=self.flipVar, command=self.applyFlip)
        flipChk.pack(side="right")

        # Video area
        self.imageLabel = ttk.Label(self)
        self.imageLabel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        #motion toggle
        motionChk = ttk.Checkbutton(topBar, text="Motion overlay", variable=self.motionEnabled)
        motionChk.pack(side="right", padx=8)

        # Close behaviour
        self.protocol("WM_DELETE_WINDOW", self.onClose)

    def setMotionParams(self, diffThreshold: int, minArea: int):
        self.motionCfg.diff_threshold = int(diffThreshold)
        self.motionCfg.min_contour_area = int(minArea)

    def writeLog(self, msg: str):
        if self.logFn:
            self.logFn(msg)

    def applyFlip(self):
        self.liveCfg.flip_horizontal = bool(self.flipVar.get())

    def startLiveFeed(self):
        try:
            self.liveController.startFeed()
        except Exception as e:
            messagebox.showerror(
                "Camera Permission / Access",
                str(e),
            )
            self.writeLog(f"ERROR (Live Feed): {e}")
            return

        self.motionDetector.reset()
        self.liveEventBuilder = EventBuilder(
            self.cfg.pre_roll_frames,
            self.cfg.post_roll_frames,
            self.cfg.min_event_frames,
        )
        self.liveFrameIdx = 0
        self.liveSessionActive = True
        self.outputDir.mkdir(parents=True, exist_ok=True)
        self.liveEventsCsvPath = self.outputDir / self.cfg.live_events_csv_name

        self.liveStatus.set("Running")
        self.startBtn.config(state="disabled")
        self.stopBtn.config(state="normal")
        self.writeLog("Live feed started.")
        self._scheduleNextFrame()

    def stopLiveFeed(self):
        if self.liveAfterId is not None:
            try:
                self.after_cancel(self.liveAfterId)
            except Exception:
                pass
            self.liveAfterId = None

        self.liveController.stopFeed()
        self._finalizeLiveEvents()
        self.liveStatus.set("Stopped")
        self.startBtn.config(state="normal")
        self.stopBtn.config(state="disabled")
        self.imageLabel.config(image="")
        self.liveTkImage = None
        self.writeLog("Live feed stopped.")
    # Finalize live events and save to CSV
    def _finalizeLiveEvents(self):
        if not self.liveSessionActive or self.liveEventBuilder is None or self.liveEventsCsvPath is None:
            return

        self.liveEventBuilder.finalize(self.liveFrameIdx)
        fps = max(1, float(self.liveCfg.target_fps))

        with open(self.liveEventsCsvPath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["event_id", "start_frame", "end_frame", "start_s", "end_s", "duration_s", "bbox_x", "bbox_y", "bbox_w", "bbox_h"])
            for ev in self.liveEventBuilder.events:
                startS = ev.startIdx / fps
                endS = ev.endIdx / fps
                dur = endS - startS
                if ev.bbox:
                    x, y, bw, bh = ev.bbox
                else:
                    x = y = bw = bh = ""
                w.writerow([ev.id, ev.startIdx, ev.endIdx, f"{startS:.3f}", f"{endS:.3f}", f"{dur:.3f}", x, y, bw, bh])

        self.writeLog(f"Saved live events CSV: {self.liveEventsCsvPath}")
        self.liveSessionActive = False

    def _scheduleNextFrame(self):
        delayMs = self.liveController.getDelayMs()
        self.liveAfterId = self.after(delayMs, self._updateFrame)

    def _resizeToFit(self, frameRgb, targetW: int, targetH: int):
        h, w = frameRgb.shape[:2]
        if targetW <= 1 or targetH <= 1:
            return frameRgb

        scale = min(targetW / w, targetH / h)
        newW = max(1, int(w * scale))
        newH = max(1, int(h * scale))

        import cv2
        return cv2.resize(frameRgb, (newW, newH), interpolation=cv2.INTER_AREA)

    def _updateFrame(self):
        frameRgb = self.liveController.readFrameRgb()
        if frameRgb is None:
            self.writeLog("Live feed frame read failed. Stopping feed.")
            self.stopLiveFeed()
            return

        self.liveFrameIdx += 1

        # Motion detection
        if bool(self.motionEnabled.get()):
            motionRes = self.motionDetector.update(frameRgb)

            # Draw overlays onto RGB frame
            for (x, y, w, h) in motionRes.boxes:
                cv2.rectangle(frameRgb, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if motionRes.hasMotion:
                cv2.putText(
                    frameRgb, "MOTION",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 0, 0),
                    2,
                    cv2.LINE_AA
                )

            if self.liveEventBuilder is not None:
                self.liveEventBuilder.update(self.liveFrameIdx, motionRes.hasMotion, motionRes.boxes)

        targetW = self.imageLabel.winfo_width()
        targetH = self.imageLabel.winfo_height()

        if targetW <= 1 or targetH <= 1:
            self.liveAfterId = self.after(50, self._updateFrame)
            return

        frameRgb = self._resizeToFit(frameRgb, targetW, targetH)

        pilImage = Image.fromarray(frameRgb)
        self.liveTkImage = ImageTk.PhotoImage(pilImage)
        self.imageLabel.config(image=self.liveTkImage)

        self._scheduleNextFrame()

    def onClose(self):
        try:
            self.stopLiveFeed()
        except Exception:
            pass
        self.destroy()
