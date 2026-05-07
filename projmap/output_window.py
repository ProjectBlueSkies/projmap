from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QMainWindow


class OutputWindow(QMainWindow):
    def __init__(self, canvas, renderer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("projmap — output")
        self.resize(960, 540)
        self._canvas = canvas
        self._renderer = renderer
        self._pending_screen = None

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: black;")
        self.setCentralWidget(self._label)

    def refresh(self):
        pixmap = self._renderer.render(self._canvas.surfaces)
        self._label.setPixmap(
            pixmap.scaled(
                self._label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh()

    def send_to_screen(self, screen):
        self._pending_screen = screen
        if self.isFullScreen():
            self.showNormal()
            QTimer.singleShot(150, self._apply_screen)
        else:
            self._apply_screen()

    def _apply_screen(self):
        screen = self._pending_screen
        if screen is None:
            return
        handle = self.windowHandle()
        if handle:
            handle.setScreen(screen)
        self.raise_()
        self.activateWindow()
        self.showFullScreen()

    def go_windowed(self):
        self._pending_screen = None
        self.showNormal()
        self.resize(960, 540)
        self.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_windowed()
        super().keyPressEvent(event)
