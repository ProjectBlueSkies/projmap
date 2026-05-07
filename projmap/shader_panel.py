from PySide6.QtWidgets import (
    QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from projmap.shaders import BUILTIN_SHADERS
from projmap.sources import ImageSource, VideoSource

_IMAGE_EXTS = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"
_VIDEO_EXTS = "Video (*.mp4 *.mov *.avi *.mkv *.webm *.m4v)"


class ShaderPanel(QWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._sources = list(BUILTIN_SHADERS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Source"))

        self._list = QListWidget()
        for s in self._sources:
            self._list.addItem(s.name)
        self._list.setCurrentRow(0)
        self._list.currentRowChanged.connect(self._assign)
        layout.addWidget(self._list)

        btn_img = QPushButton("Load Image…")
        btn_img.clicked.connect(self._load_image)
        layout.addWidget(btn_img)

        btn_vid = QPushButton("Load Video…")
        btn_vid.clicked.connect(self._load_video)
        layout.addWidget(btn_vid)

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

    def _add_source(self, source):
        self._sources.append(source)
        self._list.addItem(QListWidgetItem(source.name))
        self._list.setCurrentRow(len(self._sources) - 1)

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Image", "", _IMAGE_EXTS)
        if path:
            self._add_source(ImageSource(path))

    def _load_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Video", "", _VIDEO_EXTS)
        if path:
            self._add_source(VideoSource(path))
