from projmap.quad import Quad
from projmap.shaders import BUILTIN_SHADERS

STAGE_W = 1920
STAGE_H = 1080


class Surface:
    def __init__(self, quad=None, source=None):
        self.quad = quad or Quad.centered(STAGE_W, STAGE_H, fill=0.5)
        self.source = source or BUILTIN_SHADERS[0]
