pyinstaller --noconfirm --onefile --windowed --name "DorkyReader" ^
    --add-data "epub_reader;epub_reader" ^
    --hidden-import "PyQt6.QtWebEngineWidgets" ^
    --hidden-import "ebooklib" ^
    main.py