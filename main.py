import sys
from PyQt6.QtWidgets import QApplication
from epub_reader.library import LibraryWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LibraryWindow()
    window.show()
    sys.exit(app.exec())