from PySide6.QtWidgets import QMainWindow

from projmap.canvas import Canvas


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("projmap")
        self.resize(1280, 720)
        self.setCentralWidget(Canvas())
