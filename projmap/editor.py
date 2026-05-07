from PySide6.QtWidgets import QMainWindow

from projmap.canvas import Canvas
from projmap.output_window import OutputWindow


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("projmap — editor")
        self.resize(1280, 720)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self.output = OutputWindow(self.canvas.quad)
        self.canvas.quad_changed.connect(self.output.widget.update)
        self.output.show()
