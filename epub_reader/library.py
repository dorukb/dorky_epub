import os
import shutil
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QFileDialog, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QLabel, QMenu)
from PyQt6.QtCore import Qt
from .database import load_library, save_library, get_epub_meta, STORAGE_DIR, delete_book_files
from .reader import ReaderWindow

class LibraryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dorky Library")
        self.resize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        layout.addWidget(QLabel("<h2>Books</h2>"))

        # Book List
        self.book_list = QListWidget()
        self.book_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self.show_context_menu)
        self.book_list.itemDoubleClicked.connect(self.open_book)
        layout.addWidget(self.book_list)

        btn = QPushButton("Import")
        btn.clicked.connect(self.import_book)
        layout.addWidget(btn)

        self.refresh_list()
        
        # Placeholder for the reader window reference
        self.reader = None

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
        delete_action = menu.addAction("Delete")
        action = menu.exec(self.book_list.mapToGlobal(pos))

        if action == delete_action:
            book_id = item.data(Qt.ItemDataRole.UserRole)
            self.delete_book(book_id)

    def delete_book(self, book_id):
        lib = load_library()
        if book_id in lib:
            filename = lib[book_id]['filename']
            delete_book_files(filename) 
            del lib[book_id]            
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
            # Use filename as simple ID
            book_id = filename 
            
            lib[book_id] = {'title': title, 'filename': filename, 'last_chapter_index': 0}
            save_library(lib)
            self.refresh_list()

    def open_book(self, item):
        book_id = item.data(Qt.ItemDataRole.UserRole)
        lib = load_library()
        if book_id in lib:
            self.hide()
            
            # This ensures that when Reader closes, it calls this method.
            self.reader = ReaderWindow(book_id, lib[book_id], self.show_library)
            self.reader.show()

    def show_library(self):
        """Callback to re-open library when reader closes"""
        self.refresh_list() # Good practice to refresh data
        self.show()