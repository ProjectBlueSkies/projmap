import sys
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from projmap.editor import EditorWindow


def main():
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("projmap")
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())
