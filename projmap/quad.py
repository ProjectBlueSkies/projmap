import numpy as np


class Quad:
    def __init__(self, corners):
        self.corners = np.array(corners, dtype=np.float64)

    @classmethod
    def centered(cls, stage_w, stage_h, fill=0.6):
        m = (1 - fill) / 2
        x0, y0 = stage_w * m, stage_h * m
        x1, y1 = stage_w * (1 - m), stage_h * (1 - m)
        return cls([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
