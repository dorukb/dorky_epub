import sys
from PyQt6.QtWidgets import QApplication
from epub_reader.library import LibraryWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Optional: Enable high DPI scaling
    # app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    
    window = LibraryWindow()
    window.show()
    sys.exit(app.exec())