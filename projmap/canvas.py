import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QWidget

from projmap.quad import Quad
from projmap.test_pattern import make_checkerboard

STAGE_W = 1920
STAGE_H = 1080
HANDLE_R = 9


class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setMouseTracking(True)
        self._scale = 1.0
        self._ox = 0.0
        self._oy = 0.0
        self.quad = Quad.centered(STAGE_W, STAGE_H)
        self._dragging = None
        self._pattern = make_checkerboard()

    def _update_transform(self):
        pad = 24
        sw = self.width() - 2 * pad
        sh = self.height() - 2 * pad
        self._scale = min(sw / STAGE_W, sh / STAGE_H)
        self._ox = (self.width() - STAGE_W * self._scale) / 2
        self._oy = (self.height() - STAGE_H * self._scale) / 2

    def resizeEvent(self, event):
        self._update_transform()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._update_transform()
        super().showEvent(event)

    def _s2w(self, pt):
        return np.array([pt[0] * self._scale + self._ox,
                         pt[1] * self._scale + self._oy])

    def _w2s(self, pt):
        return np.array([(pt[0] - self._ox) / self._scale,
                         (pt[1] - self._oy) / self._scale])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Stage background
        painter.fillRect(
            int(self._ox), int(self._oy),
            int(STAGE_W * self._scale), int(STAGE_H * self._scale),
            QColor(15, 15, 15),
        )

        # Perspective-warp test pattern into quad
        pw, ph = self._pattern.width(), self._pattern.height()
        corners_w = [self._s2w(c) for c in self.quad.corners]
        src = QPolygonF([QPointF(0, 0), QPointF(pw, 0), QPointF(pw, ph), QPointF(0, ph)])
        dst = QPolygonF([QPointF(c[0], c[1]) for c in corners_w])
        xform = QTransform()
        if QTransform.quadToQuad(src, dst, xform):
            painter.save()
            painter.setTransform(xform)
            painter.drawPixmap(0, 0, self._pattern)
            painter.restore()

        # Quad outline
        painter.setPen(QPen(QColor(255, 200, 0), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pts = [QPointF(c[0], c[1]) for c in corners_w]
        for i in range(4):
            painter.drawLine(pts[i], pts[(i + 1) % 4])

        # Handles
        for i, cw in enumerate(corners_w):
            active = i == self._dragging
            painter.setBrush(QBrush(QColor(255, 80, 80) if active else QColor(255, 255, 255)))
            painter.setPen(QPen(QColor(0, 0, 0), 1.5))
            painter.drawEllipse(QPointF(cw[0], cw[1]), HANDLE_R, HANDLE_R)

    def _hit_handle(self, wx, wy):
        pt = np.array([wx, wy])
        for i, c in enumerate(self.quad.corners):
            if np.linalg.norm(self._s2w(c) - pt) <= HANDLE_R + 3:
                return i
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = self._hit_handle(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        if self._dragging is not None:
            self.quad.corners[self._dragging] = self._w2s(
                np.array([event.position().x(), event.position().y()])
            )
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = None
