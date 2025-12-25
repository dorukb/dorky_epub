import os
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl

# PREMIUM PAGE STYLE
COZY_CSS = """
<style>
    body {
        font-family: "Georgia", "Cambria", serif;
        font-size: 21px;
        line-height: 1.8;
        color: #222;            /* Darker gray for better contrast */
        background-color: #fdfdfd;
        
        max-width: 900px;
        margin: 0 auto;
        
        /* HUGE VERTICAL PADDING 
           This creates the "Head" and "Foot" of the page 
        */
        padding: 80px 10%;
        
        overflow-y: hidden;
    }
    
    body::-webkit-scrollbar {
        display: none;
    }

    p {
        margin-bottom: 1.5em;
        text-align: justify;
        text-justify: inter-word;
    }

    h1, h2, h3 {
        font-family: "Helvetica Neue", sans-serif;
        color: #111;
        margin-top: 1.5em;
        margin-bottom: 1.0em;
    }

    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 30px auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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

def prepare_html(html_content, temp_img_dir):
    soup = BeautifulSoup(html_content, 'xml') 
    
    if not soup.head:
        head_tag = soup.new_tag("head")
        soup.html.insert(0, head_tag)
    
    style_tag = BeautifulSoup(COZY_CSS, 'html.parser')
    soup.head.append(style_tag)

    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            filename = os.path.basename(src)
            local_path = os.path.join(temp_img_dir, filename)
            img['src'] = QUrl.fromLocalFile(local_path).toString()

    return str(soup)