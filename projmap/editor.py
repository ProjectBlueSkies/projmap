from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMainWindow

from projmap.canvas import Canvas
from projmap.output_window import OutputWindow
from projmap.renderer import Renderer


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("projmap — editor")
        self.resize(1280, 720)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self._renderer = Renderer()
        self.output = OutputWindow(self.canvas, self._renderer)
        self.canvas.scene_changed.connect(self.output.refresh)
        self.output.show()
        self.output.raise_()
        self.output.refresh()

        self._build_menu()
        self._update_status()

        app = QApplication.instance()
        app.screenAdded.connect(self._refresh_screens)
        app.screenRemoved.connect(self._refresh_screens)
        self.canvas.scene_changed.connect(self._update_status)

    def _build_menu(self):
        surfaces_menu = self.menuBar().addMenu("Surfaces")
        add_action = QAction("Add Surface", self)
        add_action.setShortcut("N")
        add_action.triggered.connect(self.canvas.add_surface)
        surfaces_menu.addAction(add_action)

        del_action = QAction("Delete Selected", self)
        del_action.setShortcut("Delete")
        del_action.triggered.connect(self.canvas.delete_active)
        surfaces_menu.addAction(del_action)

        output_menu = self.menuBar().addMenu("Output")
        self._screen_group = QActionGroup(self)
        self._screen_group.setExclusive(True)
        self._screen_menu = output_menu.addMenu("Send to Screen")
        self._refresh_screens()

        output_menu.addSeparator()
        windowed = QAction("Windowed", self)
        windowed.triggered.connect(self._go_windowed)
        output_menu.addAction(windowed)

    def _refresh_screens(self):
        self._screen_menu.clear()
        for a in self._screen_group.actions():
            self._screen_group.removeAction(a)
        for i, screen in enumerate(QApplication.screens()):
            geo = screen.geometry()
            label = f"Screen {i + 1}: {screen.name()}  {geo.width()}×{geo.height()}"
            action = QAction(label, self, checkable=True)
            action.triggered.connect(
                lambda checked, s=screen, lbl=label: self._select_screen(s, lbl)
            )
            self._screen_group.addAction(action)
            self._screen_menu.addAction(action)

    def _select_screen(self, screen, label):
        self.output.send_to_screen(screen)
        self.statusBar().showMessage(f"Output: {label}  —  Esc to return to windowed")

    def _go_windowed(self):
        self.output.go_windowed()
        for a in self._screen_group.actions():
            a.setChecked(False)
        self._update_status()

    def _update_status(self):
        n = len(self.canvas.surfaces)
        i = self.canvas.active_idx + 1
        self.statusBar().showMessage(
            f"Surface {i} of {n}  —  N: add  Del: remove  Click surface to select"
        )
