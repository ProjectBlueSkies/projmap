# projmap

A Linux-native projection mapping tool with a focus on usability and polished output.

## Goals

- Intuitive surface editor with real-time warping
- Support for walls (quads/meshes) and 3D objects (mesh import)
- Media sources: video, images, live GLSL shaders, screen capture
- Clean split editor/output architecture

## Stack

- **PySide6** — editor UI
- **moderngl** — OpenGL rendering
- **numpy** — projection and geometry math
- **GStreamer / OpenCV** — video pipeline (planned)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
projmap
```

## Status

Early development.
