from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QLabel, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget

from projmap.renderer import _SOURCE_VERT
from projmap.syntax import GlslHighlighter

_TEMPLATE = """\
#version 330
uniform float time;
uniform vec2 resolution;
in vec2 uv;
out vec4 f_color;

void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;

    float r = length(p);
    float a = atan(p.y, p.x);
    float pattern = sin(r * 8.0 - time * 2.0 + a * 3.0);
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + pattern + time * 0.3);
    col *= smoothstep(1.2, 0.8, r);

    f_color = vec4(col, 1.0);
}
"""


class ShaderEditorWindow(QMainWindow):
    def __init__(self, source, renderer, parent=None):
        super().__init__(parent)
        self._source = source
        self._renderer = renderer
        self.setWindowTitle(f"Shader Editor — {source.name}")
        self.resize(720, 620)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(11)

        self._editor = QPlainTextEdit()
        self._editor.setFont(font)
        self._editor.setPlainText(source.frag_code)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._apply_dark_palette()
        GlslHighlighter(self._editor.document())
        layout.addWidget(self._editor)

        self._status = QLabel("  Ready")
        self._status.setFixedHeight(24)
        self._status.setStyleSheet(
            "background:#1e1e1e; color:#4CAF50; font-family:monospace; padding-left:6px;"
        )
        layout.addWidget(self._status)

        self._debounce = QTimer(singleShot=True, interval=500)
        self._debounce.timeout.connect(self._compile)
        self._editor.textChanged.connect(self._debounce.start)

        shortcut_apply = self._editor.keyPressEvent

        self.statusBar().hide()

    def _apply_dark_palette(self):
        p = self._editor.palette()
        p.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        p.setColor(QPalette.ColorRole.Text, QColor("#eeffff"))
        self._editor.setPalette(p)

    def _compile(self):
        code = self._editor.toPlainText()
        ctx = self._renderer._ctx
        try:
            prog = ctx.program(vertex_shader=_SOURCE_VERT, fragment_shader=code)
            prog.release()
            self._source.frag_code = code
            self._renderer.invalidate_source(self._source)
            self._status.setText("  ● Compiled OK")
            self._status.setStyleSheet(
                "background:#1e1e1e; color:#4CAF50; font-family:monospace; padding-left:6px;"
            )
        except Exception as exc:
            msg = str(exc).split('\n')[0][:120]
            self._status.setText(f"  ✗ {msg}")
            self._status.setStyleSheet(
                "background:#1e1e1e; color:#F44336; font-family:monospace; padding-left:6px;"
            )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._debounce.stop()
            self._compile()
        else:
            super().keyPressEvent(event)

    @staticmethod
    def template():
        return _TEMPLATE
