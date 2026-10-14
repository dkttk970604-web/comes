"""bellink 로고 2차 시안 생성기 (감각적인 방향 세 가지).

    pip install fonttools skia-pathops uharfbuzz
    python3 brand/logo/v2/source/generate.py

PNG와 미리보기 보드 렌더링에는 Node.js + Playwright(Chromium)가 필요합니다.
폰트(Jost, Fraunces, Pretendard: 모두 SIL OFL)는 처음 실행할 때 source/fonts/ 에 내려받습니다.
모든 로고의 글자는 윤곽선(path)으로 변환되므로 결과 SVG는 폰트 없이도 똑같이 보입니다.
"""
import json
import math
import os
import re
import subprocess
import urllib.request

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from pathops import PathOp, op

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
FONT_DIR, BUILD_DIR = f'{HERE}/fonts', f'{HERE}/.build'

GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl'
PRET = 'https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static'
FONTS = {
    'Jost[wght].ttf': f'{GF}/jost/Jost%5Bwght%5D.ttf',
    'Fraunces[SOFT,WONK,opsz,wght].ttf': f'{GF}/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf',
    'Pretendard-Regular.otf': f'{PRET}/Pretendard-Regular.otf',
    'Pretendard-SemiBold.otf': f'{PRET}/Pretendard-SemiBold.otf',
}
JOST = f'{FONT_DIR}/Jost[wght].ttf'
FRAUNCES = f'{FONT_DIR}/Fraunces[SOFT,WONK,opsz,wght].ttf'
FRAUNCES_VAR = {'wght': 400, 'opsz': 144, 'SOFT': 0, 'WONK': 0}

# 방향별 팔레트
ARCH = {'forest': '#1F3A32', 'clay': '#C9734F', 'ivory': '#F4EFE7', 'sand': '#E3D8C6'}
SERIF = {'ink': '#1C1B19', 'ivory': '#F4EFE7', 'champagne': '#B8976A', 'stone': '#D9D2C5'}
MOD = {'teal': '#1E5B57', 'terra': '#D2693C', 'mustard': '#E2A93B', 'cream': '#F3ECE0', 'ink': '#1D1D1B'}


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


def circle(cx, cy, r):
    p = pathops.Path()
    _arc(p, cx, cy, r, 0, 2 * math.pi, move=True)
    p.close()
    return p


def ellipse(cx, cy, rx, ry):
    return circle(0, 0, 1).transform(rx, 0, 0, ry, cx, cy)


def poly(points):
    p = pathops.Path()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    p.close()
    return p


def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def arch(x, w, h, base=0.0):
    """아치(문) 모양: 왼쪽 x, 폭 w, 전체 높이 h, 바닥 y=base. y축은 아래 방향."""
    r = w / 2
    p = pathops.Path()
    p.moveTo(x, base)
    p.lineTo(x, base - h + r)
    _arc(p, x + r, base - h + r, r, math.pi, 2 * math.pi)
    p.lineTo(x + w, base)
    p.close()
    return p


def union(*ps):
    out = pathops.Path()
    for p in ps:
        out.addPath(p)
    out.simplify()
    return out


def inter(a, b):
    return op(a, b, PathOp.INTERSECTION)


def diff(a, b):
    return op(a, b, PathOp.DIFFERENCE)


def move(p, dx, dy, s=1.0):
    return p.transform(s, 0, 0, s, dx, dy)


def bbox(parts):
    return union(*parts).bounds


def to_d(path):
    pen = SVGPathPen(None, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
    path.draw(pen)
    return pen.getCommands()


# -------------------------------------------------------------------- text ---
_fonts = {}


def glyph_paths(font_path, text, size, variations=None, tracking=0.0, extra=None):
    """HarfBuzz로 조판한 글자별 윤곽선 목록. 기준선 y=0."""
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
    x, out = 0.0, []
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        g = pathops.Path()
        font.draw_glyph_with_pen(info.codepoint, TransformPen(g.getPen(), (s, 0, 0, -s, x + pos.x_offset * s, -pos.y_offset * s)))
        out.append(g)
        x += pos.x_advance * s + tracking * size
        if extra and i in extra:
            x += extra[i] * size / 100
    return out


def split_i_dot(g):
    cs = sorted(g.contours, key=lambda c: c.bounds[1])
    return union(*cs[1:]), cs[0]


def left_align(items):
    x0 = bbox([p for p, _ in items])[0]
    return [(move(p, -x0, 0), c) for p, c in items]


# ------------------------------------------------------- 01 Arch (아치) ---
def arch_parts(h):
    """두 개의 둥근 아치가 겹치고, 겹친 자리(뾰족한 아치)는 비워 빛이 드는 창처럼 보이게 함. 바닥 y=0."""
    a1, a2 = arch(0, 60, 100), arch(34, 60, 100)
    s = h / 100
    return move(diff(a1, a2), 0, 0, s), move(diff(a2, a1), 0, 0, s)


def arch_wordmark(size=100):
    return union(*glyph_paths(JOST, 'bellink', size, {'wght': 400}, 0.0))


def arch_logo(dark=False, size=100):
    a = 0.78 * size                      # Jost 'b' 높이
    left, right = arch_parts(a * 1.32)
    gap = 0.46 * a
    word = arch_wordmark(size)
    word = move(word, bbox([left, right])[2] + gap - word.bounds[0], 0)
    fg = ARCH['ivory'] if dark else ARCH['forest']
    return [(left, fg), (right, ARCH['clay']), (word, fg)]


def arch_mark(dark=False, h=100):
    left, right = arch_parts(h)
    return [(left, ARCH['ivory'] if dark else ARCH['forest']), (right, ARCH['clay'])]


# --------------------------------------------------- 02 Serif door (세리프) ---
def serif_parts(size=100, gap_extra=8.0, top=-84.0, hair=3.0, cut=-58.0):
    """Fraunces 'bellink'에서 ll을 하나의 아치형 문으로 잇는 합자. (본체, ll 문, i의 점) 반환."""
    g = glyph_paths(FRAUNCES, 'bellink', 100, FRAUNCES_VAR, 0.0, extra={2: gap_extra})
    l1, l2 = g[2], g[3]
    stem = (97.25, 106.11)               # Fraunces 400 opsz144 의 l 세로획 (크기 100 기준)
    sw = stem[1] - stem[0]
    off = l2.bounds[0] - l1.bounds[0]
    xl, xr = stem[0], stem[1] + off
    ro, cx = (xr - xl) / 2, (xl + xr) / 2
    ys = top + ro
    below = rect(-1e4, cut, 1e4, 1e4)
    legs = union(inter(l1, below), inter(l2, below),
                 rect(xl, ys, xl + sw, cut + 0.5), rect(xr - sw, ys, xr, cut + 0.5))
    arc = inter(diff(circle(cx, ys, ro), ellipse(cx, ys, ro - sw, ro - hair)), rect(-1e4, -1e4, 1e4, ys + 0.01))
    door = union(legs, arc)
    i_body, i_dot = split_i_dot(g[4])
    body = union(*[gg for i, gg in enumerate(g) if i not in (2, 3, 4)], i_body)
    s = size / 100
    return move(body, 0, 0, s), move(door, 0, 0, s), move(i_dot, 0, 0, s)


def serif_logo(dark=False, size=100):
    body, door, dot = serif_parts(size)
    fg = SERIF['ivory'] if dark else SERIF['ink']
    return left_align([(body, fg), (door, fg), (dot, SERIF['champagne'])])


def serif_mark(dark=False, h=100):
    """문(ll 합자) 하나와 그 안의 샴페인색 점: 짧은 표기용 모노그램."""
    _, door, dot = serif_parts(100)
    x0, y0, x1, y1 = door.bounds
    inner_cx = (x0 + x1) / 2
    d = dot.bounds
    r = (d[2] - d[0]) / 2
    sun = circle(inner_cx, y0 + (y1 - y0) * 0.36, r * 1.05)
    s = h / (y1 - y0)
    fg = SERIF['ivory'] if dark else SERIF['ink']
    return left_align([(move(door, -x0 * s, -y1 * s, s), fg), (move(sun, -x0 * s, -y1 * s, s), SERIF['champagne'])])


# ------------------------------------------------- 03 Modular b (모듈 b) ---
def mod_parts(h=100):
    """아치(숙박) + 사각(부동산) + 해(여행) 세 조각이 모여 소문자 b가 됨. 바닥 y=0."""
    u = h / 2
    door = arch(0, u, u, base=-u)
    block = rect(0, -u, u, 0)
    sun = circle(u * 1.5, -u / 2, u / 2)
    return door, block, sun


def mod_logo(dark=False, size=100):
    a = 0.78 * size
    door, block, sun = mod_parts(a * 1.12)
    word = union(*glyph_paths(JOST, 'bellink', size, {'wght': 500}, -0.005))
    word = move(word, bbox([door, block, sun])[2] + 0.42 * a - word.bounds[0], 0)
    fg = MOD['cream'] if dark else MOD['ink']
    return [(door, MOD['terra']), (block, MOD['cream'] if dark else MOD['teal']), (sun, MOD['mustard']), (word, fg)]


def mod_mark(dark=False, h=100):
    door, block, sun = mod_parts(h)
    return [(door, MOD['terra']), (block, MOD['cream'] if dark else MOD['teal']), (sun, MOD['mustard'])]


# ------------------------------------------------------------------ output ---
def svg_doc(items, title='bellink'):
    def n(v):
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    x0, y0, x1, y1 = bbox([p for p, _ in items])
    w, h = x1 - x0, y1 - y0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{n(x0)} {n(y0)} {n(w)} {n(h)}" width="{n(w)}" height="{n(h)}" role="img" aria-label="{title}">',
           f'<title>{title}</title>']
    out += [f'<path fill="{fill}" d="{to_d(p)}"/>' for p, fill in items]
    return '\n'.join(out + ['</svg>']) + '\n', w, h


DIRECTIONS = {
    '01-arch': (arch_logo, arch_mark),
    '02-serif': (serif_logo, serif_mark),
    '03-modular': (mod_logo, mod_mark),
}


def main():
    os.makedirs(FONT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    for name, url in FONTS.items():
        if not os.path.exists(f'{FONT_DIR}/{name}'):
            print('download', name)
            urllib.request.urlretrieve(url, f'{FONT_DIR}/{name}')

    jobs = []
    for key, (logo, mark) in DIRECTIONS.items():
        d = f'{OUT}/{key}'
        os.makedirs(d, exist_ok=True)
        for name, items, ph in ((f'bellink-{key}-logo', logo(), 400), (f'bellink-{key}-logo-white', logo(dark=True), 400),
                                (f'bellink-{key}-symbol', mark(), 800), (f'bellink-{key}-symbol-white', mark(dark=True), 800)):
            svg, w, h = svg_doc(items)
            with open(f'{d}/{name}.svg', 'w') as f:
                f.write(svg)
            pw = round(w * ph / h)
            html = f'{BUILD_DIR}/{name}.html'
            with open(html, 'w') as f:
                f.write(f'<html><body style="margin:0"><img src="file://{d}/{name}.svg" style="display:block;width:{pw}px;height:{ph}px"></body></html>')
            jobs.append({'html': html, 'out': f'{d}/{name}.png', 'w': pw, 'h': ph, 'transparent': True})

    with open(f'{HERE}/board.html') as f:
        tpl = f.read()
    tpl = tpl.replace('{{FONT_DIR}}', FONT_DIR).replace('{{OUT}}', OUT)
    with open(f'{BUILD_DIR}/board.html', 'w') as f:
        f.write(tpl)
    jobs.append({'html': f'{BUILD_DIR}/board.html', 'out': f'{OUT}/bellink-logo-v2-preview.png', 'w': 1600, 'h': 1200, 'full': True})
    with open(f'{BUILD_DIR}/jobs.json', 'w') as f:
        json.dump(jobs, f)
    subprocess.run(['node', f'{HERE}/render.js', f'{BUILD_DIR}/jobs.json'], check=True)
    print('done')


if __name__ == '__main__':
    main()
