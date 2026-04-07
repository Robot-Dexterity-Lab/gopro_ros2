"""Threaded MJPEG video capture for GoPro via USB capture card."""

import os
import sys
import time
import pathlib
import threading
from typing import Optional, Tuple

import cv2
import numpy as np


def configure_display(default_display: str = ":0") -> None:
    """Configure X11 display environment for GUI support."""
    display_arg = None
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--display="):
            display_arg = arg.split("=", 1)[1]
        elif arg == "--display" and i + 1 < len(sys.argv):
            display_arg = sys.argv[i + 1]

    if display_arg:
        os.environ["DISPLAY"] = display_arg
    elif not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = default_display

    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


class FastVideoCapture:
    """Threaded V4L2 capture using MJPEG for high framerate."""

    def __init__(self, src: str, width: int = 1920, height: int = 1080, fps: int = 60):
        self.src = src
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)

        # Force MJPEG codec for high framerate
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        self.grabbed, self.frame = self.cap.read()
        if not self.grabbed:
            raise RuntimeError(f"FastVideoCapture: unable to read from {src}")

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(
            f"[Camera] Requested {width}x{height}@{fps}fps -> "
            f"Actual {actual_w}x{actual_h}@{actual_fps:.1f}fps"
        )

        self._started = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "FastVideoCapture":
        if self._started:
            return self
        self._started = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self) -> None:
        while self._started:
            grabbed, frame = self.cap.read()
            with self._lock:
                self.grabbed = grabbed
                self.frame = frame
            time.sleep(0.0005)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self.frame is not None:
                return self.grabbed, self.frame.copy()
            return self.grabbed, None

    def stop(self) -> None:
        self._started = False
        if self._thread:
            self._thread.join()
        self.cap.release()


def get_v4l_devices(by_id: bool = True) -> list:
    """Find valid V4L2 device paths (index0 only)."""
    dirname = "by-id" if by_id else "by-path"
    v4l_dir = pathlib.Path("/dev/v4l") / dirname
    if not v4l_dir.exists():
        return []
    return [
        str(p.absolute())
        for p in sorted(v4l_dir.glob("*video*"))
        if "index0" in p.name
    ]
