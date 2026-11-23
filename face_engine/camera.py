import threading
import time

import cv2


class VideoStream:
    """Threaded reader that always exposes the newest frame and reconnects on failure."""

    def __init__(self, source):
        self.source = source
        self._frame = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._cap = None

    def _open(self):
        self._cap = cv2.VideoCapture(self.source)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def start(self):
        self._open()
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while not self._stop.is_set():
            if self._cap is None or not self._cap.isOpened():
                time.sleep(2)
                self._open()
                continue
            ok, frame = self._cap.read()
            if not ok:
                self._cap.release()
                time.sleep(1)
                continue
            with self._lock:
                self._frame = frame

    def read(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self):
        self._stop.set()
        if self._cap:
            self._cap.release()
