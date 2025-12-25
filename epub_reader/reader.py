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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view, 1)

        # Nav Bar
        nav_container = QWidget()
        nav_container.setFixedHeight(60)
        nav_container.setStyleSheet("""
            QWidget { background-color: #ffffff; border-top: 1px solid #e5e5e5; }
            QPushButton {
                background-color: white; color: #333; border: 1px solid #ddd;
                padding: 8px 25px; border-radius: 4px; font-weight: 600; font-size: 14px;
            }
            QPushButton:hover { background-color: #f7f7f7; border-color: #ccc; }
            QLabel { font-size: 14px; color: #888; font-family: "Segoe UI", sans-serif; }
        """)
        
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(30, 10, 30, 10)

        self.btn_prev = QPushButton("Previous")
        self.btn_prev.clicked.connect(self.prev_page)
        
        self.lbl_progress = QLabel("Chapter 1")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_page)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.lbl_progress)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        
        layout.addWidget(nav_container, 0)

        self.temp_dir = os.path.join(tempfile.gettempdir(), "epub_reader", book_id)
        full_path = os.path.join(STORAGE_DIR, book_data['filename'])
        self.load_book(full_path)

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            self.current_idx = self.book_data.get('last_chapter_index', 0)
            extract_images_and_fix_html(self.book, self.temp_dir)
            self.render_chapter()
        except Exception as e:
            print(f"Error: {e}")

    def render_chapter(self, start_at_bottom=False):
        if not self.book or not self.spine_order: return

        self.current_idx = max(0, min(self.current_idx, len(self.spine_order) - 1))
        self.lbl_progress.setText(f"Chapter {self.current_idx + 1} of {len(self.spine_order)}")

        item = self.book.get_item_with_id(self.spine_order[self.current_idx])
        if item:
            raw_html = item.get_content().decode('utf-8')
            final_html = prepare_html(raw_html, self.temp_dir)
            base_url = QUrl.fromLocalFile(self.temp_dir + os.sep)
            
            def load_finished(ok):
                if ok and start_at_bottom:
                    self.web_view.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")
                elif ok:
                    self.web_view.page().runJavaScript("window.scrollTo(0, 0);")
            
            try: self.web_view.loadFinished.disconnect()
            except: pass
            
            self.web_view.loadFinished.connect(load_finished)
            self.web_view.setHtml(final_html, base_url)
            self.save_progress()

    def save_progress(self):
        lib = load_library()
        if self.book_id in lib:
            lib[self.book_id]['last_chapter_index'] = self.current_idx
            save_library(lib)

    # --- SAFETY BUFFER PAGE LOGIC ---
    
    def next_page(self):
        js = """
        (function() {
            var totalHeight = document.body.scrollHeight;
            var currentBottom = window.scrollY + window.innerHeight;
            
            if (currentBottom >= totalHeight - 2) {
                return false; 
            } else {
                // Scroll screen height minus 40px buffer
                // This ensures cut lines appear fully on the next page
                window.scrollBy(0, window.innerHeight - 40);
                return true;
            }
        })();
        """
        self.web_view.page().runJavaScript(js, self._handle_next_page)

    def _handle_next_page(self, scrolled):
        if scrolled is False:
            if self.current_idx < len(self.spine_order) - 1:
                self.current_idx += 1
                self.render_chapter(start_at_bottom=False)

    def prev_page(self):
        js = """
        (function() {
            if (window.scrollY <= 0) {
                return false; 
            } else {
                // Scroll UP by screen height minus 40px
                window.scrollBy(0, -(window.innerHeight - 40));
                return true;
            }
        })();
        """
        self.web_view.page().runJavaScript(js, self._handle_prev_page)

    def _handle_prev_page(self, scrolled):
        if scrolled is False:
            if self.current_idx > 0:
                self.current_idx -= 1
                self.render_chapter(start_at_bottom=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_L:
            self.next_page()
        elif event.key() == Qt.Key.Key_J:
            self.prev_page()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.on_close_callback()
        event.accept()