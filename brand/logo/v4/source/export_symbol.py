"""명함 뒷면 워터마크 심볼(심볼 A, 1.5배 굵기)을 따로 내보냅니다.

    python3 brand/logo/v4/source/export_symbol.py

brand/logo/v4/symbol/ 에 색상별 SVG, 투명 배경 PNG(2000px), 인쇄용 PDF(높이 100mm)를 만듭니다.
"""
import json
import os
import subprocess

import generate as g

OUT = os.path.join(g.OUT, 'symbol')
GRAY = '#88887A'          # 검정 바탕 위 크림 50%를 단색으로 (명함 뒷면과 같은 색)

# 이름 뒤에 붙는 말, 색, 투명도
VARIANTS = [
    ('black', g.BLACK, None),
    ('cream', g.CREAM, None),
    ('gray', GRAY, None),
    ('cream-50', g.CREAM, 0.5),
    ('black-50', g.BLACK, 0.5),
]
PNG_H = 2000
PDF_H_MM = 100.0


def main():
    if not os.path.exists(g.NOTO):
        g.main()
    os.makedirs(OUT, exist_ok=True)
    build = f'{g.HERE}/.build'
    os.makedirs(build, exist_ok=True)
    sym = g.normalise(g.symbol_watermark(), 200)
    jobs = []
    for suffix, fill, opacity in VARIANTS:
        name = f'bellink-symbol-watermark-{suffix}'
        svg, w, h = g.svg_doc([sym], fill, opacity=opacity)
        with open(f'{OUT}/{name}.svg', 'w') as f:
            f.write(svg)
        pw = round(w * PNG_H / h)
        html = f'{build}/{name}.html'
        with open(html, 'w') as f:
            f.write(f'<html><body style="margin:0"><img src="file://{OUT}/{name}.svg" style="display:block;width:{pw}px;height:{PNG_H}px"></body></html>')
        jobs.append({'html': html, 'out': f'{OUT}/{name}.png', 'w': pw, 'h': PNG_H, 'transparent': True})
        if opacity is None and suffix != 'gray':
            wmm = w * PDF_H_MM / h
            phtml = f'{build}/{name}-pdf.html'
            with open(phtml, 'w') as f:
                f.write(f'<html><head><style>@page {{ size: {wmm:.3f}mm {PDF_H_MM:g}mm; margin: 0; }} * {{ margin: 0; }}</style></head>'
                        f'<body><img src="file://{OUT}/{name}.svg" style="display:block;width:{wmm:.3f}mm;height:{PDF_H_MM:g}mm"></body></html>')
            jobs.append({'html': phtml, 'w': pw, 'h': PNG_H, 'pdf': f'{OUT}/{name}.pdf',
                         'pdfw': f'{wmm:.3f}mm', 'pdfh': f'{PDF_H_MM:g}mm'})
    with open(f'{build}/symbol-jobs.json', 'w') as f:
        json.dump(jobs, f)
    subprocess.run(['node', f'{g.HERE}/render.js', f'{build}/symbol-jobs.json'], check=True)
    for j in jobs:
        if 'pdf' in j:
            exact_page(j['pdf'], float(j['pdfw'][:-2]), float(j['pdfh'][:-2]))
    print(OUT)


def exact_page(path, wmm, hmm):
    """Chromium이 반올림한 PDF 쪽 크기를 정확한 mm 값으로 맞춥니다."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import RectangleObject
    except ImportError:
        return
    pt = 72 / 25.4
    reader, writer = PdfReader(path), PdfWriter()
    for page in reader.pages:
        top = float(page.mediabox.top)
        page.mediabox = page.cropbox = RectangleObject([0, top - hmm * pt, wmm * pt, top])
        writer.add_page(page)
    with open(path, 'wb') as f:
        writer.write(f)


if __name__ == '__main__':
    main()
