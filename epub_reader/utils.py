import os
import shutil
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl

def extract_images_and_fix_html(book, temp_dir):
    """
    1. Extracts all images from the book to temp_dir.
    2. Rewrites HTML src tags to point to these local files.
    """
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # 1. Extract Images
    # We map the internal filename (images/cover.jpg) to the actual item
    for item in book.get_items():
        if item.get_type() == 9: # 9 = Image in EbookLib
            # Normalized name
            name = os.path.basename(item.file_name)
            file_path = os.path.join(temp_dir, name)
            with open(file_path, 'wb') as f:
                f.write(item.get_content())

    return temp_dir

def prepare_html(html_content, temp_img_dir):
    """
    Parses HTML, finds <img> tags, and points them to the extracted files.
    """
    soup = BeautifulSoup(html_content, 'xml')
    
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # We just take the filename and assume it's in our flat temp dir
            filename = os.path.basename(src)
            local_path = os.path.join(temp_img_dir, filename)
            # WebEngine needs file:/// paths for local resources
            img['src'] = QUrl.fromLocalFile(local_path).toString()
            # Note: We need QUrl imported here or handle string manually
            # Let's do string manually to keep utils pure python if possible
            # or strictly formatted:
            img['src'] = f"file:///{local_path.replace(os.sep, '/')}"

    return str(soup)