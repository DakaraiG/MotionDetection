from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import cv2

from config import AppConfig
from video_io import open_video, make_writer
from motion import detect_motion
from events import EventBuilder

@dataclass
class ProcessResult:
    highlight_path: Path
    events_csv_path: Path
    event_count: int

def annotate_frame(frame, boxes, text: str):
    for (x, y, w, h) in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

def process_video(input_path: Path, cfg: AppConfig, log_fn=None) -> ProcessResult:
    output_dir = cfg.output_dir
    events_dir = output_dir / cfg.events_dirname
    output_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)

    cap, meta = open_video(input_path)

    highlight_path = output_dir / cfg.highlight_name
    writer = make_writer(highlight_path, meta.fps, meta.width, meta.height)

    events_csv_path = output_dir / cfg.events_csv_name

    # Read first frame
    ok, prev = cap.read()
    if not ok:
        cap.release()
        writer.release()
        raise RuntimeError("Could not read first frame.")

    frame_idx = 0
    builder = EventBuilder(cfg.pre_roll_frames, cfg.post_roll_frames, cfg.min_event_frames)

    #log per-frame, then summarize events
    per_frame_motion = []

    if log_fn:
        log_fn(f"Video: {input_path.name} | {meta.width}x{meta.height} | fps={meta.fps:.2f} | frames={meta.frame_count}")

    while True:
        ok, curr = cap.read()
        if not ok:
            break

        frame_idx += 1

        res = detect_motion(
            prev_bgr=prev,
            curr_bgr=curr,
            diff_threshold=cfg.diff_threshold,
            min_contour_area=cfg.min_contour_area,
            blur_kernel=cfg.blur_kernel,
            erode_iters=cfg.erode_iters,
            dilate_iters=cfg.dilate_iters,
        )

        timestamp_s = frame_idx / meta.fps
        text = f"{timestamp_s:0.2f}s | Motion: {'YES' if res.motion else 'no'} | score={res.score:.4f}"

        frame_out = curr.copy()
        if res.motion:
            annotate_frame(frame_out, res.boxes, text)
        else:
            cv2.putText(frame_out, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        writer.write(frame_out)

        builder.update(frame_idx, res.motion, res.boxes)
        per_frame_motion.append((frame_idx, timestamp_s, res.motion, res.score))

        prev = curr

    # Finalize any open event
    builder.finalize(frame_idx)

    cap.release()
    writer.release()

    # Write CSV
    with open(events_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "start_frame", "end_frame", "start_s", "end_s", "duration_s", "bbox_x", "bbox_y", "bbox_w", "bbox_h"])
        for ev in builder.events:
            start_s = ev.start_idx / meta.fps
            end_s = ev.end_idx / meta.fps
            dur = end_s - start_s
            if ev.bbox:
                x, y, bw, bh = ev.bbox
            else:
                x = y = bw = bh = ""
            w.writerow([ev.id, ev.start_idx, ev.end_idx, f"{start_s:.3f}", f"{end_s:.3f}", f"{dur:.3f}", x, y, bw, bh])

    if log_fn:
        log_fn(f"Saved highlight: {highlight_path}")
        log_fn(f"Saved events CSV: {events_csv_path}")
        log_fn(f"Detected events: {len(builder.events)}")

    return ProcessResult(highlight_path=highlight_path, events_csv_path=events_csv_path, event_count=len(builder.events))
