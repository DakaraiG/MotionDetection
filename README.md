# Motion Detection

Desktop applicaton for detecting motion in videos and a live camera feed. It can generate a highlighted video and an events CSV for quick review.

## Features

- GUI with presets and sliders for sensitivity and minimum movement area
- Batch processing of a video file into a highlighted MP4 and events CSV
- Live camera feed with motion overlays and optional mirroring
- Lightweight, local-only processing (no network calls)

## Requirements

- Python 3.9+
- OpenCV, Pillow, NumPy
- Tkinter (bundled with most Python installs)

## Setup

Get the latest [Release](https://github.com/DakaraiG/MotionDetection/releases)

or 

```bash
python -m venv .venv
source .venv/bin/activate
pip install opencv-python pillow numpy
```

## Run

```bash
python src/main.py
```

## Using The App

1. Click "Select Video" and choose an input file.
2. Adjust "Motion sensitivity" and "Ignore small movement" or pick a preset.
3. Click "Run" to generate outputs.
4. Use "Open Output Folder" to inspect results.
5. Click "Live Feed" to open the camera window.

## Output Files

- `~/MotionDetection/output/highlight.mp4` highlighted video with bounding boxes
- `~/MotionDetection/output/events.csv` motion event summary (start/end frames and timestamps)
- `~/MotionDetection/output/live_events.csv` live feed motion event summary (start/end frames and timestamps)
- `~/MotionDetection/output/events/` reserved for per-event assets if you add them later

You can override the output folder by setting `MOTIONDETECTION_OUTPUT_DIR`.

## Build macOS .app

```bash
./scripts/build_macos_app.sh
```

The app bundle will be created at `dist/MotionDetection.app`.

The app includes a camera usage description in its Info.plist so macOS can show the permission prompt.

## Build Windows .exe

```bat
scripts\\build_windows_exe.bat
```

The executable will be created at `dist\\MotionDetection.exe`.

## Notes

- Live feed uses the default camera (index 0). Close other apps using the camera.
- On macOS, grant camera permission to the app running Python (VS Code/Terminal).
