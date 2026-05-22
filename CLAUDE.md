# projmap

Linux-native projection mapping desktop app. Warps GLSL shader / image / video / text sources onto multi-surface quads for a connected projector.

## Stack
PySide6, moderngl (OpenGL 3.3 core, standalone context), numpy, Pillow, opencv-python, anthropic

## Entry Point
`projmap` CLI (installed via `pip install -e .` into `.venv/`). Also runnable via `./launch.sh` or the desktop launcher.

## Architecture

| File | Role |
|------|------|
| `projmap/editor.py` | `EditorWindow` — main window, Canvas + ShaderPanel splitter, 16ms animation timer, File/Surfaces/**Display** menus (Display has Send to Screen, Windowed, Always on Top, Display Layout…), dirty tracking, save/load |
| `projmap/display_panel.py` | `DisplayLayoutDialog` — live-edit dialog (Display ▸ Display Layout…, Ctrl+L): per-surface source picker + corner-position spinboxes + add/delete, applied live |
| `projmap/_screencast_helper.py` | Run under **system** python3 (needs `gi`): creates a Mutter `RecordVirtual` virtual monitor and streams it as raw RGB to stdout via PipeWire+GStreamer. Used by `DesktopSource`. Wayland only. |
| `projmap/canvas.py` | Qt widget showing 1920×1080 stage scaled to fit; draggable corner handles per surface; checkerboard warp preview (NOT shader output) |
| `projmap/output_window.py` | `OutputWindow` — GPU render as QPixmap; goes fullscreen on any screen for projector targeting; Esc returns windowed |
| `projmap/renderer.py` | moderngl standalone context; GLSL → 960×540 FBO → inverse homography warp → 1920×1080 output FBO → numpy → QPixmap |
| `projmap/homography.py` | 3×3 homography via SVD from 4-point correspondences |
| `projmap/surface.py` | `Surface`: a `Quad` + a source; stage is 1920×1080 |
| `projmap/quad.py` | `Quad`: 4 corners as numpy float64 `(4,2)` array in stage pixel coords |
| `projmap/shaders.py` | 10 built-in animated GLSL shaders (Plasma, Tunnel, Noise, Ripple, Kaleidoscope, Scan Lines, Lissajous, Grid Pulse, Voronoi, Aurora) — all use `time` + `resolution` uniforms |
| `projmap/sources.py` | `ImageSource` (PIL), `VideoSource` (OpenCV), `TextSource` (PIL RGBA 960×540), `WindowSource` (live X11 window via `xwd`/XGetImage), `DesktopSource` (Wayland virtual desktop via `_screencast_helper.py`); `list_windows()` enumerates X11 windows via `wmctrl -lx` |
| `projmap/shader_panel.py` | Right sidebar: source list, New/Edit Shader, Load Image/Video, Add Text, Capture Window, Virtual Desktop |
| `projmap/shader_editor.py` | Floating GLSL editor; 500ms debounce compile, Ctrl+S immediate; AI prompt bar calls `claude-opus-4-7` in a QThread worker |
| `projmap/text_editor.py` | `TextEditorWindow`: text content, font size, colour swatches + None/transparent toggles, alignment (L/C/R) |
| `projmap/syntax.py` | GLSL syntax highlighter for QPlainTextEdit |
| `projmap/project.py` | Save/load `.projmap` JSON |

## Key Invariants
- Canvas shows checkerboard warp preview only — shader output is in `OutputWindow`
- Renderer uses a standalone (offscreen) moderngl context — no `QOpenGLWidget`
- Output read back from GPU each frame (FBO → numpy → QImage → QPixmap) — not zero-copy
- Shader programs cached by `id(source)`; `invalidate_source()` clears on live edit
- All sources flip Y before GPU upload
- `TextSource` uses RGBA (4-channel) texture; blend enabled so transparent BG works
- `WindowSource` captures via `xwd -id <xid>` (plain XGetImage, NOT MIT-SHM) in a background thread → so it grabs true window content even when occluded under the compositor (no feedback loop with the fullscreen output). X11 only; needs `xwd` + `wmctrl`. `ximagesrc xid=` was rejected: its `X_ShmGetImage` path fails `BadMatch` on 32-bit-visual windows. Texture auto-resizes if the window resizes.
- Non-shader sources are detected in `renderer.py` by the absence of a `frag_code` attribute (then `update(ctx,time)` + `.texture` are used)
- `DesktopSource` is the no-feedback way to warp a whole desktop: it captures a *virtual* monitor (separate from the projector output), so projmap can run fullscreen on the projector while warping the desktop. **Wayland only** (RecordVirtual). Do NOT add a `videorate` to its pipeline — the virtual-monitor stream's buffers lack durations and `videorate` asserts/crashes; it's damage-driven so already rate-limited.
- X11 vs Wayland tradeoff on the deployment host: `WindowSource` (xwd) + x11vnc need **X11**; `DesktopSource` (RecordVirtual) needs **Wayland**. Can't have both natively in one session.
- AI shader gen reads `ANTHROPIC_API_KEY` from env or `~/.config/projmap/config` (KEY=VALUE format)

## Hardware
- **Dev copy:** `/home/ahrens/projmap` on the laptop (GNOME 46 Wayland — note: `WindowSource` capture needs X11, so it returns no windows here)
- **Deployment host:** 2012 Mac Mini (`ahrens@100.95.20.42` via Tailscale), Ubuntu 24.04 on an **Xorg** session (forced via `WaylandEnable=false`); drives the projector on HDMI-3. This is where window capture works.
- **Projector:** connected as a display output; `OutputWindow` goes fullscreen on it via Qt's per-screen targeting
- Sync laptop→Mac Mini: `rsync -az projmap/ ahrens@100.95.20.42:~/projmap/projmap/`

## Planned (not yet implemented)
- Mesh / 3D object sources
- Region/screen capture (window capture is done; full-screen region grab not yet)
