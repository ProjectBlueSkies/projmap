import os
import subprocess
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

_TEXT_W, _TEXT_H = 960, 540


def _load_font(size):
    from PIL import ImageFont
    try:
        path = subprocess.check_output(
            ['fc-match', '--format=%{file}', 'sans-serif:bold'],
            timeout=2, text=True,
        ).strip()
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


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


class TextSource:
    def __init__(self, name="Text", text="Hello", font_size=120,
                 color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255), align='center'):
        self.name = name
        self.text = text
        self.font_size = font_size
        self.color = _rgba4(color)
        self.bg_color = _rgba4(bg_color)
        self.align = align
        self._tex = None
        self._dirty = True

    def mark_dirty(self):
        self._dirty = True

    def update(self, ctx, time):
        if not self._dirty and self._tex is not None:
            return
        from PIL import ImageDraw
        img = Image.new('RGBA', (_TEXT_W, _TEXT_H), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = _load_font(self.font_size)
        text = self.text or ""
        bbox = draw.multiline_textbbox((0, 0), text, font=font, align=self.align)
        x = (_TEXT_W - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (_TEXT_H - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.multiline_text((x, y), text, fill=self.color, font=font, align=self.align)
        data = img.tobytes()
        if self._tex is None:
            self._tex = ctx.texture((_TEXT_W, _TEXT_H), 4, data)
            self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        else:
            self._tex.write(data)
        self._dirty = False

    @property
    def texture(self):
        return self._tex


def _rgba4(c):
    """Ensure color is a 4-tuple RGBA."""
    c = tuple(c)
    return c if len(c) == 4 else (*c, 255)
