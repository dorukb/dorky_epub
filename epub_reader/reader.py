import os
import shutil
import tempfile
from PyQt6.QtWidgets import (QMainWindow, QApplication, QListWidgetItem)
from PyQt6.QtCore import Qt, QUrl, QTimer, QEvent
from PyQt6.QtGui import QCursor
from ebooklib import epub
from .database import load_library, save_library, STORAGE_DIR
from .utils import extract_images_and_fix_html, prepare_chapter_html
from .reader_ui import ReaderUI

class ReaderWindow(QMainWindow):
    def __init__(self, book_id, book_data, on_close_callback, is_dark=False):
        super().__init__()
        self.book_id = book_id
        self.book_data = book_data
        self.on_close_callback = on_close_callback
        self.is_dark = is_dark
        self.is_returning_to_library = False
        self.is_ready_to_save = False
        
        self.setMinimumSize(1200, 900) 
        self.setWindowTitle(f"Reading: {book_data.get('title', 'Book')}")
        
        self.ui = ReaderUI(self)
        
        self.ui.web_view.loadFinished.connect(self.on_chapter_loaded)
        self.ui.toc_list.itemClicked.connect(self.on_toc_chapter_clicked)
        
        QApplication.instance().installEventFilter(self)
        self.ui.web_view.installEventFilter(self)

        self._apply_theme_logic()

        self.book = None
        self.spine_order = [] 
        self.spine_map = {} 
        self.all_html_map = {} 
        self.chapter_idx = 0     
        self.current_page_idx = 0  
        self.total_pages_in_chapter = 1
        self.scroll_stride = 0     
        self._pending_target_page = 0 
        
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(150)
        self.resize_timer.timeout.connect(self.handle_resize_finished)

        self.temp_dir = os.path.join(tempfile.gettempdir(), "epub_reader", book_id)
        fname = book_data.get('filename', book_id)
        full_path = os.path.join(STORAGE_DIR, fname)
        
        self.load_book(full_path)

    def toggle_toc_panel(self):
        if self.ui.side_panel.isVisible():
            self.ui.side_panel.hide()
        else:
            self.ui.side_panel.show()
        self.resize_timer.start()

    def handle_resize_finished(self):
        self.calculate_layout_geometry()

    def handle_internal_link(self, qurl):
        path = qurl.path() 
        filename = os.path.basename(path) 
        anchor = qurl.fragment()
        
        print(f"DEBUG: Link Clicked -> {filename} (Anchor: {anchor})")
        
        if filename in self.spine_map:
            new_idx = self.spine_map[filename]
            
            if new_idx != self.chapter_idx:
                self.chapter_idx = new_idx
                target = f"#{anchor}" if anchor else 0
                self.load_chapter_content(target_page=target)
            elif anchor:
                self.scroll_to_anchor(anchor)

        elif filename in self.all_html_map:
            item_id = self.all_html_map[filename]
            self.load_custom_item(item_id, anchor)
            
        else:
            print(f"DEBUG: Filename '{filename}' NOT found in spine or item maps.")

    def _apply_theme_logic(self):
        self.ui.apply_theme(self.is_dark)
        
        # Check if body exists before accessing classList
        action = "add" if self.is_dark else "remove"
        js = f"if (document && document.body) document.body.classList.{action}('dark-mode');"
        self.ui.web_view.page().runJavaScript(js)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        lib = load_library()
        lib['theme'] = 'dark' if self.is_dark else 'light'
        save_library(lib)
        self._apply_theme_logic()

    def load_book(self, path):
        try:
            self.book = epub.read_epub(path)
            self.spine_order = [x[0] for x in self.book.spine]
            
            self.spine_map = {}
            for idx, item_id in enumerate(self.spine_order):
                item = self.book.get_item_with_id(item_id)
                if item:
                    fname = os.path.basename(item.file_name)
                    self.spine_map[fname] = idx

            self.all_html_map = {}
            for item in self.book.get_items():
                if item.get_type() == 9:
                    fname = os.path.basename(item.file_name)
                    self.all_html_map[fname] = item.get_id()

            self.chapter_idx = self.book_data.get('last_chapter_index', 0)
            saved_page = self.book_data.get('last_page_index', 0)
            
            extract_images_and_fix_html(self.book, self.temp_dir)
            self.populate_toc() 
            self.load_chapter_content(target_page=saved_page)
            
        except Exception as e:
            print(f"Error loading book: {e}")

    def populate_toc(self):
        self.ui.toc_list.clear()
        
        def flatten_toc(toc_list):
            items = []
            for item in toc_list:
                if isinstance(item, (list, tuple)):
                    items.extend(flatten_toc(item))
                elif hasattr(item, 'href') and hasattr(item, 'title'):
                    items.append(item)
            return items

        flat_toc = flatten_toc(self.book.toc)

        if not flat_toc:
            for i in range(len(self.spine_order)):
                self.ui.toc_list.addItem(QListWidgetItem(f"Chapter {i+1}"))
                self.ui.toc_list.item(i).setData(Qt.ItemDataRole.UserRole, i)
            return

        for link in flat_toc:
            href_clean = link.href.split('#')[0]
            fname = os.path.basename(href_clean)
            
            if fname in self.spine_map:
                spine_idx = self.spine_map[fname]
                list_item = QListWidgetItem(link.title)
                list_item.setData(Qt.ItemDataRole.UserRole, spine_idx)
                self.ui.toc_list.addItem(list_item)

        if 0 <= self.chapter_idx < self.ui.toc_list.count():
            self.ui.toc_list.setCurrentRow(self.chapter_idx)

    def on_toc_chapter_clicked(self, item):
        target_idx = item.data(Qt.ItemDataRole.UserRole)
        if target_idx is not None and target_idx != self.chapter_idx:
            self.chapter_idx = target_idx
            self.load_chapter_content(target_page=0)

    def load_chapter_content(self, target_page=0):
        if not self.spine_order: return
        self.chapter_idx = max(0, min(self.chapter_idx, len(self.spine_order) - 1))
        
        for i in range(self.ui.toc_list.count()):
            if self.ui.toc_list.item(i).data(Qt.ItemDataRole.UserRole) == self.chapter_idx:
                self.ui.toc_list.setCurrentRow(i)
                break

        item_id = self.spine_order[self.chapter_idx]
        self.load_custom_item(item_id, target_page)

    def load_custom_item(self, item_id, target_page=0):
        item = self.book.get_item_with_id(item_id)
        if item:
            self._pending_target_page = target_page
            raw = item.get_content().decode('utf-8')
            html = prepare_chapter_html(raw, self.temp_dir)
            
            if self.is_dark:
                html = html.replace("<body>", "<body class='dark-mode'>")

            self.ui.web_view.setHtml(html, QUrl.fromLocalFile(self.temp_dir + os.sep))

    def scroll_to_anchor(self, anchor_id):
        js = f"""
        (function() {{
            var el = document.getElementById('{anchor_id}');
            if (el) {{
                var rect = el.getBoundingClientRect();
                var container = document.getElementById('book-content');
                var totalLeft = container.scrollLeft + rect.left;
                return totalLeft;
            }}
            return -1;
        }})();
        """
        self.ui.web_view.page().runJavaScript(js, self._handle_anchor_result)

    def _handle_anchor_result(self, result):
        if result != -1 and self.scroll_stride > 0:
            page_idx = int(result / self.scroll_stride)
            self.current_page_idx = max(0, min(page_idx, self.total_pages_in_chapter - 1))
            self.update_view_position()

    def on_chapter_loaded(self, success):
        if not success: return
        
        # Safe Theme Application
        action = "add" if self.is_dark else "remove"
        js_theme = f"if (document && document.body) document.body.classList.{action}('dark-mode');"
        self.ui.web_view.page().runJavaScript(js_theme)
        
        js_block = """
        window.addEventListener('wheel', function(e) { if(e.ctrlKey) e.preventDefault(); }, { passive: false });
        window.addEventListener('keydown', function(e) { if (e.ctrlKey && ['+', '-', '=', '0'].includes(e.key)) e.preventDefault(); });
        """
        self.ui.web_view.page().runJavaScript(js_block)
        self.ui.web_view.setZoomFactor(1.0)
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
        self.ui.web_view.page().runJavaScript(js, self._handle_page_count_result)

    def _handle_page_count_result(self, result):
        if isinstance(result, dict):
            self.total_pages_in_chapter = int(result.get('pages', 1))
            self.scroll_stride = float(result.get('stride', 0))
        else:
            self.total_pages_in_chapter = 1
            self.scroll_stride = float(self.ui.web_view.width())
        
        target = self._pending_target_page
        
        if isinstance(target, str) and target.startswith("#"):
            self.is_ready_to_save = True
            self.scroll_to_anchor(target[1:]) 
            self._pending_target_page = 'current'
            return
            
        elif target == 'end':
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
        self.ui.web_view.page().runJavaScript(f"var e=document.getElementById('book-content'); if(e) e.scrollLeft={target_x};")
        self.ui.lbl_progress.setText(f"Chap {self.chapter_idx + 1} • Page {self.current_page_idx + 1} / {self.total_pages_in_chapter}")

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
        if source == self.ui.web_view and event.type() == QEvent.Type.Resize:
            self.resize_timer.start()

        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            if event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_J:
                self.prev_page(); return True
            if event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_L:
                self.next_page(); return True
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                 if event.key() in [Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Minus, Qt.Key.Key_0]: return True
        
        if event.type() == QEvent.Type.Wheel and self.isActiveWindow():
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier: 
                return True # Block zoom

            # Check if mouse is physically over the side panel
            if self.ui.side_panel.isVisible():
                cursor_pos = QCursor.pos()
                local_pos = self.ui.side_panel.mapFromGlobal(cursor_pos)
                if self.ui.side_panel.rect().contains(local_pos):
                    # Mouse is over sidebar, let standard processing happen (scroll the list)
                    return super().eventFilter(source, event)

            delta = event.angleDelta().y()
            if delta > 0: # Scroll Up -> Previous Page
                self.prev_page()
            elif delta < 0: # Scroll Down -> Next Page
                self.next_page()
            return True 
            
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.save_progress()
        QApplication.instance().removeEventFilter(self)
        self.ui.web_view.removeEventFilter(self)
        if os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except: pass 
            
        if self.is_returning_to_library:
            self.on_close_callback()
        else:
            QApplication.instance().quit()
        event.accept()