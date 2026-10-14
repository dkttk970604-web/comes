"""bellink 로고 생성기.

모든 SVG/PNG와 미리보기 보드를 이 스크립트 하나로 다시 만듭니다.
워드마크는 글자를 윤곽선(path)으로 변환해 넣으므로, 결과 파일은 폰트 없이도 똑같이 보입니다.

    pip install fonttools skia-pathops uharfbuzz
    python3 brand/logo/source/generate.py           # SVG + PNG + 미리보기
    python3 brand/logo/source/generate.py --svg-only

PNG 렌더링에는 Node.js와 Playwright(Chromium)가 필요합니다.
폰트(Outfit, Pretendard: 둘 다 SIL OFL)는 처음 실행할 때 source/fonts/ 에 내려받습니다.
"""
import json
import math
import os
import subprocess
import sys
import urllib.request

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from pathops import LineCap, LineJoin, PathOp, op

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SVG_DIR, PNG_DIR, FONT_DIR = f'{OUT}/svg', f'{OUT}/png', f'{HERE}/fonts'
BUILD_DIR = f'{HERE}/.build'

NAVY, GOLD, WHITE, INK = '#0E2A47', '#E3A21A', '#FFFFFF', '#111111'

FONTS = {
    'Outfit[wght].ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/outfit/Outfit%5Bwght%5D.ttf',
    'Pretendard-Bold.otf': 'https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static/Pretendard-Bold.otf',
    'Pretendard-SemiBold.otf': 'https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static/Pretendard-SemiBold.otf',
}
OUTFIT = f'{FONT_DIR}/Outfit[wght].ttf'
PRETENDARD = f'{FONT_DIR}/Pretendard-Bold.otf'
WORDMARK_WEIGHT = 600
WORDMARK_TRACKING = -0.012
ASCENDER = 0.723  # Outfit 'b' 높이 / em


# ---------------------------------------------------------------- geometry ---
def _arc(p, cx, cy, r, a0, a1, move=False):
    segs = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2) - 1e-9))
    da = (a1 - a0) / segs
    k = 4 / 3 * math.tan(da / 4)
    if move:
        p.moveTo(cx + r * math.cos(a0), cy + r * math.sin(a0))
    for i in range(segs):
        t0 = a0 + i * da
        t1 = t0 + da
        x0, y0 = cx + r * math.cos(t0), cy + r * math.sin(t0)
        x3, y3 = cx + r * math.cos(t1), cy + r * math.sin(t1)
        p.cubicTo(x0 - k * r * math.sin(t0), y0 + k * r * math.cos(t0),
                  x3 + k * r * math.sin(t1), y3 - k * r * math.cos(t1), x3, y3)


def stadium(cx, cy, length, r, angle_deg):
    """체인 링크의 중심선: 반원 두 개를 직선으로 이은 닫힌 경로."""
    p = pathops.Path()
    h = length / 2
    p.moveTo(h, -r)
    _arc(p, h, 0, r, -math.pi / 2, math.pi / 2)
    p.lineTo(-h, r)
    _arc(p, -h, 0, r, math.pi / 2, 3 * math.pi / 2)
    p.close()
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return p.transform(c, s, -s, c, cx, cy)


def poly(points, closed=True):
    p = pathops.Path()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    if closed:
        p.close()
    return p


def stroke(p, w, join=LineJoin.ROUND_JOIN, cap=LineCap.ROUND_CAP, miter=4):
    q = pathops.Path(p)
    q.stroke(w, cap, join, miter)
    q.convertConicsToQuads()
    q.simplify()
    return q


def union(*ps):
    out = pathops.Path()
    for p in ps:
        out.addPath(p)
    out.simplify()
    return out


def move(p, dx, dy, s=1.0):
    return p.transform(s, 0, 0, s, dx, dy)


def bbox(parts):
    return union(*parts).bounds


def star4(cx, cy, R, k=0.15):
    """네 갈래 별(best)."""
    p = pathops.Path()
    kk = R * k
    p.moveTo(cx, cy - R)
    p.quadTo(cx + kk, cy - kk, cx + R, cy)
    p.quadTo(cx + kk, cy + kk, cx, cy + R)
    p.quadTo(cx - kk, cy + kk, cx - R, cy)
    p.quadTo(cx - kk, cy - kk, cx, cy - R)
    p.close()
    return p


def to_d(path):
    pen = SVGPathPen(None, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
    path.draw(pen)
    return pen.getCommands()


# -------------------------------------------------------------------- text ---
_fonts = {}


def text_path(font_path, text, size, variations=None, tracking=0.0):
    """HarfBuzz로 조판한 글자 윤곽선. 기준선 y=0, y축은 아래 방향."""
    key = (font_path, tuple(sorted((variations or {}).items())))
    if key not in _fonts:
        face = hb.Face(hb.Blob.from_file_path(font_path))
        font = hb.Font(face)
        if variations:
            font.set_variations(variations)
        _fonts[key] = (face, font)
    face, font = _fonts[key]
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True, 'liga': False, 'calt': False})
    s = size / face.upem
    x, glyphs = 0.0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = pathops.Path()
        font.draw_glyph_with_pen(info.codepoint, TransformPen(g.getPen(), (s, 0, 0, -s, x + pos.x_offset * s, -pos.y_offset * s)))
        glyphs.append(g)
        x += pos.x_advance * s + tracking * size
    return glyphs


def wordmark(size=100):
    """'bellink' 본체와 i의 점(따로 색을 넣기 위해 분리)."""
    glyphs = text_path(OUTFIT, 'bellink', size, {'wght': WORDMARK_WEIGHT}, WORDMARK_TRACKING)
    body = pathops.Path()
    dot = None
    for i, g in enumerate(glyphs):
        if i == 4:  # i: 맨 위 윤곽이 점
            cs = sorted(g.contours, key=lambda c: c.bounds[1])
            dot = cs[0]
            for c in cs[1:]:
                body.addPath(c)
        else:
            body.addPath(g)
    body.simplify()
    x0 = union(body, dot).bounds[0]
    return move(body, -x0, 0), move(dot, -x0, 0)


def korean(text, size):
    p = union(*text_path(PRETENDARD, text, size, None, -0.01))
    return move(p, -p.bounds[0], 0)


# ------------------------------------------------------------------ symbols ---
def _overlap_centres(a, b):
    out = []
    for c in op(a, b, PathOp.INTERSECTION).contours:
        x0, y0, x1, y1 = c.bounds
        out.append(((x0 + x1) / 2, (y0 + y1) / 2))
    return sorted(out, key=lambda t: t[1])


def peak_link(theta=60, L=48, r=16, w=12, k=0.5, gap=2.8):
    """A안: 두 링크가 맞물려 ∧(정점)을 이룸. 위 교차점은 네이비가, 아래 교차점은 골드가 위로 지나감."""
    a = math.radians(theta)
    ux, uy = math.cos(a), -math.sin(a)
    upx = -r * k  # 왼쪽 링크 윗쪽 반원의 중심 x (축에서 r*k 만큼 왼쪽)
    c1 = stadium(upx - ux * L / 2, -uy * L / 2, L, r, -theta)
    c2 = c1.transform(-1, 0, 0, 1, 0, 0)
    r1, r2 = stroke(c1, w), stroke(c2, w)
    ov = _overlap_centres(r1, r2)
    assert len(ov) == 2, ov
    mid = (ov[0][1] + ov[1][1]) / 2
    big = 1e4
    upper = poly([(-big, mid), (big, mid), (big, -big), (-big, -big)])
    lower = poly([(-big, mid), (big, mid), (big, big), (-big, big)])
    r2 = op(r2, op(stroke(c1, w + 2 * gap), upper, PathOp.INTERSECTION), PathOp.DIFFERENCE)
    r1 = op(r1, op(stroke(c2, w + 2 * gap), lower, PathOp.INTERSECTION), PathOp.DIFFERENCE)
    return [r1, r2]


def symbol(h=100):
    parts = peak_link()
    x0, y0, x1, y1 = bbox(parts)
    s = h / (y1 - y0)
    return [move(p, -x0 * s, -y0 * s, s) for p in parts]  # [네이비 링크, 골드 링크]


# ----------------------------------------------------------------- lockups ---
def lock_horizontal(dark=False, size=100, sym_scale=1.3, gap=0.42, star_dot=False):
    a = ASCENDER * size
    body, dot = wordmark(size)
    sym = [move(p, 0, -a * sym_scale) for p in symbol(a * sym_scale)]  # 심볼 바닥 = 기준선
    dx = bbox(sym)[2] + gap * a
    body, dot = move(body, dx, 0), move(dot, dx, 0)
    fg = WHITE if dark else NAVY
    items = [(sym[0], fg), (sym[1], GOLD), (body, fg)]
    if star_dot:
        x0, y0, x1, y1 = dot.bounds
        items.append((star4((x0 + x1) / 2, (y0 + y1) / 2 - 0.01 * size, (x1 - x0) * 0.78, 0.16), GOLD))
    else:
        items.append((dot, GOLD))
    return items


def lock_vertical(dark=False, size=100, sym_scale=2.0, gap=0.42):
    a = ASCENDER * size
    body, dot = wordmark(size)
    wm_w = union(body, dot).bounds[2]
    sym = symbol(a * sym_scale)
    sw = bbox(sym)[2]
    sym = [move(p, (wm_w - sw) / 2, -a - gap * a - a * sym_scale) for p in sym]
    fg = WHITE if dark else NAVY
    return [(sym[0], fg), (sym[1], GOLD), (body, fg), (dot, GOLD)]


def lock_korean(dark=False, size=100, gap=0.42):
    a = ASCENDER * size
    ko = korean('벨링크', size * 0.98)
    x0, y0, x1, y1 = ko.bounds
    sym = symbol((y1 - y0) * 1.3 * 0.92)
    sw, sh = bbox(sym)[2], bbox(sym)[3]
    sym = [move(p, 0, (y0 + y1) / 2 - sh / 2) for p in sym]
    fg = WHITE if dark else NAVY
    return [(sym[0], fg), (sym[1], GOLD), (move(ko, sw + gap * a, 0), fg)]


def app_icon(S=1024):
    s = symbol(100)
    x0, y0, x1, y1 = bbox(s)
    k = S * 0.58 / (x1 - x0)
    w, h = (x1 - x0) * k, (y1 - y0) * k
    s = [move(p, (S - w) / 2, (S - h) / 2 - S * 0.012, k) for p in s]
    return [(s[0], WHITE), (s[1], GOLD)]


def house_b_wordmark(size=100):
    """B안: b의 둥근 부분을 지붕 있는 집으로 바꾸고 안에 골드 별."""
    k = size / 100
    w = 13.15 * k        # Outfit 600 세로획 굵기
    wb = w * 0.9
    L = (5.75 + 6.575) * k
    R = 56.0 * k - wb / 2
    bot, eave, peak = -wb / 2, -34 * k, -48 * k
    stem = poly([(L, -72.3 * k), (L, 0)], closed=False)
    bowl = poly([(L, bot), (L, eave), ((L + R) / 2, peak), (R, eave), (R, bot)])
    b = union(stroke(stem, w, LineJoin.MITER_JOIN, LineCap.BUTT_CAP),
              stroke(bowl, wb, LineJoin.MITER_JOIN, LineCap.BUTT_CAP, 10))
    star = star4((L + w / 2 - wb / 2 + R) / 2, (bot + eave) / 2 - 1.0 * k, 9.0 * k, 0.15)
    glyphs = text_path(OUTFIT, 'bellink', size, {'wght': WORDMARK_WEIGHT}, WORDMARK_TRACKING)
    return [(b, NAVY), (union(*glyphs[1:]), NAVY), (star, GOLD)]


# ------------------------------------------------------------------ output ---
def svg_doc(items, bg=None, size=None, rx=0):
    def n(v):
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    if size:
        X0, Y0, W, H = 0, 0, size, size
    else:
        x0, y0, x1, y1 = bbox([p for p, _ in items])
        X0, Y0, W, H = x0, y0, x1 - x0, y1 - y0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{n(X0)} {n(Y0)} {n(W)} {n(H)}" width="{n(W)}" height="{n(H)}" role="img" aria-label="bellink">',
           '<title>bellink</title>']
    if bg:
        out.append(f'<rect x="{n(X0)}" y="{n(Y0)}" width="{n(W)}" height="{n(H)}" rx="{n(rx)}" fill="{bg}"/>')
    out += [f'<path fill="{fill}" d="{to_d(p)}"/>' for p, fill in items]
    return '\n'.join(out + ['</svg>']) + '\n', W, H


def recolor(items, colour):
    return [(p, colour) for p, _ in items]


def main():
    svg_only = '--svg-only' in sys.argv
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, url in FONTS.items():
        if not os.path.exists(f'{FONT_DIR}/{name}'):
            print('download', name)
            urllib.request.urlretrieve(url, f'{FONT_DIR}/{name}')
    for d in (SVG_DIR, PNG_DIR, BUILD_DIR):
        os.makedirs(d, exist_ok=True)

    jobs = []

    def save(name, items, heights, **kw):
        svg, W, H = svg_doc(items, **kw)
        with open(f'{SVG_DIR}/{name}.svg', 'w') as f:
            f.write(svg)
        for h in heights:
            w = round(W * h / H)
            out = f'{PNG_DIR}/{name}' + (f'-{h}' if len(heights) > 1 else '') + '.png'
            html = f'{BUILD_DIR}/{os.path.basename(out)}.html'
            with open(html, 'w') as f:
                f.write(f'<html><body style="margin:0"><img src="file://{SVG_DIR}/{name}.svg" style="display:block;width:{w}px;height:{h}px"></body></html>')
            jobs.append({'html': html, 'out': out, 'w': w, 'h': h, 'transparent': True})

    sym = symbol()
    save('bellink-symbol', [(sym[0], NAVY), (sym[1], GOLD)], [1000])
    save('bellink-symbol-white', [(sym[0], WHITE), (sym[1], GOLD)], [1000])
    save('bellink-symbol-navy', [(sym[0], NAVY), (sym[1], NAVY)], [1000])
    h = lock_horizontal()
    save('bellink-logo-horizontal', h, [400])
    save('bellink-logo-horizontal-white', lock_horizontal(dark=True), [400])
    save('bellink-logo-horizontal-navy', recolor(h, NAVY), [400])
    save('bellink-logo-horizontal-black', recolor(h, INK), [400])
    save('bellink-logo-vertical', lock_vertical(), [800])
    save('bellink-logo-vertical-white', lock_vertical(dark=True), [800])
    save('bellink-logo-korean', lock_korean(), [400])
    save('bellink-logo-korean-white', lock_korean(dark=True), [400])
    save('bellink-app-icon', app_icon(1024), [1024, 512, 180, 64, 32], bg=NAVY, size=1024, rx=1024 * 0.22)
    save('concept-b-house-b-wordmark', house_b_wordmark(), [400])
    save('concept-c-star-wordmark', lock_horizontal(star_dot=True)[2:], [400])

    with open(f'{BUILD_DIR}/board.html', 'w') as f:
        f.write(board_html())
    jobs.append({'html': f'{BUILD_DIR}/board.html', 'out': f'{OUT}/bellink-logo-preview.png', 'w': 1600, 'h': 1200, 'full': True})

    if not svg_only:
        with open(f'{BUILD_DIR}/jobs.json', 'w') as f:
            json.dump(jobs, f)
        subprocess.run(['node', f'{HERE}/render.js', f'{BUILD_DIR}/jobs.json'], check=True)
    print('done')


def board_html():
    def img(name, h):
        return f'<img src="file://{SVG_DIR}/{name}.svg" style="height:{h}px;display:block">'
    with open(f'{HERE}/board.html') as f:
        tpl = f.read()
    tpl = tpl.replace('{{FONT_DIR}}', FONT_DIR)
    import re
    return re.sub(r'\{\{img:([\w-]+):(\d+)\}\}', lambda m: img(m.group(1), int(m.group(2))), tpl)


if __name__ == '__main__':
    main()
