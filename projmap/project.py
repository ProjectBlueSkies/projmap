import json
from pathlib import Path

import numpy as np

from projmap.quad import Quad
from projmap.shaders import BUILTIN_SHADERS, ShaderSource
from projmap.sources import ImageSource, TextSource, VideoSource
from projmap.surface import Surface

VERSION = 1
FILE_EXT = ".projmap"
FILE_FILTER = f"projmap project (*{FILE_EXT})"

_BUILTIN_BY_NAME = {s.name: s for s in BUILTIN_SHADERS}


def _ser_source(source):
    for s in BUILTIN_SHADERS:
        if s is source:
            return {"type": "builtin", "name": s.name}
    if hasattr(source, "frag_code"):
        return {"type": "custom", "name": source.name, "code": source.frag_code}
    if isinstance(source, ImageSource):
        return {"type": "image", "path": str(source.path)}
    if isinstance(source, VideoSource):
        return {"type": "video", "path": str(source.path)}
    if isinstance(source, TextSource):
        return {
            "type": "text",
            "name": source.name,
            "text": source.text,
            "font_size": source.font_size,
            "color": list(source.color),
            "bg_color": list(source.bg_color),
            "align": source.align,
        }
    return {"type": "builtin", "name": BUILTIN_SHADERS[0].name}


def _deser_source(data):
    t = data.get("type", "builtin")
    if t == "builtin":
        return _BUILTIN_BY_NAME.get(data.get("name", ""), BUILTIN_SHADERS[0])
    if t == "custom":
        return ShaderSource(data.get("name", "Custom"), data["code"])
    if t == "image":
        p = Path(data["path"])
        if not p.exists():
            print(f"Warning: image not found: {p}")
            return BUILTIN_SHADERS[0]
        return ImageSource(p)
    if t == "video":
        p = Path(data["path"])
        if not p.exists():
            print(f"Warning: video not found: {p}")
            return BUILTIN_SHADERS[0]
        return VideoSource(p)
    if t == "text":
        def _c(val, default):
            v = list(val) if val is not None else list(default)
            if len(v) == 3:
                v.append(255)
            return tuple(v)
        return TextSource(
            name=data.get("name", "Text"),
            text=data.get("text", "Hello"),
            font_size=data.get("font_size", 120),
            color=_c(data.get("color"), [255, 255, 255, 255]),
            bg_color=_c(data.get("bg_color"), [0, 0, 0, 255]),
            align=data.get("align", "center"),
        )
    return BUILTIN_SHADERS[0]


def save(surfaces, path):
    payload = {
        "version": VERSION,
        "surfaces": [
            {
                "quad": surf.quad.corners.tolist(),
                "source": _ser_source(surf.source),
            }
            for surf in surfaces
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2))


def load(path):
    payload = json.loads(Path(path).read_text())
    surfaces = []
    for sd in payload.get("surfaces", []):
        quad = Quad(np.array(sd["quad"], dtype=np.float64))
        source = _deser_source(sd.get("source", {}))
        surfaces.append(Surface(quad=quad, source=source))
    return surfaces or [Surface()]
