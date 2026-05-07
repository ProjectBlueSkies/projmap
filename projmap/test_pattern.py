import numpy as np
from PySide6.QtGui import QImage, QPixmap


def make_checkerboard(w=640, h=360, cell=40):
    xs = np.arange(w)
    ys = np.arange(h)
    grid = (xs[None, :] // cell + ys[:, None] // cell) % 2
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[grid == 0] = [200, 200, 200]
    arr[grid == 1] = [45, 45, 45]
    img = QImage(arr.tobytes(), w, h, w * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img)
