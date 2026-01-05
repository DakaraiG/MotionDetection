from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List

@dataclass
class Event:
    id: int
    start_idx: int
    end_idx: int
    # aggregate bounding box for the event (optional)
    bbox: Optional[Tuple[int, int, int, int]] = None

def _merge_bbox(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = min(ax, bx)
    y1 = min(ay, by)
    x2 = max(ax + aw, bx + bw)
    y2 = max(ay + ah, by + bh)
    return (x1, y1, x2 - x1, y2 - y1)

class EventBuilder:

    # Builds motion events from per-frame motion detections.

    def __init__(self, pre_roll: int, post_roll: int, min_event_frames: int):
        self.pre_roll = pre_roll
        self.post_roll = post_roll
        self.min_event_frames = min_event_frames

        self._active = False
        self._start_idx = 0
        self._last_motion_idx = -1
        self._bbox = None
        self._events: List[Event] = []
        self._next_id = 1

    def update(self, frame_idx: int, motion: bool, boxes):
        if motion:
            if not self._active:
                self._active = True
                self._start_idx = max(0, frame_idx - self.pre_roll)
                self._bbox = None

            self._last_motion_idx = frame_idx

            # merge boxes into an event bbox (coarse but useful)
            for b in boxes:
                self._bbox = b if self._bbox is None else _merge_bbox(self._bbox, b)

        if self._active and (not motion):
            # close if gone past post-roll frames
            if self._last_motion_idx >= 0 and frame_idx > self._last_motion_idx + self.post_roll:
                end_idx = self._last_motion_idx + self.post_roll
                if (end_idx - self._start_idx + 1) >= self.min_event_frames:
                    self._events.append(Event(
                        id=self._next_id,
                        start_idx=self._start_idx,
                        end_idx=end_idx,
                        bbox=self._bbox
                    ))
                    self._next_id += 1
                self._active = False
                self._bbox = None
                self._last_motion_idx = -1

    def finalize(self, last_frame_idx: int):
        if self._active:
            end_idx = min(last_frame_idx, (self._last_motion_idx + self.post_roll) if self._last_motion_idx >= 0 else last_frame_idx)
            if (end_idx - self._start_idx + 1) >= self.min_event_frames:
                self._events.append(Event(
                    id=self._next_id,
                    start_idx=self._start_idx,
                    end_idx=end_idx,
                    bbox=self._bbox
                ))
            self._active = False

    @property
    def events(self) -> List[Event]:
        return self._events
