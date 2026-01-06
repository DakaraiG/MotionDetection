from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List

@dataclass
class Event:
    id: int
    startIdx: int
    endIdx: int
    # aggregate bounding box for the event (optional)
    bbox: Optional[Tuple[int, int, int, int]] = None

def _mergeBbox(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = min(ax, bx)
    y1 = min(ay, by)
    x2 = max(ax + aw, bx + bw)
    y2 = max(ay + ah, by + bh)
    return (x1, y1, x2 - x1, y2 - y1)

class EventBuilder:

    # Builds motion events from per-frame motion detections.

    def __init__(self, preRoll: int, postRoll: int, minEventFrames: int):
        self.preRoll = preRoll
        self.postRoll = postRoll
        self.minEventFrames = minEventFrames

        self._active = False
        self._startIdx = 0
        self._lastMotionIdx = -1
        self._bbox = None
        self._events: List[Event] = []
        self._nextId = 1

    def update(self, frameIdx: int, motion: bool, boxes):
        if motion:
            if not self._active:
                self._active = True
                self._startIdx = max(0, frameIdx - self.preRoll)
                self._bbox = None

            self._lastMotionIdx = frameIdx

            # merge boxes into an event bbox (coarse but useful)
            for b in boxes:
                self._bbox = b if self._bbox is None else _mergeBbox(self._bbox, b)

        if self._active and (not motion):
            # close if gone past post-roll frames
            if self._lastMotionIdx >= 0 and frameIdx > self._lastMotionIdx + self.postRoll:
                endIdx = self._lastMotionIdx + self.postRoll
                if (endIdx - self._startIdx + 1) >= self.minEventFrames:
                    self._events.append(Event(
                        id=self._nextId,
                        startIdx=self._startIdx,
                        endIdx=endIdx,
                        bbox=self._bbox
                    ))
                    self._nextId += 1
                self._active = False
                self._bbox = None
                self._lastMotionIdx = -1

    def finalize(self, lastFrameIdx: int):
        if self._active:
            endIdx = min(lastFrameIdx, (self._lastMotionIdx + self.postRoll) if self._lastMotionIdx >= 0 else lastFrameIdx)
            if (endIdx - self._startIdx + 1) >= self.minEventFrames:
                self._events.append(Event(
                    id=self._nextId,
                    startIdx=self._startIdx,
                    endIdx=endIdx,
                    bbox=self._bbox
                ))
            self._active = False

    @property
    def events(self) -> List[Event]:
        return self._events
