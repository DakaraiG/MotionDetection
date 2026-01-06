from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import AppConfig
from processor import process_video

class SmartCamGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MotionDetection")
        self.geometry("820x520")

        self.input_path: Path | None = None

        self.cfg = AppConfig()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        # Window Buttons
        ttk.Button(top, text="Select Video", command=self.pick_video).pack(side="left")
        ttk.Button(top, text="Run", command=self.run_processing).pack(side="left", padx=8)

        out_btn = ttk.Button(top, text="Open Output Folder", command=self.open_output_folder)
        out_btn.pack(side="left", padx=8)

        #Config Sliders
        settings = ttk.LabelFrame(self, text="Settings", padding=10)
        settings.pack(fill="x", padx=10, pady=(0, 10))

        self.thresh = tk.IntVar(value=self.cfg.diff_threshold)
        self.min_area = tk.IntVar(value=self.cfg.min_contour_area)

        ttk.Label(settings, text="Diff threshold").grid(row=0, column=0, sticky="w")
        ttk.Scale(settings, from_=5, to=80, variable=self.thresh, orient="horizontal").grid(row=0, column=1, sticky="ew", padx=8)

        ttk.Label(settings, text="Min contour area").grid(row=1, column=0, sticky="w", pady=(8,0))
        ttk.Scale(settings, from_=100, to=8000, variable=self.min_area, orient="horizontal").grid(row=1, column=1, sticky="ew", padx=8, pady=(8,0))

        settings.columnconfigure(1, weight=1)

        #Log Box
        status = ttk.LabelFrame(self, text="Status", padding=10)
        status.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log = tk.Text(status, height=12, wrap="word")
        self.log.pack(fill="both", expand=True)

        self.log.config(state="disabled")

        self.write_log("Ready. Select a video.")
    #
    def write_log(self, msg: str):
        self.log.config(state="normal")  # allow insert
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")  # lock again
        self.update_idletasks()

    def pick_video(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")]
        )
        if not path:
            return
        self.input_path = Path(path)
        self.write_log(f"Selected: {self.input_path}")

    def run_processing(self):
        if not self.input_path:
            messagebox.showwarning("No video", "Please select a video first.")
            return

        self.cfg.diff_threshold = int(self.thresh.get())
        self.cfg.min_contour_area = int(self.min_area.get())

        try:
            self.write_log(f"Processing with threshold={self.cfg.diff_threshold}, min_area={self.cfg.min_contour_area} ...")
            res = process_video(self.input_path, self.cfg, log_fn=self.write_log)
            messagebox.showinfo("Done", f"Saved highlight + CSV.\nEvents: {res.event_count}\n\n{res.highlight_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.write_log(f"ERROR: {e}")
    #s
    def open_output_folder(self):
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

def run_gui():
    app = SmartCamGUI()
    app.mainloop()
