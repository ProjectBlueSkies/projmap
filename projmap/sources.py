import json
import os
import struct
import subprocess
import threading
import time as _time
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
        arr = np.asarray(img)[::-1].copy()  # flip Y for OpenGL convention
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
            frame = frame[::-1]  # flip Y for OpenGL convention
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
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # flip Y for OpenGL convention
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


def list_windows():
    """Enumerate open X11 windows as [{xid, wm_class, title}, ...].

    Uses `wmctrl -lx`. Returns [] on Wayland / if wmctrl is unavailable.
    """
    try:
        out = subprocess.check_output(['wmctrl', '-lx'], text=True, timeout=3)
    except Exception:
        return []
    wins = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 5:
            xid, _desk, wm_class, _host, title = parts
        elif len(parts) == 4:
            xid, _desk, wm_class, _host = parts
            title = ''
        else:
            continue
        # Skip projmap's own windows to avoid capture feedback loops.
        if 'projmap' in wm_class.lower() or 'projmap' in title.lower():
            continue
        wins.append({'xid': xid, 'wm_class': wm_class, 'title': title})
    return wins


def _read_exactly(stream, n):
    """Read exactly n bytes from a (possibly chunking) pipe; None on EOF."""
    chunks = []
    got = 0
    while got < n:
        c = stream.read(n - got)
        if not c:
            return None
        chunks.append(c)
        got += len(c)
    return b''.join(chunks)


def list_monitors():
    """Enumerate real monitors via the screencast helper.

    Returns [{connector, primary, x, y, scale, width, height}, ...], or [] if
    unavailable (e.g. not a GNOME/Mutter Wayland session).
    """
    helper = os.path.join(os.path.dirname(__file__), '_screencast_helper.py')
    try:
        out = subprocess.check_output(
            ['/usr/bin/python3', helper, 'list'],
            text=True, timeout=5, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception:
        return []


class DesktopSource:
    """Live capture of a Wayland desktop via Mutter ScreenCast.

    Spawns `_screencast_helper.py` under the system python (which has PyGObject):
    the helper streams the capture as raw RGB to its stdout via PipeWire+GStreamer,
    and a reader thread pulls frames so the render loop never blocks. Two modes:

    - ``'virtual'`` (RecordVirtual): a NEW, blank virtual monitor — separate from
      the projector output, so it never feeds back, but it starts empty (you'd
      drag windows onto it). Use on single-display setups.
    - ``'monitor'`` (RecordMonitor): mirrors a REAL output (``connector``) — shows
      your actual screen. Use when projmap outputs to a *different* display (e.g.
      the projector) so there's no feedback loop.

    Wayland session only.
    """

    def __init__(self, width=1280, height=720, fps=15, mode='virtual', connector=None):
        self.mode = mode
        self.connector = connector
        if mode == 'monitor':
            self.name = '🖥 Screen' + (f': {connector}' if connector else '')
        else:
            self.name = '🖵 Virtual Desktop'
        self.cap_w = int(width)
        self.cap_h = int(height)
        self.fps = int(fps)
        self._proc = None
        self._tex = None
        self._latest = None
        self._new = False
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def _open(self):
        helper = os.path.join(os.path.dirname(__file__), '_screencast_helper.py')
        if self.mode == 'monitor':
            args = ['/usr/bin/python3', helper, 'monitor',
                    str(self.cap_w), str(self.cap_h), str(self.fps),
                    self.connector or '']
        else:
            args = ['/usr/bin/python3', helper, 'virtual',
                    str(self.cap_w), str(self.cap_h), str(self.fps)]
        self._proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        n = self.cap_w * self.cap_h * 3
        stream = self._proc.stdout
        while self._running:
            buf = _read_exactly(stream, n)
            if buf is None:
                break
            with self._lock:
                self._latest = buf
                self._new = True

    def update(self, ctx, time):
        if self._proc is None:
            self._open()
        with self._lock:
            if not self._new:
                return
            buf = self._latest
            self._new = False
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(self.cap_h, self.cap_w, 3)
        arr = arr[::-1].copy()  # flip Y for OpenGL convention
        if self._tex is None:
            self._tex = ctx.texture((self.cap_w, self.cap_h), 3)
            self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._tex.write(arr.tobytes())

    @property
    def texture(self):
        return self._tex

    def close(self):
        self._running = False
        if self._proc is not None:
            self._proc.terminate()


def _parse_xwd(data):
    """Parse `xwd` output (XWD file format) into (width, height, rgb_bytes).

    rgb_bytes is row-major RGB already flipped vertically for OpenGL.
    Returns None if the data is incomplete/unsupported.
    """
    if len(data) < 100:
        return None
    hdr = struct.unpack('>25I', data[:100])
    header_size, _ver, _fmt, _depth, pw, ph, _xoff, byte_order = hdr[0:8]
    bits_per_pixel = hdr[11]
    bytes_per_line = hdr[12]
    red_mask, green_mask, blue_mask = hdr[14], hdr[15], hdr[16]
    ncolors = hdr[19]
    bpp = bits_per_pixel // 8
    if bpp < 3 or pw == 0 or ph == 0:
        return None
    pix_start = header_size + ncolors * 12
    need = bytes_per_line * ph
    pix = data[pix_start:pix_start + need]
    if len(pix) < need:
        return None
    arr = np.frombuffer(pix, dtype=np.uint8).reshape(ph, bytes_per_line)
    arr = arr[:, :pw * bpp].reshape(ph, pw, bpp)

    def bidx(mask):
        shift = (mask & -mask).bit_length() - 1
        b = shift // 8
        return (bpp - 1 - b) if byte_order == 1 else b

    ri, gi, bi = bidx(red_mask), bidx(green_mask), bidx(blue_mask)
    rgb = np.dstack([arr[..., ri], arr[..., gi], arr[..., bi]])
    rgb = rgb[::-1].copy()  # flip Y for OpenGL convention
    return pw, ph, rgb.tobytes()


class WindowSource:
    """Live capture of a specific X11 window via `xwd` (XGetImage).

    Uses plain XGetImage (not MIT-SHM), so it captures the window's true content
    even when occluded under a compositor (e.g. behind projmap's own fullscreen
    output) — no feedback loop. A background thread grabs frames so the render
    loop never blocks; the texture is resized automatically if the window does.
    """

    def __init__(self, xid, title, wm_class='', fps=12):
        self.xid = xid
        self.title = title
        self.wm_class = wm_class
        self.name = ('⊞ ' + (title or wm_class or xid))[:40]
        self.fps = int(fps)
        self._tex = None
        self._tex_size = None
        self._latest = None       # (w, h, rgb_bytes)
        self._new = False
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def _start(self):
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _grab(self):
        try:
            data = subprocess.check_output(
                ['xwd', '-id', self.xid, '-silent'],
                stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            return None
        return _parse_xwd(data)

    def _reader(self):
        interval = 1.0 / max(1, self.fps)
        while self._running:
            t0 = _time.monotonic()
            frame = self._grab()
            if frame is not None:
                with self._lock:
                    self._latest = frame
                    self._new = True
            dt = _time.monotonic() - t0
            if dt < interval:
                _time.sleep(interval - dt)

    def update(self, ctx, time):
        if self._thread is None:
            self._start()
        with self._lock:
            if not self._new:
                return
            w, h, rgb = self._latest
            self._new = False
        if self._tex is None or self._tex_size != (w, h):
            if self._tex is not None:
                self._tex.release()
            self._tex = ctx.texture((w, h), 3)
            self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._tex_size = (w, h)
        self._tex.write(rgb)

    @property
    def texture(self):
        return self._tex

    def close(self):
        self._running = False
