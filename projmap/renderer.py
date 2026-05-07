import numpy as np
import moderngl
from PySide6.QtGui import QImage, QPixmap

from projmap.homography import compute_homography

STAGE_W = 1920
STAGE_H = 1080
SRC_W, SRC_H = 960, 540

_SOURCE_VERT = """
#version 330
in vec2 in_vert;
out vec2 uv;
void main() {
    uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

_WARP_VERT = """
#version 330
in vec2 in_vert;
out vec2 v_pos;
void main() {
    v_pos = in_vert;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

_WARP_FRAG = """
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

        verts = np.array([-1,-1, 1,-1, 1,1, -1,-1, 1,1, -1,1], dtype=np.float32)
        self._quad_vbo = self._ctx.buffer(verts.tobytes())

        self._warp_prog = self._ctx.program(
            vertex_shader=_WARP_VERT, fragment_shader=_WARP_FRAG
        )
        self._warp_vao = self._ctx.vertex_array(
            self._warp_prog, [(self._quad_vbo, '2f', 'in_vert')]
        )

        self._src_tex = self._ctx.texture((SRC_W, SRC_H), 3)
        self._src_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._src_fbo = self._ctx.framebuffer(color_attachments=[self._src_tex])

        self._out_fbo = self._ctx.simple_framebuffer((STAGE_W, STAGE_H))

        # frag_code -> (prog, vao)
        self._src_cache: dict = {}

    def _src_vao(self, frag_code):
        if frag_code not in self._src_cache:
            prog = self._ctx.program(
                vertex_shader=_SOURCE_VERT, fragment_shader=frag_code
            )
            vao = self._ctx.vertex_array(prog, [(self._quad_vbo, '2f', 'in_vert')])
            self._src_cache[frag_code] = (prog, vao)
        return self._src_cache[frag_code]

    def _source_texture(self, surface, time):
        source = surface.source
        if hasattr(source, 'frag_code'):
            prog, vao = self._src_vao(source.frag_code)
            self._src_fbo.use()
            self._ctx.clear(0, 0, 0)
            if 'time' in prog:
                prog['time'] = float(time)
            if 'resolution' in prog:
                prog['resolution'] = (SRC_W, SRC_H)
            vao.render()
            return self._src_tex
        else:
            source.update(self._ctx, time)
            return source.texture

    def _render_surface(self, surface, time):
        tex = self._source_texture(surface, time)
        if tex is None:
            return  # source not ready yet (first video frame)

        c = surface.quad.corners
        ndc = np.column_stack([
            c[:, 0] / STAGE_W * 2 - 1,
            -(c[:, 1] / STAGE_H * 2 - 1),
        ])
        H = compute_homography(_UV_CORNERS, ndc)
        inv_H = np.linalg.inv(H)
        inv_H /= inv_H[2, 2]

        self._out_fbo.use()
        tex.use(0)
        self._warp_prog['tex'] = 0
        self._warp_prog['inv_H'].write(inv_H.T.astype(np.float32).tobytes())
        self._warp_vao.render()

    def render(self, surfaces, time=0.0):
        self._out_fbo.use()
        self._ctx.clear(0, 0, 0)
        for surface in surfaces:
            self._render_surface(surface, time)
        raw = self._out_fbo.read(components=3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(STAGE_H, STAGE_W, 3)
        arr = arr[::-1].copy()
        img = QImage(arr.data, STAGE_W, STAGE_H, STAGE_W * 3, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(img)
