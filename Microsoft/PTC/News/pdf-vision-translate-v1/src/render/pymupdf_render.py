import json
import pathlib
import sys

import fitz


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: pymupdf_render.py <input.pdf> <pages-dir> <dpi> <pages.json>')
    source = pathlib.Path(sys.argv[1])
    pages_dir = pathlib.Path(sys.argv[2])
    dpi = int(sys.argv[3])
    pages_json = pathlib.Path(sys.argv[4])
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    result = {'source': str(source), 'dpi': dpi, 'format': 'png', 'renderer': 'pymupdf', 'pages': []}
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = pages_dir / f'page-{index:03d}.png'
        pix.save(image)
        rect = page.rect
        result['pages'].append({
            'page': index,
            'image': str(image),
            'widthPx': pix.width,
            'heightPx': pix.height,
            'widthPt': rect.width,
            'heightPt': rect.height,
            'rotation': page.rotation,
        })
    pages_json.parent.mkdir(parents=True, exist_ok=True)
    pages_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
