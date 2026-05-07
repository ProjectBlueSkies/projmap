from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup, QColorDialog, QHBoxLayout, QLabel,
    QMainWindow, QPlainTextEdit, QPushButton, QRadioButton,
    QSpinBox, QVBoxLayout, QWidget,
)

_SWATCH = (
    "border:1px solid #555; border-radius:3px;"
)
_NONE_ON  = "background:#3a3a3a; color:#F44336; border:1px solid #555; border-radius:3px; font-weight:bold;"
_NONE_OFF = "background:#2a2a2a; color:#888; border:1px solid #555; border-radius:3px;"


class TextEditorWindow(QMainWindow):
    def __init__(self, source, parent=None):
        super().__init__(parent)
        self._source = source
        self.setWindowTitle(f"Text — {source.name}")
        self.resize(600, 480)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        self._editor = QPlainTextEdit()
        self._editor.setPlainText(source.text)
        self._editor.setStyleSheet(
            "background:#1e1e1e; color:#eeffff; font-size:22px;"
            " font-family:sans-serif; border:none; padding:12px;"
        )
        layout.addWidget(self._editor)

        # ── controls bar ──────────────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet("background:#252526;")
        bar.setFixedHeight(48)
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(8)

        # Size
        row.addWidget(self._lbl("Size"))
        self._size_box = QSpinBox()
        self._size_box.setRange(8, 500)
        self._size_box.setValue(source.font_size)
        self._size_box.setFixedWidth(68)
        self._size_box.setStyleSheet(
            "background:#1e1e1e; color:#eeffff; border:1px solid #3c3c3c; padding:2px 4px;"
        )
        row.addWidget(self._size_box)

        row.addSpacing(6)

        # Text colour
        row.addWidget(self._lbl("Text"))
        r, g, b, a = source.color
        self._color_btn, self._color_none = self._color_pair(QColor(r, g, b), a == 0)
        row.addWidget(self._color_btn)
        row.addWidget(self._color_none)

        row.addSpacing(6)

        # Background colour
        row.addWidget(self._lbl("BG"))
        r, g, b, a = source.bg_color
        self._bg_btn, self._bg_none = self._color_pair(QColor(r, g, b), a == 0)
        row.addWidget(self._bg_btn)
        row.addWidget(self._bg_none)

        row.addSpacing(6)

        # Alignment
        row.addWidget(self._lbl("Align"))
        self._align_group = QButtonGroup(self)
        for i, (lbl, val) in enumerate([("L", "left"), ("C", "center"), ("R", "right")]):
            rb = QRadioButton(lbl)
            rb.setStyleSheet("color:#ccc; font-size:12px;")
            rb.setProperty("align_val", val)
            if val == source.align:
                rb.setChecked(True)
            self._align_group.addButton(rb, i)
            row.addWidget(rb)

        row.addStretch()
        layout.addWidget(bar)

        # debounce
        self._debounce = QTimer(singleShot=True, interval=300)
        self._debounce.timeout.connect(self._apply)
        self._editor.textChanged.connect(self._debounce.start)
        self._size_box.valueChanged.connect(self._debounce.start)
        self._align_group.buttonToggled.connect(lambda *_: self._debounce.start())

        self.statusBar().hide()

    # ── helpers ────────────────────────────────────────────────────────────

    def _lbl(self, text):
        w = QLabel(text)
        w.setStyleSheet("color:#9E9E9E; font-size:11px;")
        return w

    def _color_pair(self, color: QColor, is_none: bool):
        """Return (color_swatch_btn, none_toggle_btn)."""
        swatch = QPushButton()
        swatch.setFixedSize(28, 28)
        swatch.setEnabled(not is_none)
        self._paint_swatch(swatch, color)
        swatch.clicked.connect(lambda: self._pick_color(swatch, none_btn))

        none_btn = QPushButton("None")
        none_btn.setCheckable(True)
        none_btn.setChecked(is_none)
        none_btn.setFixedSize(42, 28)
        self._paint_none_btn(none_btn)
        none_btn.toggled.connect(lambda checked, s=swatch, n=none_btn: self._on_none_toggled(s, n, checked))

        return swatch, none_btn

    def _paint_swatch(self, btn, color: QColor):
        btn.setStyleSheet(f"background:{color.name()}; {_SWATCH}")
        btn.setProperty("qcolor", color)

    def _paint_none_btn(self, btn):
        btn.setStyleSheet(_NONE_ON if btn.isChecked() else _NONE_OFF)

    def _on_none_toggled(self, swatch, none_btn, checked):
        swatch.setEnabled(not checked)
        self._paint_none_btn(none_btn)
        self._debounce.start()

    def _pick_color(self, swatch, none_btn):
        current = swatch.property("qcolor") or QColor("white")
        chosen = QColorDialog.getColor(current, self, "Pick colour")
        if chosen.isValid():
            self._paint_swatch(swatch, chosen)
            none_btn.setChecked(False)
            self._debounce.start()

    def _rgba_from_pair(self, swatch, none_btn):
        c = swatch.property("qcolor") or QColor("white")
        a = 0 if none_btn.isChecked() else 255
        return (c.red(), c.green(), c.blue(), a)

    # ── apply ──────────────────────────────────────────────────────────────

    def _apply(self):
        self._source.text = self._editor.toPlainText()
        self._source.font_size = self._size_box.value()
        self._source.color    = self._rgba_from_pair(self._color_btn, self._color_none)
        self._source.bg_color = self._rgba_from_pair(self._bg_btn, self._bg_none)
        checked = self._align_group.checkedButton()
        if checked:
            self._source.align = checked.property("align_val")
        self._source.mark_dirty()
