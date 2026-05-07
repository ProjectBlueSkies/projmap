import re

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

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

_SYSTEM_PROMPT = """\
You are a GLSL fragment shader generator for a projection mapping tool.

Write a fragment shader that matches the user's description. Follow these rules exactly:
- GLSL version: #version 330
- Available uniforms: uniform float time;  uniform vec2 resolution;
- Input varying: in vec2 uv;  (0.0–1.0 range, origin at bottom-left)
- Output: out vec4 f_color;
- Do NOT declare any other uniforms or inputs
- Animate using the time uniform where appropriate
- Output ONLY the raw GLSL code — no markdown, no code fences, no explanation
"""


def _strip_fences(text):
    text = text.strip()
    m = re.match(r'^```\w*\n(.*?)(?:\n```)?$', text, re.DOTALL)
    return m.group(1).strip() if m else text


class _GenerateWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, prompt):
        super().__init__()
        self._prompt = prompt

    def run(self):
        try:
            import os
            from pathlib import Path
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                config = Path.home() / ".config" / "projmap" / "config"
                if config.exists():
                    for line in config.read_text().splitlines():
                        if line.startswith("ANTHROPIC_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
            if not api_key:
                self.error.emit(
                    "ANTHROPIC_API_KEY not set — add it to ~/.config/projmap/config"
                )
                return
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": self._prompt}],
            )
            self.done.emit(_strip_fences(msg.content[0].text))
        except Exception as exc:
            self.error.emit(str(exc))


class ShaderEditorWindow(QMainWindow):
    def __init__(self, source, renderer, parent=None):
        super().__init__(parent)
        self._source = source
        self._renderer = renderer
        self._worker = None
        self.setWindowTitle(f"Shader Editor — {source.name}")
        self.resize(720, 680)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        # AI prompt row
        prompt_row = QWidget()
        prompt_row.setStyleSheet("background:#252526;")
        row_layout = QHBoxLayout(prompt_row)
        row_layout.setContentsMargins(6, 6, 6, 6)
        row_layout.setSpacing(6)

        self._prompt_input = QLineEdit()
        self._prompt_input.setPlaceholderText("Describe the effect you want…")
        self._prompt_input.setStyleSheet(
            "background:#1e1e1e; color:#eeffff; border:1px solid #3c3c3c;"
            " padding:4px 6px; font-family:sans-serif; font-size:12px;"
        )
        self._prompt_input.returnPressed.connect(self._generate)
        row_layout.addWidget(self._prompt_input)

        self._gen_btn = QPushButton("Generate")
        self._gen_btn.setFixedWidth(80)
        self._gen_btn.setStyleSheet(
            "background:#0e639c; color:#fff; border:none; padding:4px 8px;"
            " font-size:12px;"
        )
        self._gen_btn.clicked.connect(self._generate)
        row_layout.addWidget(self._gen_btn)
        layout.addWidget(prompt_row)

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

        self.statusBar().hide()

    def _apply_dark_palette(self):
        p = self._editor.palette()
        p.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        p.setColor(QPalette.ColorRole.Text, QColor("#eeffff"))
        self._editor.setPalette(p)

    def _generate(self):
        prompt = self._prompt_input.text().strip()
        if not prompt:
            return
        self._gen_btn.setEnabled(False)
        self._gen_btn.setText("…")
        self._set_status("  ⟳ Generating…", "#9E9E9E")

        self._worker = _GenerateWorker(prompt)
        self._worker.done.connect(self._on_generated)
        self._worker.error.connect(self._on_generate_error)
        self._worker.start()

    def _on_generated(self, code):
        self._editor.setPlainText(code)
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("Generate")
        self._debounce.stop()
        self._compile()

    def _on_generate_error(self, msg):
        short = msg.split('\n')[0][:120]
        self._set_status(f"  ✗ {short}", "#F44336")
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("Generate")

    def _compile(self):
        code = self._editor.toPlainText()
        ctx = self._renderer._ctx
        try:
            prog = ctx.program(vertex_shader=_SOURCE_VERT, fragment_shader=code)
            prog.release()
            self._source.frag_code = code
            self._renderer.invalidate_source(self._source)
            self._set_status("  ● Compiled OK", "#4CAF50")
        except Exception as exc:
            msg = str(exc).split('\n')[0][:120]
            self._set_status(f"  ✗ {msg}", "#F44336")

    def _set_status(self, text, color):
        self._status.setText(text)
        self._status.setStyleSheet(
            f"background:#1e1e1e; color:{color}; font-family:monospace; padding-left:6px;"
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
