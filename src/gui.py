from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import AppConfig
from processor import processVideo

class SmartCamGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MotionDetection")
        self.geometry("820x520")

        self.inputPath: Path | None = None

        self.cfg = AppConfig()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        # Window Buttons
        ttk.Button(top, text="Select Video", command=self.pickVideo).pack(side="left")
        ttk.Button(top, text="Run", command=self.runProcessing).pack(side="left", padx=8)

        outBtn = ttk.Button(top, text="Open Output Folder", command=self.openOutputFolder)
        outBtn.pack(side="left", padx=8)

        #Config Sliders
        settings = ttk.LabelFrame(self, text="Settings", padding=10)
        settings.pack(fill="x", padx=10, pady=(0, 10))

        self.diffThreshold = tk.IntVar(value=self.cfg.diff_threshold)
        self.minArea = tk.IntVar(value=self.cfg.min_contour_area)

        ttk.Label(settings, text="Diff threshold").grid(row=0, column=0, sticky="w")
        ttk.Scale(settings, from_=5, to=80, variable=self.diffThreshold, orient="horizontal").grid(row=0, column=1, sticky="ew", padx=8)

        ttk.Label(settings, text="Min contour area").grid(row=1, column=0, sticky="w", pady=(8,0))
        ttk.Scale(settings, from_=100, to=8000, variable=self.minArea, orient="horizontal").grid(row=1, column=1, sticky="ew", padx=8, pady=(8,0))

        settings.columnconfigure(1, weight=1)

        #Log Box
        status = ttk.LabelFrame(self, text="Status", padding=10)
        status.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log = tk.Text(status, height=12, wrap="word")
        self.log.pack(fill="both", expand=True)

        self.log.config(state="disabled")

        self.writeLog("Ready. Select a video.")
    #
    def writeLog(self, msg: str):
        self.log.config(state="normal")  # allow insert
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")  # lock again
        self.update_idletasks()

    def pickVideo(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")]
        )
        if not path:
            return
        self.inputPath = Path(path)
        self.writeLog(f"Selected: {self.inputPath}")

    def runProcessing(self):
        if not self.inputPath:
            messagebox.showwarning("No video", "Please select a video first.")
            return

        self.cfg.diff_threshold = int(self.diffThreshold.get())
        self.cfg.min_contour_area = int(self.minArea.get())

        try:
            self.writeLog(f"Processing with threshold={self.cfg.diff_threshold}, minArea={self.cfg.min_contour_area} ...")
            res = processVideo(self.inputPath, self.cfg, logFn=self.writeLog)
            messagebox.showinfo("Done", f"Saved highlight + CSV.\nEvents: {res.eventCount}\n\n{res.highlightPath}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.writeLog(f"ERROR: {e}")
    #s
    def openOutputFolder(self):
        # Cross-platform open folder
        import os, subprocess, sys
        p = self.cfg.output_dir.resolve()
        p.mkdir(parents=True, exist_ok=True)

        if sys.platform.startswith("darwin"):
            subprocess.run(["open", str(p)])
        elif os.name == "nt":
            os.startfile(str(p))  # type: ignore
        else:
            subprocess.run(["xdg-open", str(p)])

def runGui():
    app = SmartCamGUI()
    app.mainloop()
