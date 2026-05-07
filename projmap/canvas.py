import numpy as np
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QWidget

from projmap.quad import Quad
from projmap.surface import Surface, STAGE_W, STAGE_H
from projmap.test_pattern import make_checkerboard

HANDLE_R = 9


def _point_in_quad(corners, px, py):
    crosses = []
    for i in range(4):
        ax, ay = corners[i]
        bx, by = corners[(i + 1) % 4]
        crosses.append((bx - ax) * (py - ay) - (by - ay) * (px - ax))
    return all(c >= 0 for c in crosses) or all(c <= 0 for c in crosses)


class Canvas(QWidget):
    scene_changed = Signal()
    surface_selected = Signal(int)  # emitted when active_idx changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._scale = 1.0
        self._ox = 0.0
        self._oy = 0.0
        self.surfaces = [Surface()]
        self.active_idx = 0
        self._dragging = None  # (surface_idx, corner_idx) or None
        self._pattern = make_checkerboard()

    def _update_transform(self):
        pad = 24
        self._scale = min(
            (self.width() - 2 * pad) / STAGE_W,
            (self.height() - 2 * pad) / STAGE_H,
        )
        self._ox = (self.width() - STAGE_W * self._scale) / 2
        self._oy = (self.height() - STAGE_H * self._scale) / 2

    def resizeEvent(self, event):
        self._update_transform()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._update_transform()
        super().showEvent(event)

    def _s2w(self, pt):
        return np.array([pt[0] * self._scale + self._ox, pt[1] * self._scale + self._oy])

    def _w2s(self, pt):
        return np.array([(pt[0] - self._ox) / self._scale, (pt[1] - self._oy) / self._scale])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(
            int(self._ox), int(self._oy),
            int(STAGE_W * self._scale), int(STAGE_H * self._scale),
            QColor(15, 15, 15),
        )

        # Draw inactive surfaces first, active surface last (handles on top)
        order = [i for i in range(len(self.surfaces)) if i != self.active_idx]
        if self.active_idx is not None and self.active_idx < len(self.surfaces):
            order.append(self.active_idx)

        for si in order:
            self._draw_surface(painter, si)

    def _draw_surface(self, painter, si):
        surface = self.surfaces[si]
        is_active = (si == self.active_idx)
        corners_w = [self._s2w(c) for c in surface.quad.corners]

        pw, ph = self._pattern.width(), self._pattern.height()
        src = QPolygonF([QPointF(0, 0), QPointF(pw, 0), QPointF(pw, ph), QPointF(0, ph)])
        dst = QPolygonF([QPointF(c[0], c[1]) for c in corners_w])
        xform = QTransform()
        if QTransform.quadToQuad(src, dst, xform):
            painter.save()
            painter.setTransform(xform)
            painter.drawPixmap(0, 0, self._pattern)
            painter.restore()

        outline = QColor(255, 200, 0) if is_active else QColor(90, 70, 0)
        painter.setPen(QPen(outline, 1.5 if is_active else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pts = [QPointF(c[0], c[1]) for c in corners_w]
        for i in range(4):
            painter.drawLine(pts[i], pts[(i + 1) % 4])

        if is_active:
            for ci, cw in enumerate(corners_w):
                dragging_this = (self._dragging == (si, ci))
                painter.setBrush(QBrush(QColor(255, 80, 80) if dragging_this else QColor(255, 255, 255)))
                painter.setPen(QPen(QColor(0, 0, 0), 1.5))
                painter.drawEllipse(QPointF(cw[0], cw[1]), HANDLE_R, HANDLE_R)

    def _hit_handle(self, wx, wy):
        pt = np.array([wx, wy])
        # Active surface has priority, then top-to-bottom z-order
        check_order = []
        if self.active_idx is not None:
            check_order.append(self.active_idx)
        check_order += [i for i in reversed(range(len(self.surfaces))) if i != self.active_idx]
        for si in check_order:
            for ci, c in enumerate(self.surfaces[si].quad.corners):
                if np.linalg.norm(self._s2w(c) - pt) <= HANDLE_R + 3:
                    return (si, ci)
        return None

    def _hit_surface(self, wx, wy):
        stage_pt = self._w2s(np.array([wx, wy]))
        for si in reversed(range(len(self.surfaces))):
            if _point_in_quad(self.surfaces[si].quad.corners, stage_pt[0], stage_pt[1]):
                return si
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            wx, wy = event.position().x(), event.position().y()
            prev = self.active_idx
            hit = self._hit_handle(wx, wy)
            if hit is not None:
                self.active_idx = hit[0]
                self._dragging = hit
            else:
                si = self._hit_surface(wx, wy)
                if si is not None:
                    self.active_idx = si
                self._dragging = None
            if self.active_idx != prev:
                self.surface_selected.emit(self.active_idx)
            self.update()

    def mouseMoveEvent(self, event):
        if self._dragging is not None:
            si, ci = self._dragging
            self.surfaces[si].quad.corners[ci] = self._w2s(
                np.array([event.position().x(), event.position().y()])
            )
            self.update()
            self.scene_changed.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_N:
            self.add_surface()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_active()
        else:
            super().keyPressEvent(event)

    def add_surface(self):
        offset = len(self.surfaces) * 40
        quad = Quad.centered(STAGE_W, STAGE_H, fill=0.5)
        quad.corners += offset
        self.surfaces.append(Surface(quad))
        self.active_idx = len(self.surfaces) - 1
        self.update()
        self.scene_changed.emit()
        self.surface_selected.emit(self.active_idx)

    def delete_active(self):
        if len(self.surfaces) <= 1:
            return
        self.surfaces.pop(self.active_idx)
        self.active_idx = min(self.active_idx, len(self.surfaces) - 1)
        self.update()
        self.scene_changed.emit()
        self.surface_selected.emit(self.active_idx)
