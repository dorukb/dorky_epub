from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import QSize, QByteArray, Qt
from PyQt6.QtSvg import QSvgRenderer

# --- ICONS ---
MOON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="{color}"/></svg>"""
SUN_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="5" fill="{color}"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="{color}" stroke-width="2" stroke-linecap="round"/></svg>"""
BACK_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 12H3M8 7L3 12L8 17" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
IMPORT_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12H19" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

def create_icon(svg_data, color="#333", size=24):
    colored_svg = svg_data.format(color=color)
    renderer = QSvgRenderer(QByteArray(colored_svg.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class ThemeToggleButton(QPushButton):
    def __init__(self, is_dark=False, size=40, parent=None):
        super().__init__(parent)
        self.btn_size = size
        self.icon_dim = int(size * 0.6)
        
        self.setFixedSize(self.btn_size, self.btn_size)
        self.setIconSize(QSize(self.icon_dim, self.icon_dim))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.refresh_icon(is_dark)

    def refresh_icon(self, is_dark):
        if is_dark:
            self.setIcon(create_icon(SUN_SVG, "#eee", self.icon_dim))
            hover_bg = "rgba(255, 255, 255, 0.1)"
        else:
            self.setIcon(create_icon(MOON_SVG, "#333", self.icon_dim))
            hover_bg = "rgba(0, 0, 0, 0.05)"

        self.setStyleSheet(f"""
            ThemeToggleButton {{
                background: transparent; 
                border: none; 
                border-radius: {self.btn_size // 5}px;
                padding: 0px; margin: 0px; text-align: center;
            }}
            ThemeToggleButton:hover {{
                background-color: {hover_bg};
            }}
        """)

class BackButton(QPushButton):
    def __init__(self, is_dark=False, parent=None):
        super().__init__(" Library", parent) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(24, 24))
        self.refresh_style(is_dark)

    def refresh_style(self, is_dark):
        if is_dark:
            color = "#eee"
            hover_bg = "rgba(255, 255, 255, 0.1)"
        else:
            color = "#333"
            hover_bg = "rgba(0, 0, 0, 0.05)"

        self.setIcon(create_icon(BACK_SVG, color, size=24))

        self.setStyleSheet(f"""
            BackButton {{
                border: none;
                background: transparent;
                color: {color};
                font-weight: bold;
                font-size: 16px; 
                text-align: left;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            BackButton:hover {{
                background-color: {hover_bg};
            }}
        """)

class ImportButton(QPushButton):
    def __init__(self, is_dark=False, parent=None):
        # Added text " Import"
        super().__init__(" Import", parent)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(24, 24))
        self.setToolTip("Import Book")
        
        self.refresh_style(is_dark)

    def refresh_style(self, is_dark):
        if is_dark:
            color = "#eee"
            hover_bg = "rgba(255, 255, 255, 0.1)"
        else:
            color = "#333"
            hover_bg = "rgba(0, 0, 0, 0.05)"

        self.setIcon(create_icon(IMPORT_SVG, color, 24))
        
        # Updated style to match BackButton (text aligned left, padding)
        self.setStyleSheet(f"""
            ImportButton {{
                background: transparent; 
                border: none; 
                color: {color};
                font-weight: bold;
                font-size: 16px;
                text-align: left;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            ImportButton:hover {{
                background-color: {hover_bg};
            }}
        """)