import os
import copy
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl

PAGED_CSS = """
<style>
    /* 1. RESET */
    html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        overflow: hidden !important;
        background-color: #fdfdfd;
    }

    /* 2. CONTAINER */
    #book-content {
        height: 100vh !important;
        width: 100vw !important;
        
        /* SCROLLING */
        overflow-x: scroll; 
        overflow-y: hidden;
        
        /* COLUMN MATH: 
           By removing horizontal padding here, 
           Column Width becomes exactly 100vw.
        */
        padding: 60px 0; /* Top/Bottom only */
        box-sizing: border-box;

        column-width: 100vw;
        column-gap: 80px; /* Clean 80px gap */
        column-fill: auto;
        
        /* TEXT */
        font-family: "Georgia", "Cambria", serif;
        font-size: 20px;
        line-height: 1.6;
        color: #2a2a2a;
        text-align: justify;
    }
    
    #book-content::-webkit-scrollbar { display: none; }

    /* 3. CENTERED TEXT BLOCKS */
    /* We create the 'margins' here using max-width */
    p, h1, h2, h3, h4, h5, h6, ul, ol, blockquote, pre {
        /* The cozy reading width */
        width: 700px; 
        
        /* Safety for small screens (mobiles/resizing) */
        max-width: calc(100vw - 80px);
        
        /* Center the block inside the 100vw column */
        margin-left: auto;
        margin-right: auto;
        
        margin-bottom: 1.2em;
    }
    
    h1, h2, h3 { 
        margin-top: 1em; 
        margin-bottom: 0.6em; 
        break-after: avoid; 
        text-align: center;
    }
    
    img {
        max-width: calc(100vw - 80px); /* Ensure image fits */
        max-height: 85vh; 
        display: block;
        margin: 20px auto;
        break-inside: avoid;
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
    style_tag.string = PAGED_CSS.replace("<style>", "").replace("</style>", "")
    new_soup.head.append(style_tag)
    
    content_children = [copy.copy(c) for c in body_content.children]
    for child in content_children:
        new_soup.find(id="book-content").append(child)
        
    return str(new_soup)