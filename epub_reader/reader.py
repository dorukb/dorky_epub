import os
import shutil
import tempfile
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
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
        
        self.resize(1000, 800)
        self.setWindowTitle(f"Reading: {book_data['title']}")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Temp directory for this session's images
        self.temp_dir = os.path.join(tempfile.gettempdir(), "epub_reader", book_id)

        # Load Logic
        full_path = os.path.join(STORAGE_DIR, book_data['filename'])
        self.load_book(full_path)

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            self.current_idx = self.book_data.get('last_chapter_index', 0)
            
            # Extract images ONCE when book opens
            extract_images_and_fix_html(self.book, self.temp_dir)
            
            self.render_chapter()
        except Exception as e:
            print(f"Error: {e}")

    def render_chapter(self):
        if not self.book or not self.spine_order: return

        self.current_idx = max(0, min(self.current_idx, len(self.spine_order) - 1))
        item = self.book.get_item_with_id(self.spine_order[self.current_idx])
        
        if item:
            raw_html = item.get_content().decode('utf-8')
            # Fix image links
            final_html = prepare_html(raw_html, self.temp_dir)
            
            # We must pass the baseUrl so the engine allows local file access
            base_url = QUrl.fromLocalFile(self.temp_dir + os.sep)
            self.web_view.setHtml(final_html, base_url)
            
            self.setWindowTitle(f"{self.book_data['title']} (Ch {self.current_idx + 1})")
            self.save_progress()

    def save_progress(self):
        lib = load_library()
        if self.book_id in lib:
            lib[self.book_id]['last_chapter_index'] = self.current_idx
            save_library(lib)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_L:
            self.current_idx += 1
            self.render_chapter()
        elif event.key() == Qt.Key.Key_J:
            self.current_idx -= 1
            self.render_chapter()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Cleanup temp files to save space
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.on_close_callback()
        event.accept()