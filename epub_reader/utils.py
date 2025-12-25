import os
import copy
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl

# --- THEME CSS ---
# We use CSS variables so we can switch themes instantly
THEME_CSS = """
<style>
    :root {
        --bg-color: #fdfdfd;
        --text-color: #2a2a2a;
        --link-color: #0056b3;
        --img-opacity: 1.0;
    }
    
    /* DARK MODE CLASS */
    body.dark-mode {
        --bg-color: #1a1a1a;
        --text-color: #e0e0e0;
        --link-color: #64b5f6;
        --img-opacity: 0.85; /* Slightly dim images in dark mode */
    }

    html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        overflow: hidden !important;
        background-color: var(--bg-color); /* USE VAR */
        transition: background-color 0.3s ease, color 0.3s ease;
    }

    #book-content {
        height: 100vh !important;
        width: 100vw !important;
        overflow-x: scroll; 
        overflow-y: hidden;
        padding: 60px 0;
        box-sizing: border-box;

        column-width: 100vw;
        column-gap: 80px;
        column-fill: auto;
        
        font-family: "Georgia", "Cambria", serif;
        font-size: 20px;
        line-height: 1.6;
        color: var(--text-color); /* USE VAR */
        text-align: justify;
    }
    
    #book-content::-webkit-scrollbar { display: none; }

    p, h1, h2, h3, h4, h5, h6, ul, ol, blockquote, pre {
        width: 700px;
        max-width: calc(100vw - 80px);
        margin-left: auto;
        margin-right: auto;
        margin-bottom: 1.2em;
    }
    
    h1, h2, h3 { 
        margin-top: 1em; margin-bottom: 0.6em; 
        break-after: avoid; text-align: center;
    }
    
    img {
        max-width: calc(100vw - 80px);
        max-height: 85vh; 
        display: block;
        margin: 20px auto;
        break-inside: avoid;
        opacity: var(--img-opacity);
    }
    
    a {
        color: var(--link-color);
        text-decoration: none;
    }
</style>
"""

def extract_images_and_fix_html(book, temp_dir):
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    for item in book.get_items():
        if item.get_type() == 9: 
            name = os.path.basename(item.file_name)
            file_path = os.path.join(temp_dir, name)
            with open(file_path, 'wb') as f:
                f.write(item.get_content())
    return temp_dir

def prepare_chapter_html(raw_html, temp_img_dir):
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    body_content = soup.body
    if not body_content:
        body_content = soup
        
    for img in body_content.find_all('img'):
        src = img.get('src')
        if src:
            fname = os.path.basename(src)
            local = os.path.join(temp_img_dir, fname)
            img['src'] = QUrl.fromLocalFile(local).toString()

    new_soup = BeautifulSoup("<html><head></head><body><div id='book-content'></div></body></html>", 'xml')
    
    style_tag = new_soup.new_tag("style")
    style_tag.string = THEME_CSS.replace("<style>", "").replace("</style>", "")
    new_soup.head.append(style_tag)
    
    content_children = [copy.copy(c) for c in body_content.children]
    for child in content_children:
        new_soup.find(id="book-content").append(child)
        
    return str(new_soup)