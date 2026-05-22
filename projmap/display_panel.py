"""Live-edit Display Layout dialog.

Lets you adjust each mapped surface's corner positions and choose what it shows,
while the projector output updates live. Reachable from the Display menu.
"""
import numpy as np
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QListWidget, QPushButton, QVBoxLayout,
)

from projmap.renderer import STAGE_W, STAGE_H

_CORNER_LABELS = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]


class DisplayLayoutDialog(QDialog):
    def __init__(self, canvas, sources, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Display Layout")
        self.resize(420, 360)
        self._canvas = canvas
        self._sources = sources
        self._loading = False

        root = QHBoxLayout(self)

        # Left: surface list + add/delete
        left = QVBoxLayout()
        left.addWidget(QLabel("Surfaces"))
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._select_row)
        left.addWidget(self._list)
        row = QHBoxLayout()
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        rm = QPushButton("Delete")
        rm.clicked.connect(self._delete)
        row.addWidget(add)
        row.addWidget(rm)
        left.addLayout(row)
        root.addLayout(left)

        # Right: source + corner editors
        right = QVBoxLayout()
        right.addWidget(QLabel("Shows"))
        self._source_combo = QComboBox()
        self._source_combo.currentIndexChanged.connect(self._set_source)
        right.addWidget(self._source_combo)

        box = QGroupBox("Corner positions (stage px)")
        grid = QGridLayout(box)
        self._spins = []  # list of (x_spin, y_spin)
        for i, lbl in enumerate(_CORNER_LABELS):
            grid.addWidget(QLabel(lbl), i, 0)
            xs = QDoubleSpinBox()
            xs.setRange(-2000, STAGE_W + 2000)
            xs.setDecimals(0)
            ys = QDoubleSpinBox()
            ys.setRange(-2000, STAGE_H + 2000)
            ys.setDecimals(0)
            xs.valueChanged.connect(self._apply_corners)
            ys.valueChanged.connect(self._apply_corners)
            grid.addWidget(xs, i, 1)
            grid.addWidget(ys, i, 2)
            self._spins.append((xs, ys))
        right.addWidget(box)
        right.addStretch(1)
        root.addLayout(right)

        canvas.scene_changed.connect(self._reload)
        if hasattr(canvas, "surface_selected"):
            canvas.surface_selected.connect(self._on_canvas_select)
        self._reload()

    # ---- population ----
    def _reload(self):
        self._loading = True
        self._list.clear()
        for i, surf in enumerate(self._canvas.surfaces):
            self._list.addItem(f"Surface {i + 1} — {surf.source.name}")
        idx = self._canvas.active_idx
        if 0 <= idx < self._list.count():
            self._list.setCurrentRow(idx)
        self._populate_source_combo()
        self._load_corners()
        self._loading = False

    def _populate_source_combo(self):
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        for s in self._sources:
            self._source_combo.addItem(s.name)
        cur = self._canvas.surfaces[self._canvas.active_idx].source
        for i, s in enumerate(self._sources):
            if s is cur:
                self._source_combo.setCurrentIndex(i)
                break
        self._source_combo.blockSignals(True)
        self._source_combo.blockSignals(False)

    def _load_corners(self):
        surf = self._canvas.surfaces[self._canvas.active_idx]
        corners = surf.quad.corners
        for i, (xs, ys) in enumerate(self._spins):
            xs.blockSignals(True)
            ys.blockSignals(True)
            xs.setValue(float(corners[i][0]))
            ys.setValue(float(corners[i][1]))
            xs.blockSignals(False)
            ys.blockSignals(False)

    # ---- edits ----
    def _select_row(self, row):
        if self._loading or not (0 <= row < len(self._canvas.surfaces)):
            return
        self._canvas.active_idx = row
        self._canvas.update()
        if hasattr(self._canvas, "surface_selected"):
            self._canvas.surface_selected.emit(row)
        self._populate_source_combo()
        self._load_corners()

    def _on_canvas_select(self, idx):
        if 0 <= idx < self._list.count():
            self._list.blockSignals(True)
            self._list.setCurrentRow(idx)
            self._list.blockSignals(False)
            self._populate_source_combo()
            self._load_corners()

    def _set_source(self, idx):
        if self._loading or not (0 <= idx < len(self._sources)):
            return
        self._canvas.surfaces[self._canvas.active_idx].source = self._sources[idx]
        self._canvas.scene_changed.emit()

    def _apply_corners(self):
        if self._loading:
            return
        surf = self._canvas.surfaces[self._canvas.active_idx]
        pts = [[xs.value(), ys.value()] for xs, ys in self._spins]
        surf.quad.corners = np.array(pts, dtype=np.float64)
        self._canvas.update()
        self._canvas.scene_changed.emit()

    def _add(self):
        self._canvas.add_surface()
        self._reload()

    def _delete(self):
        self._canvas.delete_active()
        self._reload()
