import json
import os
import shutil
import tempfile
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QFileDialog, 
                             QPushButton, QLabel, QMenu, QScrollArea, QHBoxLayout, 
                             QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from ebooklib import epub
from .database import load_library, save_library, STORAGE_DIR, delete_book_files
from .reader import ReaderWindow

class BookCard(QFrame):
    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, b_id, data, is_dark=False):
        super().__init__()
        self.b_id = b_id
        self.data = data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self.update_style(is_dark)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        icon = QLabel("📖")
        icon.setStyleSheet("font-size: 30px; background: transparent; border: none;")
        layout.addWidget(icon)
        layout.addSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        title = QLabel(data['title'])
        title.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent; border: none;")
        info_layout.addWidget(title)
        
        # We now use the calculated percentage from the Reader if available.
        # Fallback to chapter math only if it's a fresh book.
        percent = data.get('progress_percent', 0)
        
        progress = QLabel(f"{percent}% Complete")
        progress.setStyleSheet("font-size: 12px; color: #888; background: transparent; border: none;")
        info_layout.addWidget(progress)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context)

    def update_style(self, is_dark):
        if is_dark:
            bg = "#2d2d2d"
            border = "#3d3d3d"
            text = "#fff"
            hover = "#383838"
        else:
            bg = "#ffffff"
            border = "#e0e0e0"
            text = "#000"
            hover = "#f9f9f9"

        self.setStyleSheet(f"""
            BookCard {{ background-color: {bg}; border: 1px solid {border}; border-radius: 8px; color: {text}; }}
            BookCard:hover {{ background-color: {hover}; border-color: #bbb; }}
            QLabel {{ color: {text}; }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.b_id)
        super().mousePressEvent(event)

    def show_context(self, pos):
        menu = QMenu()
        delete_action = menu.addAction("Delete Book")
        action = menu.exec(self.mapToGlobal(pos))
        if action == delete_action:
            self.delete_requested.emit(self.b_id)

class LibraryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cozy Library")
        self.resize(800, 600)
        
        self.lib_data = load_library()
        self.is_dark = (self.lib_data.get('theme', 'light') == 'dark')

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # TOP BAR
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(70)
        
        header_layout = QHBoxLayout(self.top_bar)
        header_layout.setContentsMargins(30, 0, 30, 0)
        
        self.lbl_title = QLabel("My Bookshelf")
        self.lbl_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        self.btn_theme = QPushButton("🌙" if not self.is_dark else "☀️")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setFixedSize(40, 40)
        self.btn_theme.clicked.connect(self.toggle_theme)

        self.btn_import = QPushButton("+ Import Book")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setFixedHeight(40)
        self.btn_import.clicked.connect(self.import_book)

        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_theme)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_import)
        
        self.main_layout.addWidget(self.top_bar)

        # SCROLL AREA
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scroll_content = QWidget()
        self.books_layout = QVBoxLayout(self.scroll_content)
        self.books_layout.setContentsMargins(30, 20, 30, 20)
        self.books_layout.setSpacing(15)
        self.books_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

        self.apply_theme()
        self.refresh_list()

    def apply_theme(self):
        if self.is_dark:
            bg_main = "#1e1e1e"
            text = "#ffffff"
            btn_bg = "#3e3e42"
            btn_hover = "#4e4e52"
        else:
            bg_main = "#fdfdfd"
            text = "#000000"
            btn_bg = "#ffffff"
            btn_hover = "#f0f0f0"

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg_main}; color: {text}; }}
            QScrollArea {{ border: none; background-color: {bg_main}; }}
            QPushButton {{
                background-color: {btn_bg}; border: 1px solid #ccc;
                border-radius: 6px; padding: 0 15px; font-weight: bold; color: {text};
            }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
        """)
        
        self.top_bar.setStyleSheet(f"background-color: {bg_main}; border-bottom: 1px solid #333;" if self.is_dark 
                                   else f"background-color: {bg_main}; border-bottom: 1px solid #ddd;")
        
        self.btn_theme.setText("🌙" if not self.is_dark else "☀️")
        self.refresh_list()

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.lib_data = load_library()
        self.lib_data['theme'] = 'dark' if self.is_dark else 'light'
        save_library(self.lib_data)
        self.apply_theme()

    def refresh_list(self):
        while self.books_layout.count():
            child = self.books_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        self.lib_data = load_library()
        books = self.lib_data.get('books', {})
        
        if not books:
            lbl = QLabel("No books yet. Click Import to start reading!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #888; font-size: 16px; margin-top: 50px;")
            self.books_layout.addWidget(lbl)
            return

        for b_id, data in books.items():
            card = BookCard(b_id, data, self.is_dark)
            card.clicked.connect(self.open_book)
            card.delete_requested.connect(self.delete_book)
            self.books_layout.addWidget(card)

    def import_book(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Import', filter="EPUB (*.epub)")
        if fname:
            filename = os.path.basename(fname)
            dest = os.path.join(STORAGE_DIR, filename)
            shutil.copyfile(fname, dest)
            try:
                book = epub.read_epub(dest)
                title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else filename
            except:
                title = filename

            self.lib_data = load_library()
            self.lib_data.setdefault('books', {})[filename] = {
                'title': title, 
                'filename': filename, 
                'last_chapter_index': 0, 
                'last_page_index': 0,
                'progress_percent': 0 
            }
            save_library(self.lib_data)
            self.refresh_list()

    def delete_book(self, book_id):
        self.lib_data = load_library()
        if book_id in self.lib_data['books']:
            filename = self.lib_data['books'][book_id]['filename']
            delete_book_files(filename) 
            del self.lib_data['books'][book_id]            
            save_library(self.lib_data)
            self.refresh_list()

    def open_book(self, book_id):
        books = self.lib_data.get('books', {})
        if book_id in books:
            self.hide()
            self.reader = ReaderWindow(book_id, books[book_id], self.show_library, is_dark=self.is_dark)
            self.reader.show()

    def show_library(self):
        self.lib_data = load_library()
        self.is_dark = (self.lib_data.get('theme', 'light') == 'dark')
        self.apply_theme()
        self.refresh_list()
        self.show()

    def save(self):
        data = self.to_dict()
        dirpath = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(prefix="library-", dir=dirpath, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except: pass