from projmap.quad import Quad

STAGE_W = 1920
STAGE_H = 1080


class Surface:
    def __init__(self, quad=None):
        self.quad = quad or Quad.centered(STAGE_W, STAGE_H, fill=0.5)
