import sys
from PySide6.QtWidgets import QApplication
from projmap.editor import EditorWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("projmap")
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())
