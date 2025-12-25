import os
import json
import tempfile
from ebooklib import epub
import sys
from pathlib import Path

# Detect if we are running as an EXE (frozen) or script
if getattr(sys, 'frozen', False):
    # We are running as an EXE
    # Save data in: C:\Users\You\Documents\DorkyReader
    ROOT_DIR = os.path.join(Path.home(), "Documents", "DorkyReader")
else:
    # We are running python main.py
    PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(PACKAGE_DIR)
    
STORAGE_DIR = os.path.join(ROOT_DIR, "library_storage")
DB_FILE = os.path.join(ROOT_DIR, "library.json")

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def load_library():
    if not os.path.exists(DB_FILE):
        return {'books': {}, 'theme': 'dark'} # Default structure
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            return data
    except:
        return {'books': {}, 'theme': 'dark'}

def save_library(data):
    dirpath = os.path.dirname(DB_FILE) or "."
    fd, tmp = tempfile.mkstemp(prefix="library-", dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DB_FILE)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

def get_epub_meta(path):
    try:
        book = epub.read_epub(path)
        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else os.path.basename(path)
        return title
    except:
        return os.path.basename(path)

def delete_book_files(filename):
    path = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(path):
        os.remove(path)