"""BELLINK 명함 (90 x 50 mm, 앞뒤).

    python3 brand/logo/v4/source/business_card.py [정보.json] [출력 폴더]

- 앞면: BELLINK 워드마크 + 그 아래 작은 글씨로 사업 분야
- 뒷면: 워드마크, 이름, 아이콘을 붙인 연락처(전화, 이메일, 인스타그램, 주소), 오른쪽에 크게 깔린 심볼 A(1.5배 굵기, 투명도 50%를 단색으로 환산)
- 명함의 워드마크는 로고 원본(굵기 600, 자간 -0.02em)보다 조금 굵고(680) 자간이 넓습니다(0em).
- 모든 글자는 윤곽선(패스)으로 바꿔 넣어 인쇄소에 폰트가 없어도 그대로 나옵니다.
- 인쇄용 PDF는 재단 여유 1mm씩을 더한 92 x 52 mm 두 쪽(앞, 뒤)입니다.

정보 파일을 주지 않으면 card-info.example.json(예시 정보)으로 만듭니다.
실제 연락처가 담긴 정보 파일과 결과물은 저장소에 올리지 마세요(card-info.json은 .gitignore에 있습니다).
"""
import json
import math
import os
import subprocess
import sys

import pathops
import uharfbuzz as hb
from fontTools.pens.transformPen import TransformPen

import generate as g

HERE = os.path.dirname(os.path.abspath(__file__))
BLACK, CREAM = g.BLACK, g.CREAM
WATER = '#88887A'           # 검정 위 크림 50% (인쇄에서 투명도 대신 단색으로)
MUTED = '#A9A796'           # 보조 글자
W, H, BLEED = 90.0, 50.0, 1.0

_face = hb.Face(hb.Blob.from_file_path(g.NOTO))
_fonts = {}


def text_path(text, size, wght=400, tracking=0.0):
    """Noto Sans KR로 조판한 글자 윤곽선. 왼쪽 x=0, 기준선 y=0. tracking은 글자 사이에 더할 mm."""
    if wght not in _fonts:
        f = hb.Font(_face)
        f.set_variations({'wght': wght})
        _fonts[wght] = f
    font = _fonts[wght]
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True})
    s = size / _face.upem
    out, x = pathops.Path(), 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        gp = pathops.Path()
        font.draw_glyph_with_pen(info.codepoint, TransformPen(gp.getPen(), (s, 0, 0, -s, x, 0)))
        out.addPath(gp)
        x += pos.x_advance * s + tracking
    out.simplify()
    return out


# ------------------------------------------------------------------- icons ---
# 10 x 10 칸에 그린 선 아이콘. 선 굵기 1.1칸(아이콘 2.1mm일 때 약 0.23mm).
ICON_T = 1.1


def _round_rect(x0, y0, x1, y1, r):
    p = pathops.Path()
    p.moveTo(x0 + r, y0)
    p.lineTo(x1 - r, y0)
    g._arc(p, x1 - r, y0 + r, r, -math.pi / 2, 0)
    p.lineTo(x1, y1 - r)
    g._arc(p, x1 - r, y1 - r, r, 0, math.pi / 2)
    p.lineTo(x0 + r, y1)
    g._arc(p, x0 + r, y1 - r, r, math.pi / 2, math.pi)
    p.lineTo(x0, y0 + r)
    g._arc(p, x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    p.close()
    return p


def _dot(cx, cy, r):
    return g.circle(cx, cy, r)


def icon_phone():
    return g.union(g.stroke(_round_rect(2.5, 0.6, 7.5, 9.4, 1.3), ICON_T), _dot(5, 7.6, 0.6))


def icon_email():
    v = g.line((1.0, 2.7), (5, 5.9), (9.0, 2.7))
    return g.union(g.stroke(_round_rect(0.6, 1.7, 9.4, 8.3, 1.1), ICON_T), g.stroke(v, ICON_T))


def icon_instagram():
    return g.union(g.stroke(_round_rect(0.8, 0.8, 9.2, 9.2, 2.6), ICON_T),
                   g.stroke(g.circle(5, 5, 2.0), ICON_T), _dot(7.2, 2.8, 0.6))


def icon_address():
    cx, cy, r, tip = 5.0, 3.9, 3.2, 9.5
    a = math.acos(r / (tip - cy))
    p = pathops.Path()
    p.moveTo(cx, tip)
    p.lineTo(cx + r * math.cos(math.pi / 2 - a), cy + r * math.sin(math.pi / 2 - a))
    g._arc(p, cx, cy, r, math.pi / 2 - a, -1.5 * math.pi + a)
    p.close()
    return g.union(g.stroke(p, ICON_T), g.stroke(g.circle(cx, cy, 1.15), ICON_T))


ICONS = {'phone': icon_phone, 'email': icon_email, 'instagram': icon_instagram, 'address': icon_address}


def ink_width(p):
    return p.bounds[2] - p.bounds[0]


def at(p, x, y, s=1.0):
    """윤곽선 p를 왼쪽 끝이 x, 기준선이 y에 오도록 옮김."""
    return g.move(p, x - p.bounds[0] * s, y, s)


WM_WGHT = 680              # 명함의 워드마크는 로고 원본(600)보다 조금 굵게
WM_TRACK = 0.0             # 자간도 로고 원본(-0.02em)보다 조금 넓게


def wordmark(width):
    """width는 로고 원본 자간 기준의 폭. 자간을 넓힌 만큼 실제 폭은 조금 늘어납니다."""
    s = width / g.wordmark(wght=WM_WGHT).bounds[2]
    wm = g.wordmark(wght=WM_WGHT, tracking=WM_TRACK)
    return wm, s, -wm.bounds[1] * s          # 윤곽선, 배율, 대문자 높이(mm)


FRONT_W = 56.0             # 앞면 워드마크 폭 (mm)
OPTICAL = 0.6              # 앞면: 정가운데보다 살짝 위가 눈에는 가운데로 보입니다 (mm)

# 뒷면 배치 (mm): 왼쪽 여백, 워드마크 윗선까지의 위 여백, 마지막 연락처 기준선까지의 아래 여백
LEFT, TOP, BOTTOM = 8.0, 8.5, 5.4
WATER_D, WATER_CX, WATER_CY = 50.0, 75.5, 32.0   # 워터마크 지름과 중심: 오른쪽 21%, 아래 14% 정도가 잘림


def front(info):
    items = []
    wm, s, cap = wordmark(FRONT_W)
    wm_w = wm.bounds[2] * s
    sub = info['services']
    size = 2.3
    plain = text_path(sub, size, 500)
    n = len(sub)
    track = (wm_w - ink_width(plain)) / (n - 1)
    line = text_path(sub, size, 500, track)
    sub_cap = -line.bounds[1]
    gap = 4.4
    top = H / 2 - (cap + gap + sub_cap) / 2 - OPTICAL
    items.append((at(wm, (W - wm_w) / 2, top + cap, s), CREAM))
    items.append((at(line, (W - ink_width(line)) / 2, top + cap + gap + sub_cap), MUTED))
    return items


def back(info):
    items = []
    sym = g.symbol_watermark()
    x0, y0, x1, y1 = sym.bounds
    k = WATER_D / (y1 - y0)
    items.append((g.move(sym, WATER_CX - (x0 + x1) / 2 * k, WATER_CY - (y0 + y1) / 2 * k, k), WATER))

    left = LEFT
    wm, s, cap = wordmark(37.0)
    items.append((at(wm, left, TOP + cap, s), CREAM))

    # 연락처 줄 수와 상관없이 마지막 줄이 같은 높이에 오도록 아래에서부터 쌓습니다
    step = 3.25
    first = H - BOTTOM - (len(info['contacts']) - 1) * step
    name = text_path(info['name'], 4.4, 600)
    items.append((at(name, left, first - 9.6), CREAM))
    title = text_path(info['title'], 2.6, 400)
    items.append((at(title, left + ink_width(name) + 2.2, first - 9.6), MUTED))
    items.append((at(text_path(info['name_en'], 2.1, 500, 0.32), left, first - 5.4), MUTED))

    # 연락처: 아이콘(phone, email, instagram, address) 또는 글자 표시 + 내용
    size = 2.1
    for i, (kind, value) in enumerate(info['contacts']):
        y = first + i * step
        if kind in ICONS:
            items.append((g.move(ICONS[kind](), left, y - 0.8 - size / 2, size / 10), MUTED))
        else:
            items.append((at(text_path(kind, 2.1, 600), left, y), MUTED))
        items.append((at(text_path(value, 2.2, 400), left + 3.5, y), CREAM))
    return items


def svg(items, bleed, bg=BLACK):
    b = BLEED if bleed else 0.0
    vb = f'{-b:g} {-b:g} {W + 2 * b:g} {H + 2 * b:g}'
    body = ''.join(f'<path fill="{c}" d="{g.to_d(p)}"/>' for p, c in items)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="100%" height="100%">'
            f'<rect x="{-b - 1:g}" y="{-b - 1:g}" width="{W + 2 * b + 2:g}" height="{H + 2 * b + 2:g}" fill="{bg}"/>{body}</svg>')


def fix_pdf_boxes(path):
    """Chromium이 반올림한 쪽 크기를 정확히 92 x 52 mm로 맞추고, 재단선(TrimBox 90 x 50 mm)을 적어 둡니다."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import RectangleObject
    except ImportError:
        return
    pt = 72 / 25.4
    reader, writer = PdfReader(path), PdfWriter()
    for page in reader.pages:
        top = float(page.mediabox.top)
        box = RectangleObject([0, top - (H + 2 * BLEED) * pt, (W + 2 * BLEED) * pt, top])
        page.mediabox = page.cropbox = page.bleedbox = box
        page.trimbox = RectangleObject([BLEED * pt, top - (H + BLEED) * pt, (W + BLEED) * pt, top - BLEED * pt])
        writer.add_page(page)
    with open(path, 'wb') as f:
        writer.write(f)


def main():
    info_path = sys.argv[1] if len(sys.argv) > 1 else f'{HERE}/card-info.example.json'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(HERE), 'business-card')
    with open(info_path, encoding='utf-8') as f:
        info = json.load(f)
    if not os.path.exists(g.NOTO):
        g.main()                          # 폰트 내려받기와 로고 파일 생성
    render_cards({'front': front(info), 'back': back(info)}, out)


def render_cards(sides, out, name='bellink-business-card', bg=BLACK):
    """앞뒤 윤곽선 목록으로 인쇄용 PDF, 300dpi 앞·뒷면 PNG, 나란히 놓은 미리보기 PNG를 만듭니다."""
    os.makedirs(out, exist_ok=True)
    build = f'{HERE}/.build'
    os.makedirs(build, exist_ok=True)

    # 인쇄용 PDF: 92 x 52 mm 두 쪽
    pages = ''.join(f'<div class="page">{svg(sides[k], True, bg)}</div>' for k in ('front', 'back'))
    with open(f'{build}/card-print.html', 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html><head><meta charset="utf-8"><style>'
                f'@page {{ size: {W + 2 * BLEED:g}mm {H + 2 * BLEED:g}mm; margin: 0; }}'
                '* { margin: 0; } body { background: ' + bg + '; } .page { width: 92mm; height: 52mm; break-after: page; overflow: hidden; }'
                '.page svg { display: block; }'
                f'</style></head><body>{pages}</body></html>')

    # 미리보기 PNG: 재단선 기준 90 x 50 mm, 300dpi
    px = round(W / 25.4 * 300)
    py = round(H / 25.4 * 300)
    prev = ''.join(f'<div class="page">{svg(sides[k], False, bg)}</div>' for k in ('front', 'back'))
    with open(f'{build}/card-preview.html', 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html><head><meta charset="utf-8"><style>'
                f'* {{ margin: 0; }} .page {{ width: {px}px; height: {py}px; }} .page svg {{ display: block; }}'
                f'</style></head><body>{prev}</body></html>')

    # 앞뒤를 나란히 놓은 확인용 이미지
    mock = ''.join(f'<figure><div class="card">{svg(sides[k], False, bg)}</div><figcaption>{t}</figcaption></figure>'
                   for k, t in (('front', 'FRONT'), ('back', 'BACK')))
    with open(f'{build}/card-mockup.html', 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html><head><meta charset="utf-8"><style>'
                '* { margin: 0; box-sizing: border-box; } body { width: 1500px; background: #E6E2DA; padding: 70px 60px 50px; display: flex; gap: 60px; justify-content: center; }'
                'figure { display: flex; flex-direction: column; align-items: center; gap: 20px; }'
                '.card { width: 660px; height: 366.67px; box-shadow: 0 18px 40px rgba(0,0,0,.22), 0 2px 6px rgba(0,0,0,.12); }'
                '.card svg { display: block; } figcaption { font: 600 13px sans-serif; letter-spacing: .2em; color: #8A877F; }'
                f'</style></head><body>{mock}</body></html>')

    jobs = [
        {'html': f'{build}/card-print.html', 'w': 348, 'h': 197, 'pdf': f'{out}/{name}-print.pdf',
         'pdfw': f'{W + 2 * BLEED:g}mm', 'pdfh': f'{H + 2 * BLEED:g}mm'},
        {'html': f'{build}/card-preview.html', 'w': px, 'h': py, 'pages': f'{build}/side-%02d.png'},
        {'html': f'{build}/card-mockup.html', 'w': 1500, 'h': 400, 'full': True, 'out': f'{out}/{name}-preview.png'},
    ]
    with open(f'{build}/card-jobs.json', 'w') as f:
        json.dump(jobs, f)
    subprocess.run(['node', f'{HERE}/render.js', f'{build}/card-jobs.json'], check=True)
    fix_pdf_boxes(f'{out}/{name}-print.pdf')
    os.replace(f'{build}/side-01.png', f'{out}/{name}-front.png')
    os.replace(f'{build}/side-02.png', f'{out}/{name}-back.png')
    print(out)


if __name__ == '__main__':
    main()
