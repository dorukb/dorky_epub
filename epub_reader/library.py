import os
import shutil
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QFileDialog, 
                             QPushButton, QListWidget, QListWidgetItem, QMessageBox, 
                             QHBoxLayout, QLabel, QMenu)
from PyQt6.QtCore import Qt
from .database import load_library, save_library, get_epub_meta, STORAGE_DIR, delete_book_files
from .reader import ReaderWindow

class LibraryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Python Library")
        self.resize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("<h2>My Bookshelf</h2>"))

        # Book List with Context Menu enabled
        self.book_list = QListWidget()
        self.book_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self.show_context_menu)
        self.book_list.itemDoubleClicked.connect(self.open_book)
        layout.addWidget(self.book_list)

        btn = QPushButton("Import Book")
        btn.clicked.connect(self.import_book)
        layout.addWidget(btn)

        self.refresh_list()

    def refresh_list(self):
        self.book_list.clear()
        library = load_library()
        for b_id, data in library.items():
            item = QListWidgetItem(f"{data['title']}")
            item.setData(Qt.ItemDataRole.UserRole, b_id)
            self.book_list.addItem(item)

    def show_context_menu(self, pos):
        item = self.book_list.itemAt(pos)
        if not item: return

        menu = QMenu()
        delete_action = menu.addAction("Delete Book")
        action = menu.exec(self.book_list.mapToGlobal(pos))

        if action == delete_action:
            book_id = item.data(Qt.ItemDataRole.UserRole)
            self.delete_book(book_id)

    def delete_book(self, book_id):
        lib = load_library()
        if book_id in lib:
            filename = lib[book_id]['filename']
            delete_book_files(filename) # Delete actual file
            del lib[book_id]            # Delete from DB
            save_library(lib)
            self.refresh_list()

    def import_book(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Import', filter="EPUB (*.epub)")
        if fname:
            filename = os.path.basename(fname)
            dest = os.path.join(STORAGE_DIR, filename)
            shutil.copyfile(fname, dest)
            
            title = get_epub_meta(dest)
            lib = load_library()
            # Simple ID generation (timestamp or uuid is better, but filename works for MVP)
            book_id = filename 
            
            lib[book_id] = {'title': title, 'filename': filename, 'last_chapter_index': 0}
            save_library(lib)
            self.refresh_list()

    def open_book(self, item):
        book_id = item.data(Qt.ItemDataRole.UserRole)
        lib = load_library()
        if book_id in lib:
            self.reader = ReaderWindow(book_id, lib[book_id], self.show)
            self.reader.show()
            self.hide()