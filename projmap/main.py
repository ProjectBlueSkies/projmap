import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QSurfaceFormat
from PySide6.QtWidgets import QApplication

from projmap.editor import EditorWindow

_ICON = Path(__file__).parent.parent / "icon.svg"


def main():
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("projmap")
    if _ICON.exists():
        app.setWindowIcon(QIcon(str(_ICON)))
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())
