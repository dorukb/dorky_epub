import os
import shutil
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl

# Define our "Cozy" visual style
COZY_CSS = """
<style>
    body {
        font-family: "Georgia", "Cambria", serif;
        line-height: 1.6;
        font-size: 18px;
        color: #2b2b2b;
        max-width: 800px; /* Prevents lines from getting too long */
        margin: 0 auto;   /* Centers the text block */
        padding: 40px 20px;
        background-color: #ffffff;
    }
    p {
        margin-bottom: 1.2em;
        text-align: justify;
    }
    img {
        max-width: 100%; /* Shrink to fit, but never stretch larger */
        height: auto;    /* Maintain aspect ratio */
        display: block;
        margin: 20px auto; /* Center images */
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); /* Subtle shadow for polish */
    }
    h1, h2, h3 {
        color: #1a1a1a;
        margin-top: 1.5em;
        font-family: "Helvetica Neue", sans-serif; /* Headers look nice in sans */
    }
</style>
"""

def extract_images_and_fix_html(book, temp_dir):
    """
    1. Extracts all images from the book to temp_dir.
    """
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    for item in book.get_items():
        if item.get_type() == 9: # 9 = Image in EbookLib
            name = os.path.basename(item.file_name)
            file_path = os.path.join(temp_dir, name)
            with open(file_path, 'wb') as f:
                f.write(item.get_content())
    return temp_dir

def prepare_html(html_content, temp_img_dir):
    """
    Parses HTML, injects CSS, and fixes image links.
    """
    soup = BeautifulSoup(html_content, 'xml') 
    
    # 1. Inject Style
    # Check if <head> exists, if not create it
    if not soup.head:
        head_tag = soup.new_tag("head")
        soup.html.insert(0, head_tag)
    
    # Append our custom style
    style_tag = BeautifulSoup(COZY_CSS, 'html.parser')
    soup.head.append(style_tag)

    # 2. Fix Images
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            filename = os.path.basename(src)
            local_path = os.path.join(temp_img_dir, filename)
            img['src'] = QUrl.fromLocalFile(local_path).toString()

    return str(soup)