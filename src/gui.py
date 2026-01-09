from __future__ import annotations

import tkinter as tk
import threading
import queue
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import AppConfig
from processor import processVideo
from live_feed_window import LiveFeedWindow


class SmartCamGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MotionDetection")
        self.geometry("900x650")

        # State
        self.inputPath: Path | None = None
        self.cfg = AppConfig()
        self.liveWindow = None


        # Background processing (keeps UI responsive on large videos)
        self.logQueue = queue.Queue()
        self.isProcessing = False
        self.after(100, self._drainLogQueue)
        #Top Controls
        topFrame = ttk.Frame(self, padding=10)
        topFrame.pack(fill="x")

        self.selectBtn = ttk.Button(topFrame, text="Select Video", command=self.pickVideo)
        self.selectBtn.pack(side="left")

        self.runBtn = ttk.Button(topFrame, text="Run", command=self.runProcessing)
        self.runBtn.pack(side="left", padx=8)

        self.outBtn = ttk.Button(topFrame, text="Open Output Folder", command=self.openOutputFolder)
        self.outBtn.pack(side="left", padx=8)

        self.liveBtn = ttk.Button(topFrame, text="Live Feed", command=self.openLiveFeedWindow)
        self.liveBtn.pack(side="left", padx=8)


        # Progress indicator
        self.progressValue = tk.DoubleVar(value=0.0)
        self.progressBar = ttk.Progressbar(self, mode="determinate", maximum=100, variable=self.progressValue)
        # Hidden by default
        

        #Detection Settings
        self.settingsFrame = ttk.LabelFrame(self, text="Detection Settings", padding=10)
        self.settingsFrame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(self.settingsFrame, text="Preset").grid(row=0, column=0, sticky="w")
        self.preset = tk.StringVar(value="Balanced")
        presetBox = ttk.Combobox(
            self.settingsFrame,
            textvariable=self.preset,
            values=["Low sensitivity", "Balanced", "High sensitivity"],
            state="readonly",
            width=18,
        )
        presetBox.grid(row=0, column=1, sticky="w", padx=8)

        # Slider variables
        self.diffThreshold = tk.IntVar(value=self.cfg.diff_threshold)
        self.minArea = tk.IntVar(value=self.cfg.min_contour_area)

        self.diffThresholdValue = ttk.Label(self.settingsFrame, text=f"{self.diffThreshold.get()} / 255 levels")
        self.minAreaValue = ttk.Label(self.settingsFrame, text=f"{self.minArea.get()} px²")

        # Sensitivity slider
        ttk.Label(self.settingsFrame, text="Motion sensitivity").grid(row=1, column=0, sticky="w", pady=(10, 0))
        diffThresholdSlider = ttk.Scale(
            self.settingsFrame,
            from_=5,
            to=80,
            variable=self.diffThreshold,
            orient="horizontal",
            command=lambda _=None: self.updateSliderLabels(),
        )
        diffThresholdSlider.grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.diffThresholdValue.grid(row=1, column=2, sticky="w", pady=(10, 0))

        ttk.Label(
            self.settingsFrame,
            text="Higher sensitivity detects smaller movement, but may increase false alerts.",
        ).grid(row=2, column=0, columnspan=3, sticky="w")

        # Minimum movement area slider
        ttk.Label(self.settingsFrame, text="Ignore small movement").grid(row=3, column=0, sticky="w", pady=(10, 0))
        minAreaSlider = ttk.Scale(
            self.settingsFrame,
            from_=100,
            to=8000,
            variable=self.minArea,
            orient="horizontal",
            command=lambda _=None: self.updateSliderLabels(),
        )
        minAreaSlider.grid(row=3, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.minAreaValue.grid(row=3, column=2, sticky="w", pady=(10, 0))

        ttk.Label(
            self.settingsFrame,
            text="Higher values ignore small flicker/noise.",
        ).grid(row=4, column=0, columnspan=3, sticky="w")

        self.settingsFrame.columnconfigure(1, weight=1)

        def applyPreset(*_):
            presetName = self.preset.get()
            if presetName == "Low sensitivity":
                self.diffThreshold.set(40)
                self.minArea.set(1500)
            elif presetName == "High sensitivity":
                self.diffThreshold.set(15)
                self.minArea.set(400)
            else:
                self.diffThreshold.set(25)
                self.minArea.set(800)

            self.updateSliderLabels()

        presetBox.bind("<<ComboboxSelected>>", applyPreset)
        self.updateSliderLabels()

        #Status / Log
        statusFrame = ttk.LabelFrame(self, text="Status", padding=10)
        statusFrame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.logBox = tk.Text(statusFrame, height=12, wrap="word")
        self.logBox.pack(fill="both", expand=True)
        self.logBox.config(state="disabled")

        self.writeLog("Ready. Select a video (or open Live Feed).")

        # Close handler
        self.protocol("WM_DELETE_WINDOW", self.onClose)

    #Logging
    def writeLog(self, msg: str):
        self.logBox.config(state="normal")
        self.logBox.insert("end", msg + "\n")
        self.logBox.see("end")
        self.logBox.config(state="disabled")
        self.update_idletasks()


    #Progress Bar Helpers
    def _showProgressBar(self):
        # Place progress bar just under the top controls (only when needed)
        if not self.progressBar.winfo_ismapped():
            self.progressBar.pack(fill="x", padx=10, pady=(0, 10), before=self.settingsFrame)

    def _hideProgressBar(self):
        if self.progressBar.winfo_ismapped():
            self.progressBar.pack_forget()
        self.progressValue.set(0.0)

    def _startFakeProgress(self):
        # Smooth fill up to ~95% while processing runs
        self.progressValue.set(0.0)
        self._showProgressBar()
        self._progressTick()

    def _progressTick(self):
        if not getattr(self, "isProcessing", False):
            return

        value = float(self.progressValue.get())
        if value < 98.0:
            # Ease-out towards 95%
            step = max(0.1, (98.0 - value) * 0.01)
            value = min(95.0, value + step)
            self.progressValue.set(value)

        self._progressAfterId = self.after(300, self._progressTick)

    def _completeProgress(self):
        # Jump to 100% then hide shortly after
        try:
            if hasattr(self, "_progressAfterId") and self._progressAfterId is not None:
                self.after_cancel(self._progressAfterId)
        except Exception:
            pass

        self.progressValue.set(100.0)
        self.after(500, self._hideProgressBar)

    def _drainLogQueue(self):
        try:
            while True:
                msg = self.logQueue.get_nowait()
                self.writeLog(msg)
        except queue.Empty:
            pass
        self.after(100, self._drainLogQueue)

    def _finishProcessingUi(self):
        self.isProcessing = False
        try:
            self.runBtn.config(state="normal")
            self.selectBtn.config(state="normal")
            self.outBtn.config(state="normal")
            self.liveBtn.config(state="normal")
            self._completeProgress()
        except Exception:
            pass


    #Settings UI helpers
    def updateSliderLabels(self):
        t = int(self.diffThreshold.get())
        a = int(self.minArea.get())
        self.diffThresholdValue.config(text=f"{t} / 255 levels")
        self.minAreaValue.config(text=f"{a} px²")
        if self.liveWindow is not None and self.liveWindow.winfo_exists():
            self.liveWindow.setMotionParams(self.diffThreshold.get(), self.minArea.get())

    #Live Feed Window
    def openLiveFeedWindow(self):
        if self.liveWindow is not None and self.liveWindow.winfo_exists():
            self.liveWindow.lift()
            self.liveWindow.focus_force()
            return

        self.liveWindow = LiveFeedWindow(self, logFn=self.writeLog)
        self.liveWindow.setMotionParams(self.diffThreshold.get(), self.minArea.get())

    #Video file processing
    def pickVideo(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.inputPath = Path(path)
        self.writeLog(f"Selected: {self.inputPath}")

    def runProcessing(self):
        if self.isProcessing:
            messagebox.showinfo("Busy", "Processing is already running.")
            return

        if not self.inputPath:
            messagebox.showwarning("No video", "Please select a video first.")
            return

        # Push GUI settings into config (backend uses snake_case)
        self.cfg.diff_threshold = int(self.diffThreshold.get())
        self.cfg.min_contour_area = int(self.minArea.get())

        self.isProcessing = True

        # Disable controls during processing to prevent double-run
        try:
            self.runBtn.config(state="disabled")
            self.selectBtn.config(state="disabled")
            self.outBtn.config(state="disabled")
            self.liveBtn.config(state="disabled")
        except Exception:
            pass

        # Start a determinate-style (fake) progress bar while processing runs in background
        self._startFakeProgress()

        self.logQueue.put(
            f"Processing started: {self.inputPath.name} "
            f"(threshold={self.cfg.diff_threshold}, minArea={self.cfg.min_contour_area})"
        )

        def worker():
            try:
                res = processVideo(
                    self.inputPath,
                    self.cfg,
                    logFn=lambda m: self.logQueue.put(m),
                )
                self.logQueue.put(f"Done. Events: {res.eventCount}")
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Done",
                        f"Saved highlight + CSV.\nEvents: {res.eventCount}\n\n{res.highlightPath}",
                    ),
                )
            except Exception as e:
                self.logQueue.put(f"ERROR: {e}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, self._finishProcessingUi)

        threading.Thread(target=worker, daemon=True).start()

    def openOutputFolder(self):
        import os
        import subprocess
        import sys

        p = self.cfg.output_dir.resolve()
        p.mkdir(parents=True, exist_ok=True)

        if sys.platform.startswith("darwin"):
            subprocess.run(["open", str(p)])
        elif os.name == "nt":
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(p)])

    #Close
    def onClose(self):
        # Close live feed window if open (this also stops the camera safely)
        try:
            if self.liveWindow is not None and self.liveWindow.winfo_exists():
                self.liveWindow.onClose()
        except Exception:
            pass

        self.destroy()


def run_gui():
    app = SmartCamGUI()
    app.mainloop()