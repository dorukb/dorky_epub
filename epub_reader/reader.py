import os
import shutil
import tempfile
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, 
                             QPushButton, QLabel, QApplication)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, QTimer, QEvent
from ebooklib import epub
from .database import load_library, save_library, STORAGE_DIR
from .utils import extract_images_and_fix_html, prepare_chapter_html

class ReaderWindow(QMainWindow):
    def __init__(self, book_id, book_data, on_close_callback):
        super().__init__()
        self.book_id = book_id
        self.book_data = book_data
        self.on_close_callback = on_close_callback
        
        # FLAG: Distinguish between "Back to Lib" and "Quit App"
        self.is_returning_to_library = False
        
        self.setMinimumSize(900, 700) 
        self.resize(1100, 900)
        self.setWindowTitle(f"Reading: {book_data['title']}")

        central = QWidget()
        self.setCentralWidget(central)
        
        # MAIN LAYOUT (Vertical)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 1. TOP BAR (Library Button) ---
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("""
            QWidget { background-color: #fff; border-bottom: 1px solid #eee; }
            QPushButton {
                border: none; color: #555; font-weight: bold; font-size: 14px;
                padding: 5px 15px; text-align: left;
            }
            QPushButton:hover { color: #000; background-color: #f5f5f5; border-radius: 4px; }
        """)
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 0, 10, 0)
        
        self.btn_back = QPushButton("← Back")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.go_back_to_library)
        
        top_layout.addWidget(self.btn_back)
        top_layout.addStretch() # Push button to the left
        
        layout.addWidget(top_bar, 0)

        # --- 2. WEB VIEW (Middle) ---
        self.web_view = QWebEngineView()
        self.web_view.setZoomFactor(1.0)
        self.web_view.loadFinished.connect(self.on_chapter_loaded)
        
        # Nuclear Option: Global Event Filter
        QApplication.instance().installEventFilter(self)
        
        layout.addWidget(self.web_view, 1)

        # --- 3. BOTTOM BAR (Navigation) ---
        nav_container = QWidget()
        nav_container.setFixedHeight(60)
        nav_container.setStyleSheet("""
            QWidget { background-color: #fff; border-top: 1px solid #ddd; }
            QPushButton {
                background-color: #fff; color: #333; border: 1px solid #ccc;
                padding: 6px 20px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #f5f5f5; }
            QLabel { font-size: 14px; color: #666; }
        """)
        
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.clicked.connect(self.prev_page)
        
        self.lbl_progress = QLabel("Loading...")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_page)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.lbl_progress)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        
        layout.addWidget(nav_container, 0)

        # --- STATE ---
        self.book = None
        self.spine_order = []
        self.chapter_idx = 0     
        self.current_page_idx = 0  
        self.total_pages_in_chapter = 1
        self.scroll_stride = 0     
        self._pending_target_page = 0 
        
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(100)
        self.resize_timer.timeout.connect(self.handle_resize_finished)

        self.temp_dir = os.path.join(tempfile.gettempdir(), "epub_reader", book_id)
        full_path = os.path.join(STORAGE_DIR, book_data['filename'])
        self.load_book(full_path)

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            self.chapter_idx = self.book_data.get('last_chapter_index', 0)
            saved_page = self.book_data.get('last_page_index', 0)
            extract_images_and_fix_html(self.book, self.temp_dir)
            self.load_chapter_content(target_page=saved_page)
        except Exception as e:
            print(f"Error loading book: {e}")

    def load_chapter_content(self, target_page=0):
        if not self.spine_order: return
        self.chapter_idx = max(0, min(self.chapter_idx, len(self.spine_order) - 1))
        item = self.book.get_item_with_id(self.spine_order[self.chapter_idx])
        if item:
            self._pending_target_page = target_page
            raw = item.get_content().decode('utf-8')
            html = prepare_chapter_html(raw, self.temp_dir)
            self.web_view.setHtml(html, QUrl.fromLocalFile(self.temp_dir + os.sep))

    def on_chapter_loaded(self, success):
        if not success: return
        js_block = """
        window.addEventListener('wheel', function(e) { if(e.ctrlKey) e.preventDefault(); }, { passive: false });
        window.addEventListener('keydown', function(e) { if (e.ctrlKey && ['+', '-', '=', '0'].includes(e.key)) e.preventDefault(); });
        """
        self.web_view.page().runJavaScript(js_block)
        self.web_view.setZoomFactor(1.0)
        self.calculate_layout_geometry()

    def calculate_layout_geometry(self):
        js = """(function() {
            var elem = document.getElementById('book-content');
            if (!elem) return {pages: 1, stride: 0};
            var totalW = elem.scrollWidth;
            var winW = window.innerWidth;
            var gap = parseFloat(window.getComputedStyle(elem).columnGap) || 0;
            var stride = winW + gap; if (stride < 100) stride = winW;
            return { pages: Math.ceil(totalW / stride), stride: stride };
        })();"""
        self.web_view.page().runJavaScript(js, self._handle_page_count_result)

    def _handle_page_count_result(self, result):
        if isinstance(result, dict):
            self.total_pages_in_chapter = int(result.get('pages', 1))
            self.scroll_stride = float(result.get('stride', 0))
        else:
            self.total_pages_in_chapter = 1
            self.scroll_stride = float(self.web_view.width())
        
        target = self._pending_target_page
        if target == 'end': self.current_page_idx = max(0, self.total_pages_in_chapter - 1)
        elif target == 'current': self.current_page_idx = max(0, min(self.current_page_idx, self.total_pages_in_chapter - 1))
        else: self.current_page_idx = max(0, min(int(target), self.total_pages_in_chapter - 1))
        self._pending_target_page = 'current'
        self.update_view_position()

    def update_view_position(self):
        target_x = self.current_page_idx * self.scroll_stride
        self.web_view.page().runJavaScript(f"var e=document.getElementById('book-content'); if(e) e.scrollLeft={target_x};")
        self.lbl_progress.setText(f"Chap {self.chapter_idx + 1} • Page {self.current_page_idx + 1} / {self.total_pages_in_chapter}")
        self.save_progress()

    def next_page(self):
        if self.current_page_idx < self.total_pages_in_chapter - 1:
            self.current_page_idx += 1
            self.update_view_position()
        elif self.chapter_idx < len(self.spine_order) - 1:
            self.chapter_idx += 1
            self.load_chapter_content(target_page=0)

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.update_view_position()
        elif self.chapter_idx > 0:
            self.chapter_idx -= 1
            self.load_chapter_content(target_page='end')

    def save_progress(self):
        lib = load_library()
        if self.book_id in lib:
            lib[self.book_id]['last_chapter_index'] = self.chapter_idx
            lib[self.book_id]['last_page_index'] = self.current_page_idx
            save_library(lib)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            if event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_J:
                self.prev_page()
                return True
            if event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_L:
                self.next_page()
                return True
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                 if event.key() in [Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Minus, Qt.Key.Key_0]:
                    return True
        if event.type() == QEvent.Type.Wheel and self.isActiveWindow():
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                return True
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)
        
    def handle_resize_finished(self):
        self._pending_target_page = 'current'
        self.calculate_layout_geometry()

    
    def go_back_to_library(self):
        """User explicitly clicked Back. We want to show the library."""
        self.is_returning_to_library = True
        self.close()

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        if os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except: pass 
        
        if self.is_returning_to_library:
            self.on_close_callback()
        else:
            # User clicked "X" or Alt+F4 -> Kill the whole app
            # (Because the library is currently just hidden, we must force quit)
            QApplication.instance().quit()
            
        event.accept()