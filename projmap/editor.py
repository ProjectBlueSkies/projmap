import time as _time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMessageBox, QSplitter,
)

import projmap.project as _project
from projmap.canvas import Canvas
from projmap.output_window import OutputWindow
from projmap.renderer import Renderer
from projmap.shader_panel import ShaderPanel
from projmap.shaders import BUILTIN_SHADERS


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1440, 810)

        self._renderer = Renderer()

        self.canvas = Canvas()
        self._shader_panel = ShaderPanel(self.canvas, self._renderer)
        self._shader_panel.setFixedWidth(180)

        splitter = QSplitter()
        splitter.addWidget(self.canvas)
        splitter.addWidget(self._shader_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        self.setCentralWidget(splitter)

        self.output = OutputWindow(self.canvas, self._renderer)
        self.output.show()
        self.output.raise_()

        self._current_path = None
        self._dirty = False
        self._update_title()

        self._build_menu()
        self._start_time = _time.monotonic()
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(16)

        self._update_status()
        self.canvas.scene_changed.connect(self._mark_dirty)
        self.canvas.scene_changed.connect(self._update_status)

        app = QApplication.instance()
        app.screenAdded.connect(self._refresh_screens)
        app.screenRemoved.connect(self._refresh_screens)

    def _elapsed(self):
        return _time.monotonic() - self._start_time

    def _tick(self):
        self.output.refresh(self._elapsed())

    def _mark_dirty(self):
        self._dirty = True
        self._update_title()

    def _update_title(self):
        name = Path(self._current_path).name if self._current_path else "Untitled"
        marker = " •" if self._dirty else ""
        self.setWindowTitle(f"projmap — {name}{marker}")

    def _confirm_discard(self):
        if not self._dirty:
            return True
        resp = QMessageBox.question(
            self, "Unsaved changes",
            "Save changes before continuing?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if resp == QMessageBox.StandardButton.Save:
            return self._save()
        return resp == QMessageBox.StandardButton.Discard

    def _new_project(self):
        if not self._confirm_discard():
            return
        from projmap.surface import Surface
        self.canvas.surfaces = [Surface()]
        self.canvas.active_idx = 0
        self.canvas.update()
        self.canvas.scene_changed.emit()
        self._current_path = None
        self._dirty = False
        self._update_title()

    def _open_project(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", _project.FILE_FILTER
        )
        if not path:
            return
        surfaces = _project.load(path)
        self._register_loaded_sources(surfaces)
        self.canvas.surfaces = surfaces
        self.canvas.active_idx = 0
        self.canvas.update()
        self.canvas.scene_changed.emit()
        self._current_path = path
        self._dirty = False
        self._update_title()

    def _register_loaded_sources(self, surfaces):
        builtin_ids = {id(s) for s in BUILTIN_SHADERS}
        seen = set()
        for surf in surfaces:
            src = surf.source
            if id(src) not in builtin_ids and id(src) not in seen:
                seen.add(id(src))
                self._shader_panel.register_source(src)

    def _save(self):
        if self._current_path:
            _project.save(self.canvas.surfaces, self._current_path)
            self._dirty = False
            self._update_title()
            return True
        return self._save_as()

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", _project.FILE_FILTER
        )
        if not path:
            return False
        if not path.endswith(_project.FILE_EXT):
            path += _project.FILE_EXT
        _project.save(self.canvas.surfaces, path)
        self._current_path = path
        self._dirty = False
        self._update_title()
        return True

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save)
        file_menu.addAction(save_action)

        saveas_action = QAction("Save As…", self)
        saveas_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        saveas_action.triggered.connect(self._save_as)
        file_menu.addAction(saveas_action)

        file_menu.addSeparator()

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
        src = self.canvas.surfaces[self.canvas.active_idx].source.name
        self.statusBar().showMessage(
            f"Surface {i}/{n} · {src}  —  N: add  Del: remove  Click to select"
        )
