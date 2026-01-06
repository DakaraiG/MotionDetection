from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import cv2

from config import AppConfig
from video_io import openVideo, makeWriter
from motion import detectMotion
from events import EventBuilder

@dataclass
class ProcessResult:
    highlightPath: Path
    eventsCsvPath: Path
    eventCount: int

def annotateFrame(frame, boxes, text: str):
    for (x, y, w, h) in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

def processVideo(inputPath: Path, cfg: AppConfig, logFn=None) -> ProcessResult:
    outputDir = cfg.output_dir
    eventsDir = outputDir / cfg.events_dirname
    outputDir.mkdir(parents=True, exist_ok=True)
    eventsDir.mkdir(parents=True, exist_ok=True)

    cap, meta = openVideo(inputPath)

    highlightPath = outputDir / cfg.highlight_name
    writer = makeWriter(highlightPath, meta.fps, meta.width, meta.height)

    eventsCsvPath = outputDir / cfg.events_csv_name

    # Read first frame
    ok, prev = cap.read()
    if not ok:
        cap.release()
        writer.release()
        raise RuntimeError("Could not read first frame.")

    frameIdx = 0
    builder = EventBuilder(cfg.pre_roll_frames, cfg.post_roll_frames, cfg.min_event_frames)

    #log per-frame, then summarize events
    perFrameMotion = []

    if logFn:
        logFn(f"Video: {inputPath.name} | {meta.width}x{meta.height} | fps={meta.fps:.2f} | frames={meta.frameCount}")

    while True:
        ok, curr = cap.read()
        if not ok:
            break

        frameIdx += 1

        res = detectMotion(
            prevBgr=prev,
            currBgr=curr,
            diffThreshold=cfg.diff_threshold,
            minContourArea=cfg.min_contour_area,
            blurKernel=cfg.blur_kernel,
            erodeIters=cfg.erode_iters,
            dilateIters=cfg.dilate_iters,
        )

        timestampS = frameIdx / meta.fps
        text = f"{timestampS:0.2f}s | Motion: {'YES' if res.motion else 'no'} | score={res.score:.4f}"

        frameOut = curr.copy()
        if res.motion:
            annotateFrame(frameOut, res.boxes, text)
        else:
            cv2.putText(frameOut, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        writer.write(frameOut)

        builder.update(frameIdx, res.motion, res.boxes)
        perFrameMotion.append((frameIdx, timestampS, res.motion, res.score))

        prev = curr

    # Finalize any open event
    builder.finalize(frameIdx)

    cap.release()
    writer.release()

    # Write CSV
    with open(eventsCsvPath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "start_frame", "end_frame", "start_s", "end_s", "duration_s", "bbox_x", "bbox_y", "bbox_w", "bbox_h"])
        for ev in builder.events:
            startS = ev.startIdx / meta.fps
            endS = ev.endIdx / meta.fps
            dur = endS - startS
            if ev.bbox:
                x, y, bw, bh = ev.bbox
            else:
                x = y = bw = bh = ""
            w.writerow([ev.id, ev.startIdx, ev.endIdx, f"{startS:.3f}", f"{endS:.3f}", f"{dur:.3f}", x, y, bw, bh])

    if logFn:
        logFn(f"Saved highlight: {highlightPath}")
        logFn(f"Saved events CSV: {eventsCsvPath}")
        logFn(f"Detected events: {len(builder.events)}")

    return ProcessResult(highlightPath=highlightPath, eventsCsvPath=eventsCsvPath, eventCount=len(builder.events))
