import os
import shutil
import tempfile
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, 
                             QPushButton, QLabel)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl
from ebooklib import epub
from .database import load_library, save_library, STORAGE_DIR
from .utils import extract_images_and_fix_html, prepare_html

class ReaderWindow(QMainWindow):
    def __init__(self, book_id, book_data, on_close_callback):
        super().__init__()
        self.book_id = book_id
        self.book_data = book_data
        self.on_close_callback = on_close_callback
        
        self.resize(1100, 900)
        self.setWindowTitle(f"Reading: {book_data['title']}")

        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. The Web View (Reader)
        self.web_view = QWebEngineView()
        # Add the web view with a stretch factor of 1. 
        # This makes it expand to fill all available space.
        layout.addWidget(self.web_view, 1)

        # 2. Bottom Navigation Bar
        nav_container = QWidget()
        # Force the nav bar to be a reasonable height (e.g., 50px)
        nav_container.setFixedHeight(50)
        
        nav_container.setStyleSheet("""
            QWidget { background-color: #f0f0f0; border-top: 1px solid #ccc; }
            QPushButton {
                background-color: #0078d7; color: white; border: none;
                padding: 5px 15px; border-radius: 4px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:disabled { background-color: #cccccc; }
            QLabel { font-size: 13px; color: #333; font-family: sans-serif; }
        """)
        
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(15, 5, 15, 5) # Tight margins

        self.btn_prev = QPushButton("← Previous")
        self.btn_prev.clicked.connect(self.prev_chapter)
        
        self.lbl_progress = QLabel("Chapter 1")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progress.setStyleSheet("border: none; background: transparent;") # Fix label bg
        
        self.btn_next = QPushButton("Next →")
        self.btn_next.clicked.connect(self.next_chapter)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch() # Spacer
        nav_layout.addWidget(self.lbl_progress)
        nav_layout.addStretch() # Spacer
        nav_layout.addWidget(self.btn_next)
        
        # Add nav container with stretch factor 0 (it won't expand)
        layout.addWidget(nav_container, 0)

        # Load Book Logic
        self.temp_dir = os.path.join(tempfile.gettempdir(), "epub_reader", book_id)
        full_path = os.path.join(STORAGE_DIR, book_data['filename'])
        self.load_book(full_path)

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            self.current_idx = self.book_data.get('last_chapter_index', 0)
            
            # Extract images ONCE
            extract_images_and_fix_html(self.book, self.temp_dir)
            
            self.render_chapter()
        except Exception as e:
            print(f"Error: {e}")

    def render_chapter(self):
        if not self.book or not self.spine_order: return

        self.current_idx = max(0, min(self.current_idx, len(self.spine_order) - 1))
        
        self.btn_prev.setEnabled(self.current_idx > 0)
        self.btn_next.setEnabled(self.current_idx < len(self.spine_order) - 1)
        self.lbl_progress.setText(f"Chapter {self.current_idx + 1} / {len(self.spine_order)}")

        item_id = self.spine_order[self.current_idx]
        item = self.book.get_item_with_id(item_id)
        
        if item:
            raw_html = item.get_content().decode('utf-8')
            final_html = prepare_html(raw_html, self.temp_dir)
            base_url = QUrl.fromLocalFile(self.temp_dir + os.sep)
            self.web_view.setHtml(final_html, base_url)
            self.save_progress()

    def save_progress(self):
        lib = load_library()
        if self.book_id in lib:
            lib[self.book_id]['last_chapter_index'] = self.current_idx
            save_library(lib)

    def next_chapter(self):
        if self.current_idx < len(self.spine_order) - 1:
            self.current_idx += 1
            self.render_chapter()

    def prev_chapter(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.render_chapter()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_L:
            self.next_chapter()
        elif event.key() == Qt.Key.Key_J:
            self.prev_chapter()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.on_close_callback()
        event.accept()