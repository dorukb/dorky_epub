import os
import shutil
import tempfile
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, 
                             QPushButton, QLabel, QApplication)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QUrl, QTimer, QEvent
from ebooklib import epub
from .database import load_library, save_library, STORAGE_DIR
from .utils import extract_images_and_fix_html, prepare_chapter_html
from .ui_components import ThemeToggleButton, BackButton

class ReaderWindow(QMainWindow):
    def __init__(self, book_id, book_data, on_close_callback, is_dark=False):
        super().__init__()
        self.book_id = book_id
        self.book_data = book_data
        self.on_close_callback = on_close_callback
        self.is_dark = is_dark
        self.is_returning_to_library = False
        
        # SAFETY FLAG
        self.is_ready_to_save = False
        
        # Window Setup
        self.setMinimumSize(900, 700) 
        self.resize(1100, 900)
        self.setWindowTitle(f"Reading: {book_data.get('title', 'Book')}")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Bar
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(60)
        self._init_top_bar_ui()
        layout.addWidget(self.top_bar, 0)

        # Web View
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.on_chapter_loaded)
        QApplication.instance().installEventFilter(self)
        layout.addWidget(self.web_view, 1)

        # Bottom Bar
        self.nav_container = QWidget()
        self.nav_container.setFixedHeight(60)
        self._init_bottom_bar_ui()
        layout.addWidget(self.nav_container, 0)

        # --- APPLY THEME (Fixes 1 part of the flash) ---
        self._apply_all_themes()

        # State
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
        fname = book_data.get('filename', book_id)
        full_path = os.path.join(STORAGE_DIR, fname)
        
        self.load_book(full_path)

    def _init_top_bar_ui(self):
        layout = QHBoxLayout(self.top_bar)
        layout.setContentsMargins(15, 0, 15, 0)

        self.btn_back = BackButton(self.is_dark)
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(self.go_back_to_library)

        self.btn_theme = ThemeToggleButton(self.is_dark, size=40)
        self.btn_theme.clicked.connect(self.toggle_theme)

        layout.addWidget(self.btn_back)
        layout.addStretch()
        layout.addWidget(self.btn_theme)

    def _init_bottom_bar_ui(self):
        layout = QHBoxLayout(self.nav_container)
        layout.setContentsMargins(20, 0, 20, 0)
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.clicked.connect(self.prev_page)
        self.lbl_progress = QLabel("Loading...")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_page)
        layout.addWidget(self.btn_prev)
        layout.addStretch()
        layout.addWidget(self.lbl_progress)
        layout.addStretch()
        layout.addWidget(self.btn_next)

    def _apply_all_themes(self):
        """Applies theme to Window, Bars, and the Web Engine Background"""

        if self.is_dark:
            win_bg = "#1e1e1e"; win_fg = "#e0e0e0"
            bar_bg = "#252526"; bar_border = "#333"
            btn_bg = "#2d2d2d"; btn_fg = "#eee"; btn_hover = "#3e3e42"
            
            # CRITICAL FIX 1: Set WebEngine Background to Dark
            self.web_view.page().setBackgroundColor(QColor("#1e1e1e"))
        else:
            win_bg = "#fdfdfd"; win_fg = "#333"
            bar_bg = "#fff"; bar_border = "#ddd"
            btn_bg = "#fff"; btn_fg = "#333"; btn_hover = "#f5f5f5"
            
            # Set WebEngine Background to Light
            self.web_view.page().setBackgroundColor(QColor("#fdfdfd"))
     
        #  The buttons now handle their own internal styling (icons, text color, hover)
        self.btn_back.refresh_style(self.is_dark)
        self.btn_theme.refresh_icon(self.is_dark)
        # Apply Window Style
        self.setStyleSheet(f"background-color: {win_bg}; color: {win_fg};")

        # Top Bar: ONLY style the container (QWidget). Do NOT touch QPushButtons here.
        self.top_bar.setStyleSheet(f"""
            background-color: {bar_bg}; 
            border-bottom: 1px solid {bar_border};
        """)
        
        # Bottom Bar Style
        self.nav_container.setStyleSheet(f"""
            QWidget {{ background-color: {bar_bg}; border-top: 1px solid {bar_border}; }}
            QPushButton {{ background-color: {btn_bg}; color: {btn_fg}; border: 1px solid {bar_border}; padding: 6px 20px; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QLabel {{ font-size: 14px; color: {btn_fg}; }}
        """)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        
        lib = load_library()
        lib['theme'] = 'dark' if self.is_dark else 'light'
        save_library(lib)
        
        self._apply_all_themes()
        
        js = "document.body.classList.add('dark-mode');" if self.is_dark else "document.body.classList.remove('dark-mode');"
        self.web_view.page().runJavaScript(js)

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            
            # Restore
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
            
            # CRITICAL FIX 2: Inject class BEFORE loading
            # This ensures the HTML is dark the millisecond it renders.
            if self.is_dark:
                html = html.replace("<body>", "<body class='dark-mode'>")

            self.web_view.setHtml(html, QUrl.fromLocalFile(self.temp_dir + os.sep))

    def on_chapter_loaded(self, success):
        if not success: return
        
        # We still run this to be safe, though the injection above handles the initial load
        if self.is_dark: self.web_view.page().runJavaScript("document.body.classList.add('dark-mode');")
        else: self.web_view.page().runJavaScript("document.body.classList.remove('dark-mode');")
        
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
            var pages = Math.ceil((totalW - 10) / stride);
            return { pages: pages, stride: stride };
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
        if target == 'end':
            self.current_page_idx = max(0, self.total_pages_in_chapter - 1)
        elif target == 'current':
            self.current_page_idx = max(0, min(self.current_page_idx, self.total_pages_in_chapter - 1))
        else:
            self.current_page_idx = max(0, min(int(target), self.total_pages_in_chapter - 1))
        
        self.is_ready_to_save = True
        self._pending_target_page = 'current'
        self.update_view_position()

    def update_view_position(self):
        target_x = round(self.current_page_idx * self.scroll_stride)
        self.web_view.page().runJavaScript(f"var e=document.getElementById('book-content'); if(e) e.scrollLeft={target_x};")
        self.lbl_progress.setText(f"Chap {self.chapter_idx + 1} • Page {self.current_page_idx + 1} / {self.total_pages_in_chapter}")
        
        # No save here!

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
        """Called ONLY when closing the window/app."""
        if not self.is_ready_to_save: return

        lib = load_library()
        if 'books' in lib and self.book_id in lib['books']:
            book_entry = lib['books'][self.book_id]
            
            book_entry['last_chapter_index'] = self.chapter_idx
            book_entry['last_page_index'] = self.current_page_idx
            
            total_chapters = len(self.spine_order)
            if total_chapters > 0:
                cur_chap = self.chapter_idx / total_chapters
                weight = 1 / total_chapters
                pg_frac = self.current_page_idx / max(1, self.total_pages_in_chapter)
                total_percent = int((cur_chap + (pg_frac * weight)) * 100)
                book_entry['progress_percent'] = min(100, max(0, total_percent))
            
            save_library(lib)

    def go_back_to_library(self):
        self.is_returning_to_library = True
        self.close()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            if event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_J:
                self.prev_page(); return True
            if event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_L:
                self.next_page(); return True
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                 if event.key() in [Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Minus, Qt.Key.Key_0]: return True
        if event.type() == QEvent.Type.Wheel and self.isActiveWindow():
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier: return True
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)
        
    def handle_resize_finished(self):
        self.calculate_layout_geometry()

    def closeEvent(self, event):
        self.save_progress()
        QApplication.instance().removeEventFilter(self)
        if os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except: pass 
            
        if self.is_returning_to_library:
            self.on_close_callback()
        else:
            QApplication.instance().quit()
        event.accept()