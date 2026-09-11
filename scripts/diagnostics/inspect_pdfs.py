from pathlib import Path
import fitz

paths = [
    Path(r'Intereses.pdf'),
    Path(r'Competencias.pdf'),
]

for path in paths:
    print(f'FILE {path.name} exists={path.exists()}')
    if not path.exists():
        continue
    doc = fitz.open(path)
    print(f'pages={doc.page_count}')
    for idx in range(doc.page_count):
        page = doc.load_page(idx)
        text = page.get_text('text')
        # Print a compact digest of page text, so we don't overwhelm output.
        print(f'--- PAGE {idx+1} ---')
        print(text[:2500].replace('\n', ' '))
    print()
