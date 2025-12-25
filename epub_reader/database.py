import os
import json
import shutil
from ebooklib import epub

# Paths
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PACKAGE_DIR)
STORAGE_DIR = os.path.join(ROOT_DIR, "library_storage")
DB_FILE = os.path.join(ROOT_DIR, "library.json")

# Ensure storage exists
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def load_library():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_library(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_epub_meta(path):
    try:
        book = epub.read_epub(path)
        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else os.path.basename(path)
        return title
    except:
        return os.path.basename(path)

def delete_book_files(filename):
    """Removes the EPUB file from storage"""
    path = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(path):
        os.remove(path)