from __future__ import annotations

import tkinter as tk
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

        #Detection Settings
        settingsFrame = ttk.LabelFrame(self, text="Detection Settings", padding=10)
        settingsFrame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(settingsFrame, text="Preset").grid(row=0, column=0, sticky="w")
        self.preset = tk.StringVar(value="Balanced")
        presetBox = ttk.Combobox(
            settingsFrame,
            textvariable=self.preset,
            values=["Low sensitivity", "Balanced", "High sensitivity"],
            state="readonly",
            width=18,
        )
        presetBox.grid(row=0, column=1, sticky="w", padx=8)

        # Slider variables
        self.diffThreshold = tk.IntVar(value=self.cfg.diff_threshold)
        self.minArea = tk.IntVar(value=self.cfg.min_contour_area)

        self.diffThresholdValue = ttk.Label(settingsFrame, text=f"{self.diffThreshold.get()} / 255 levels")
        self.minAreaValue = ttk.Label(settingsFrame, text=f"{self.minArea.get()} px²")

        # Sensitivity slider
        ttk.Label(settingsFrame, text="Motion sensitivity").grid(row=1, column=0, sticky="w", pady=(10, 0))
        diffThresholdSlider = ttk.Scale(
            settingsFrame,
            from_=5,
            to=80,
            variable=self.diffThreshold,
            orient="horizontal",
            command=lambda _=None: self.updateSliderLabels(),
        )
        diffThresholdSlider.grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.diffThresholdValue.grid(row=1, column=2, sticky="w", pady=(10, 0))

        ttk.Label(
            settingsFrame,
            text="Higher sensitivity detects smaller movement, but may increase false alerts.",
        ).grid(row=2, column=0, columnspan=3, sticky="w")

        # Minimum movement area slider
        ttk.Label(settingsFrame, text="Ignore small movement").grid(row=3, column=0, sticky="w", pady=(10, 0))
        minAreaSlider = ttk.Scale(
            settingsFrame,
            from_=100,
            to=8000,
            variable=self.minArea,
            orient="horizontal",
            command=lambda _=None: self.updateSliderLabels(),
        )
        minAreaSlider.grid(row=3, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.minAreaValue.grid(row=3, column=2, sticky="w", pady=(10, 0))

        ttk.Label(
            settingsFrame,
            text="Higher values ignore small flicker/noise.",
        ).grid(row=4, column=0, columnspan=3, sticky="w")

        settingsFrame.columnconfigure(1, weight=1)

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

    #Settings UI helpers
    def updateSliderLabels(self):
        t = int(self.diffThreshold.get())
        a = int(self.minArea.get())
        self.diffThresholdValue.config(text=f"{t} / 255 levels")
        self.minAreaValue.config(text=f"{a} px²")

    #Live Feed Window
    def openLiveFeedWindow(self):
        if self.liveWindow is not None and self.liveWindow.winfo_exists():
            self.liveWindow.lift()
            self.liveWindow.focus_force()
            return

        self.liveWindow = LiveFeedWindow(self, logFn=self.writeLog)

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
        if not self.inputPath:
            messagebox.showwarning("No video", "Please select a video first.")
            return

        # Push GUI settings into config
        self.cfg.diff_threshold = int(self.diffThreshold.get())
        self.cfg.min_contour_area = int(self.minArea.get())

        try:
            self.writeLog(
                f"Processing with threshold={self.cfg.diff_threshold}, minArea={self.cfg.min_contour_area} ..."
            )
            res = processVideo(self.inputPath, self.cfg, logFn=self.writeLog)
            messagebox.showinfo(
                "Done",
                f"Saved highlight + CSV.\nEvents: {res.eventCount}\n\n{res.highlightPath}",
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.writeLog(f"ERROR: {e}")

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

