# Dorky EPUB Reader

A lightweight, local EPUB reader built with Python and PyQt6. This application allows you to import books into a local library, renders complex layouts (including images), and automatically saves your reading progress.\

## Installation

### Prerequisites
* Python 3.8+
* see requirements.txt

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd dorky_epub
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application:**
    ```bash
    python main.py
    ```

2.  **Library Window:**
    * Click **Import Book** to select an `.epub` file from your computer.
    * Double-click a book title to start reading.
    * Right-click a book to **Delete** it.

3.  **Reader Controls:**
    | Key | Action |
    | :--- | :--- |
    | **L** | Next Chapter |
    | **J** | Previous Chapter |
    | **+ / -** | Zoom In / Out |
    | **Resize** | Drag window edges to reflow text |

## Project Structure

The application is structured as a Python package:

```text
dorky_epub/
├── library.json           # Stores metadata and reading progress
├── library_storage/       # Local copies of your imported EPUB files
├── main.py                # Application entry point
├── epub_reader/           # Source Code Package
│   ├── database.py        # JSON & File I/O logic
│   ├── library.py         # Main Library Window (GUI)
│   ├── reader.py          # Reader Window (GUI) & Nav logic
│   └── utils.py           # Image extraction & HTML patching
