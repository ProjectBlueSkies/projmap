from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMainWindow

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

        self._build_menu()

        app = QApplication.instance()
        app.screenAdded.connect(self._refresh_screens)
        app.screenRemoved.connect(self._refresh_screens)

    def _build_menu(self):
        output_menu = self.menuBar().addMenu("Output")

        self._screen_group = QActionGroup(self)
        self._screen_group.setExclusive(True)
        self._screen_menu = output_menu.addMenu("Send to Screen")
        self._refresh_screens()

        output_menu.addSeparator()

        windowed = QAction("Windowed", self)
        windowed.triggered.connect(self.output.go_windowed)
        output_menu.addAction(windowed)

    def _refresh_screens(self):
        self._screen_menu.clear()
        for a in self._screen_group.actions():
            self._screen_group.removeAction(a)

        for i, screen in enumerate(QApplication.screens()):
            geo = screen.geometry()
            label = f"Screen {i + 1}: {screen.name()}  {geo.width()}×{geo.height()}"
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked, s=screen: self.output.send_to_screen(s))
            self._screen_group.addAction(action)
            self._screen_menu.addAction(action)
