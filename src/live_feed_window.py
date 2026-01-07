from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from live_feed import LiveFeedController, LiveFeedConfig


class LiveFeedWindow(tk.Toplevel):
    def __init__(self, parent, logFn=None):
        super().__init__(parent)
        self.title("Live Video Feed")
        self.geometry("900x600")

        self.logFn = logFn

        # Controller
        self.liveCfg = LiveFeedConfig(camera_index=0, target_fps=25, flip_horizontal=False)
        self.liveController = LiveFeedController(self.liveCfg)

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

        # Optional: mirror
        self.flipVar = tk.BooleanVar(value=self.liveCfg.flip_horizontal)
        flipChk = ttk.Checkbutton(topBar, text="Mirror", variable=self.flipVar, command=self.applyFlip)
        flipChk.pack(side="right")

        # Video area
        self.imageLabel = ttk.Label(self)
        self.imageLabel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Close behaviour
        self.protocol("WM_DELETE_WINDOW", self.onClose)

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
        self.liveStatus.set("Stopped")
        self.startBtn.config(state="normal")
        self.stopBtn.config(state="disabled")
        self.imageLabel.config(image="")
        self.liveTkImage = None
        self.writeLog("Live feed stopped.")

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

        targetW = self.imageLabel.winfo_width()
        targetH = self.imageLabel.winfo_height()

        # Layout not ready yet
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
