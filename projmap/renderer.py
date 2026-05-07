import numpy as np
import moderngl
from PySide6.QtGui import QImage, QPixmap

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
        discard;
    f_color = texture(tex, uv);
}
"""

_UV_CORNERS = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)


class Renderer:
    def __init__(self):
        self._ctx = moderngl.create_standalone_context()
        self._prog = self._ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)

        verts = np.array([-1,-1, 1,-1, 1,1, -1,-1, 1,1, -1,1], dtype=np.float32)
        vbo = self._ctx.buffer(verts.tobytes())
        self._vao = self._ctx.vertex_array(self._prog, [(vbo, '2f', 'in_vert')])
        self._fbo = self._ctx.simple_framebuffer((STAGE_W, STAGE_H))
        self._set_checkerboard()

    def _set_checkerboard(self):
        w, h = 640, 360
        xs, ys = np.arange(w), np.arange(h)
        grid = (xs[None, :] // 40 + ys[:, None] // 40) % 2
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        arr[grid == 0] = [200, 200, 200]
        arr[grid == 1] = [45, 45, 45]
        self._tex = self._ctx.texture((w, h), 3, arr.tobytes())
        self._tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

    def _render_surface(self, surface):
        c = surface.quad.corners
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

    def render(self, surfaces):
        self._fbo.use()
        self._ctx.clear(0.0, 0.0, 0.0)
        for surface in surfaces:
            self._render_surface(surface)
        raw = self._fbo.read(components=3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(STAGE_H, STAGE_W, 3)
        arr = arr[::-1].copy()
        img = QImage(arr.data, STAGE_W, STAGE_H, STAGE_W * 3, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(img)
