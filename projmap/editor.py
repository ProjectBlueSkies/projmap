from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("projmap")
        self.resize(1280, 720)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        placeholder = QLabel("Editor canvas coming soon")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
