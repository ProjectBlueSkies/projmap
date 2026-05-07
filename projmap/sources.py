from pathlib import Path

import moderngl
import numpy as np
from PIL import Image


class ImageSource:
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self._tex = None

    def update(self, ctx, time):
        if self._tex is not None:
            return
        img = Image.open(self.path).convert('RGB')
        arr = np.asarray(img)
        self._tex = ctx.texture((img.width, img.height), 3, arr.tobytes())
        self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

    @property
    def texture(self):
        return self._tex


class VideoSource:
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self._cap = None
        self._tex = None
        self._frame_duration = 1 / 30.0
        self._next_frame_time = 0.0

    def _open(self):
        import cv2
        self._cap = cv2.VideoCapture(str(self.path))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self._frame_duration = 1.0 / fps

    def update(self, ctx, time):
        import cv2
        if self._cap is None:
            self._open()
        if time < self._next_frame_time:
            return
        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]
            if self._tex is None:
                self._tex = ctx.texture((w, h), 3)
                self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._tex.write(frame.tobytes())
        self._next_frame_time += self._frame_duration

    @property
    def texture(self):
        return self._tex
