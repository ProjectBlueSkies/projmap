from PySide6.QtWidgets import (
    QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from projmap.shaders import BUILTIN_SHADERS, ShaderSource
from projmap.sources import ImageSource, TextSource, VideoSource

_IMAGE_EXTS = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"
_VIDEO_EXTS = "Video (*.mp4 *.mov *.avi *.mkv *.webm *.m4v)"
_custom_count = 0
_text_count = 0


class ShaderPanel(QWidget):
    def __init__(self, canvas, renderer, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._renderer = renderer
        self._sources = list(BUILTIN_SHADERS)
        self._editors = {}  # source id -> open editor window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Source"))

        self._list = QListWidget()
        for s in self._sources:
            self._list.addItem(s.name)
        self._list.setCurrentRow(0)
        self._list.currentRowChanged.connect(self._assign)
        self._list.itemDoubleClicked.connect(self._edit_selected)
        layout.addWidget(self._list)

        btn_new = QPushButton("New Shader…")
        btn_new.clicked.connect(self._new_shader)
        layout.addWidget(btn_new)

        self._btn_edit = QPushButton("Edit…")
        self._btn_edit.clicked.connect(self._edit_selected)
        layout.addWidget(self._btn_edit)

        self._list.currentRowChanged.connect(self._update_edit_btn)

        btn_img = QPushButton("Load Image…")
        btn_img.clicked.connect(self._load_image)
        layout.addWidget(btn_img)

        btn_vid = QPushButton("Load Video…")
        btn_vid.clicked.connect(self._load_video)
        layout.addWidget(btn_vid)

        btn_txt = QPushButton("Add Text…")
        btn_txt.clicked.connect(self._new_text)
        layout.addWidget(btn_txt)

        canvas.surface_selected.connect(self._sync)

    def _assign(self, row):
        if 0 <= row < len(self._sources):
            self._canvas.surfaces[self._canvas.active_idx].source = self._sources[row]

    def _sync(self, surface_idx):
        current = self._canvas.surfaces[surface_idx].source
        for i, s in enumerate(self._sources):
            if s is current:
                self._list.blockSignals(True)
                self._list.setCurrentRow(i)
                self._list.blockSignals(False)
                return

    def _update_edit_btn(self, row=None):
        if row is None:
            row = self._list.currentRow()
        if 0 <= row < len(self._sources):
            src = self._sources[row]
            if isinstance(src, TextSource):
                self._btn_edit.setText("Edit Text…")
                self._btn_edit.setEnabled(True)
                return
            if hasattr(src, 'frag_code'):
                self._btn_edit.setText("Edit Shader…")
                self._btn_edit.setEnabled(True)
                return
        self._btn_edit.setText("Edit…")
        self._btn_edit.setEnabled(False)

    def _add_source(self, source):
        self._sources.append(source)
        self._list.addItem(QListWidgetItem(source.name))
        self._list.setCurrentRow(len(self._sources) - 1)
        self._update_edit_btn()

    def _new_shader(self):
        global _custom_count
        _custom_count += 1
        from projmap.shader_editor import ShaderEditorWindow
        source = ShaderSource(f"Custom {_custom_count}", ShaderEditorWindow.template())
        self._add_source(source)
        self._open_editor(source)

    def _new_text(self):
        global _text_count
        _text_count += 1
        source = TextSource(name=f"Text {_text_count}")
        self._add_source(source)
        self._open_text_editor(source)

    def _edit_selected(self):
        row = self._list.currentRow()
        if row < 0:
            return
        source = self._sources[row]
        if isinstance(source, TextSource):
            self._open_text_editor(source)
            return
        if not hasattr(source, 'frag_code'):
            return  # image/video sources not editable
        # Built-in shaders: copy to a new custom source
        if source in BUILTIN_SHADERS:
            global _custom_count
            _custom_count += 1
            source = ShaderSource(f"Custom {_custom_count} ({source.name})", source.frag_code)
            self._add_source(source)
        self._open_shader_editor(source)

    def _open_shader_editor(self, source):
        from projmap.shader_editor import ShaderEditorWindow
        sid = id(source)
        if sid in self._editors and self._editors[sid].isVisible():
            self._editors[sid].raise_()
            return
        editor = ShaderEditorWindow(source, self._renderer)
        self._editors[sid] = editor
        editor.show()

    def _open_text_editor(self, source):
        from projmap.text_editor import TextEditorWindow
        sid = id(source)
        if sid in self._editors and self._editors[sid].isVisible():
            self._editors[sid].raise_()
            return
        editor = TextEditorWindow(source)
        self._editors[sid] = editor
        editor.show()

    def _open_editor(self, source):
        self._open_shader_editor(source)

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Image", "", _IMAGE_EXTS)
        if path:
            self._add_source(ImageSource(path))

    def _load_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Video", "", _VIDEO_EXTS)
        if path:
            self._add_source(VideoSource(path))

    def register_source(self, source):
        """Register an externally-created source (e.g. from project load) into the panel."""
        self._sources.append(source)
        self._list.addItem(QListWidgetItem(source.name))
