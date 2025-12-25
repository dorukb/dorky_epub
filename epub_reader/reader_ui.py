from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QFrame)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from .ui_components import ThemeToggleButton, BackButton

class InterceptingWebPage(QWebEnginePage):
    """
    Custom WebPage to intercept navigation requests (clicks).
    """
    def __init__(self, parent, handle_link_cb):
        super().__init__(parent)
        self.handle_link_cb = handle_link_cb

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            # CRITICAL FIX: Schedule the handler on the next event loop iteration.
            # Processing navigation logic (which calls setHtml) synchronously inside 
            # this callback causes crashes because the engine is still handling the click.
            QTimer.singleShot(0, lambda: self.handle_link_cb(url))
            return False 
        return True

class ReaderUI:
    def __init__(self, main_window):
        self.main_window = main_window
        
        # Main Layout Components
        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- SIDE PANEL (TOC) ---
        self.side_panel = QWidget()
        self.side_panel.setFixedWidth(200)
        self.side_panel.hide() 
        
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        
        # Header
        self.toc_header = QLabel("Index")
        self.toc_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toc_header.setFixedHeight(60)
        side_layout.addWidget(self.toc_header)
        
        # Chapter List
        self.toc_list = QListWidget()
        self.toc_list.setFrameShape(QFrame.Shape.NoFrame)
        side_layout.addWidget(self.toc_list)
        
        self.main_layout.addWidget(self.side_panel)

        # --- READER CONTENT AREA ---
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.content_container, 1)

        # Top Bar
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(60)
        self._init_top_bar()
        self.content_layout.addWidget(self.top_bar, 0)

        # Web View
        self.web_view = QWebEngineView()
        
        # INSTALL INTERCEPTOR
        self.custom_page = InterceptingWebPage(self.web_view, self.main_window.handle_internal_link)
        self.web_view.setPage(self.custom_page)
        
        self.content_layout.addWidget(self.web_view, 1)

        # Bottom Bar
        self.nav_container = QWidget()
        self.nav_container.setFixedHeight(60)
        self._init_bottom_bar()
        self.content_layout.addWidget(self.nav_container, 0)
        
        self.main_window.setCentralWidget(self.central_widget)

    def _init_top_bar(self):
        layout = QHBoxLayout(self.top_bar)
        layout.setContentsMargins(15, 0, 15, 0)

        self.btn_back = BackButton(False)
        self.btn_back.clicked.connect(self.main_window.go_back_to_library)

        self.btn_toc = QPushButton("☰")
        self.btn_toc.setFixedSize(40, 40)
        self.btn_toc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toc.clicked.connect(self.main_window.toggle_toc_panel)
        self.btn_toc.setStyleSheet("font-size: 20px; border: none; background: transparent;")

        self.btn_theme = ThemeToggleButton(False, size=40)
        self.btn_theme.clicked.connect(self.main_window.toggle_theme)

        layout.addWidget(self.btn_back)
        layout.addSpacing(10)
        layout.addWidget(self.btn_toc)
        layout.addStretch()
        layout.addWidget(self.btn_theme)

    def _init_bottom_bar(self):
        layout = QHBoxLayout(self.nav_container)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.clicked.connect(self.main_window.prev_page)
        self.lbl_progress = QLabel("Loading...")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.main_window.next_page)
        
        layout.addWidget(self.btn_prev)
        layout.addStretch()
        layout.addWidget(self.lbl_progress)
        layout.addStretch()
        layout.addWidget(self.btn_next)

    def apply_theme(self, is_dark):
        if is_dark:
            win_bg = "#1e1e1e"; win_fg = "#e0e0e0"
            bar_bg = "#252526"; bar_border = "#333"
            btn_bg = "#2d2d2d"; btn_fg = "#eee"; btn_hover = "#3e3e42"
            list_bg = "#252526"; list_sel = "#37373d"
            self.web_view.page().setBackgroundColor(QColor("#1e1e1e"))
        else:
            win_bg = "#fdfdfd"; win_fg = "#333"
            bar_bg = "#fff"; bar_border = "#ddd"
            btn_bg = "#fff"; btn_fg = "#333"; btn_hover = "#f5f5f5"
            list_bg = "#f9f9f9"; list_sel = "#e5e5e5"
            self.web_view.page().setBackgroundColor(QColor("#fdfdfd"))

        self.main_window.setStyleSheet(f"background-color: {win_bg}; color: {win_fg};")
        self.top_bar.setStyleSheet(f"background-color: {bar_bg}; border-bottom: 1px solid {bar_border};")
        self.btn_toc.setStyleSheet(f"color: {win_fg}; font-size: 20px; border: none; background: transparent; font-weight: bold;")

        self.side_panel.setStyleSheet(f"background-color: {list_bg}; border-right: 1px solid {bar_border};")
        self.toc_header.setStyleSheet(f"border-bottom: 1px solid {bar_border}; font-weight: bold; color: {win_fg};")
        self.toc_list.setStyleSheet(f"""
            QListWidget {{ background-color: {list_bg}; border: none; outline: none; }}
            QListWidget::item {{ padding: 10px; color: {win_fg}; }}
            QListWidget::item:selected {{ background-color: {list_sel}; color: {win_fg}; }}
            QListWidget::item:hover {{ background-color: {btn_hover}; }}
        """)

        self.nav_container.setStyleSheet(f"""
            QWidget {{ background-color: {bar_bg}; border-top: 1px solid {bar_border}; }}
            QPushButton {{ background-color: {btn_bg}; color: {btn_fg}; border: 1px solid {bar_border}; padding: 6px 20px; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QLabel {{ font-size: 14px; color: {btn_fg}; }}
        """)

        self.btn_back.refresh_style(is_dark)
        self.btn_theme.refresh_icon(is_dark)