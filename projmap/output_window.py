import numpy as np
import moderngl
from PySide6.QtCore import QTimer, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QMainWindow

from projmap.homography import compute_homography

STAGE_W = 1920
STAGE_H = 1080

_VERT = """
#version 330
in vec2 in_vert;
out vec2 v_pos;
void main() {
    v_pos = in_vert;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

_FRAG = """
#version 330
uniform mat3 inv_H;
uniform sampler2D tex;
in vec2 v_pos;
out vec4 f_color;
void main() {
    vec3 h = inv_H * vec3(v_pos, 1.0);
    vec2 uv = h.xy / h.z;
    uv.y = 1.0 - uv.y;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0))))
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
    else
        f_color = texture(tex, uv);
}
"""

_UV_CORNERS = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)
_FULLSCREEN_VERTS = np.array(
    [-1, -1,  1, -1,  1, 1,  -1, -1,  1, 1,  -1, 1], dtype=np.float32
)


class OutputWidget(QOpenGLWidget):
    def __init__(self, quad, parent=None):
        super().__init__(parent)
        self.quad = quad
        self._ctx = None

    def initializeGL(self):
        self._ctx = moderngl.create_context()
        self._prog = self._ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)

        vbo = self._ctx.buffer(_FULLSCREEN_VERTS.tobytes())
        self._vao = self._ctx.vertex_array(self._prog, [(vbo, '2f', 'in_vert')])

        w, h = 640, 360
        xs, ys = np.arange(w), np.arange(h)
        grid = (xs[None, :] // 40 + ys[:, None] // 40) % 2
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        arr[grid == 0] = [200, 200, 200]
        arr[grid == 1] = [45, 45, 45]
        self._tex = self._ctx.texture((w, h), 3, arr.tobytes())
        self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

    def paintGL(self):
        self._ctx.clear(0.0, 0.0, 0.0)

        c = self.quad.corners
        ndc = np.column_stack([
            c[:, 0] / STAGE_W * 2 - 1,
            -(c[:, 1] / STAGE_H * 2 - 1),
        ])
        H = compute_homography(_UV_CORNERS, ndc)
        inv_H = np.linalg.inv(H)
        inv_H /= inv_H[2, 2]

        self._tex.use(0)
        self._prog['tex'] = 0
        self._prog['inv_H'].write(inv_H.T.astype(np.float32).tobytes())
        self._vao.render()


class OutputWindow(QMainWindow):
    def __init__(self, quad, parent=None):
        super().__init__(parent)
        self.setWindowTitle("projmap — output")
        self.resize(960, 540)
        self.widget = OutputWidget(quad, self)
        self.setCentralWidget(self.widget)
        self._pending_screen = None

    def send_to_screen(self, screen):
        self._pending_screen = screen
        if self.isFullScreen():
            self.showNormal()
            # Wayland is async — let the compositor process showNormal before
            # we request fullscreen on a different output
            QTimer.singleShot(150, self._apply_screen)
        else:
            self._apply_screen()

    def _apply_screen(self):
        screen = self._pending_screen
        if screen is None:
            return
        handle = self.windowHandle()
        if handle:
            handle.setScreen(screen)
        self.raise_()
        self.activateWindow()
        self.showFullScreen()

    def go_windowed(self):
        self._pending_screen = None
        self.showNormal()
        self.resize(960, 540)
        self.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_windowed()
        super().keyPressEvent(event)
