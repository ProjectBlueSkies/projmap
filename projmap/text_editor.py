from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup, QColorDialog, QHBoxLayout, QLabel,
    QMainWindow, QPlainTextEdit, QPushButton, QRadioButton,
    QSpinBox, QVBoxLayout, QWidget,
)


class TextEditorWindow(QMainWindow):
    def __init__(self, source, parent=None):
        super().__init__(parent)
        self._source = source
        self.setWindowTitle(f"Text — {source.name}")
        self.resize(560, 460)

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

        # Controls bar
        bar = QWidget()
        bar.setStyleSheet("background:#252526;")
        bar.setFixedHeight(44)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(10)

        row.addWidget(self._label("Size"))
        self._size_box = QSpinBox()
        self._size_box.setRange(8, 500)
        self._size_box.setValue(source.font_size)
        self._size_box.setFixedWidth(70)
        self._size_box.setStyleSheet(
            "background:#1e1e1e; color:#eeffff; border:1px solid #3c3c3c; padding:2px 4px;"
        )
        row.addWidget(self._size_box)

        row.addWidget(self._label("Color"))
        self._color_btn = self._color_button(QColor(*source.color))
        row.addWidget(self._color_btn)

        row.addWidget(self._label("BG"))
        self._bg_btn = self._color_button(QColor(*source.bg_color))
        row.addWidget(self._bg_btn)

        row.addWidget(self._label("Align"))
        self._align_group = QButtonGroup(self)
        for i, (label, val) in enumerate([("L", "left"), ("C", "center"), ("R", "right")]):
            rb = QRadioButton(label)
            rb.setStyleSheet("color:#eeffff; font-size:12px;")
            rb.setProperty("align_val", val)
            if val == source.align:
                rb.setChecked(True)
            self._align_group.addButton(rb, i)
            row.addWidget(rb)

        row.addStretch()
        layout.addWidget(bar)

        self._debounce = QTimer(singleShot=True, interval=300)
        self._debounce.timeout.connect(self._apply)
        self._editor.textChanged.connect(self._debounce.start)
        self._size_box.valueChanged.connect(self._debounce.start)
        self._align_group.buttonToggled.connect(lambda *_: self._debounce.start())

        self.statusBar().hide()

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#9E9E9E; font-size:11px;")
        return lbl

    def _color_button(self, color: QColor):
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        self._set_btn_color(btn, color)
        btn.clicked.connect(lambda: self._pick_color(btn))
        return btn

    def _set_btn_color(self, btn, color: QColor):
        btn.setStyleSheet(
            f"background:{color.name()}; border:1px solid #555; border-radius:3px;"
        )
        btn.setProperty("color", color)

    def _pick_color(self, btn):
        current = btn.property("color") or QColor(Qt.GlobalColor.white)
        chosen = QColorDialog.getColor(current, self, "Pick colour")
        if chosen.isValid():
            self._set_btn_color(btn, chosen)
            self._debounce.start()

    def _apply(self):
        self._source.text = self._editor.toPlainText()
        self._source.font_size = self._size_box.value()
        c = self._color_btn.property("color")
        self._source.color = (c.red(), c.green(), c.blue())
        bg = self._bg_btn.property("color")
        self._source.bg_color = (bg.red(), bg.green(), bg.blue())
        checked = self._align_group.checkedButton()
        if checked:
            self._source.align = checked.property("align_val")
        self._source.mark_dirty()
