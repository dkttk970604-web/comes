"""bellink 브랜드 아이덴티티 (2차 시안 02 세리프 도어 디벨롭).

로고 전체 세트(SVG/PNG/파비콘), 패턴, 브랜드 가이드(PDF와 페이지별 PNG)를 이 스크립트 하나로 만듭니다.
로고 속 글자는 모두 윤곽선(path)으로 변환되므로 결과 SVG는 폰트 없이도 똑같이 보입니다.

    pip install fonttools skia-pathops uharfbuzz
    python3 brand/logo/v3/source/generate.py

PNG·PDF 렌더링에는 Node.js + Playwright(Chromium), 파비콘 .ico 에는 ImageMagick이 필요합니다.
폰트(Fraunces, Jost, Hahmlet, Pretendard: 모두 SIL OFL)는 처음 실행할 때 source/fonts/ 에 내려받습니다.
"""
import json
import math
import os
import shutil
import subprocess
import urllib.request

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from pathops import PathOp, op

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SVG_DIR, PNG_DIR, FAV_DIR, GUIDE_DIR = f'{OUT}/svg', f'{OUT}/png', f'{OUT}/favicon', f'{OUT}/guide'
FONT_DIR, BUILD_DIR = f'{HERE}/fonts', f'{HERE}/.build'

GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl'
PRET = 'https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static'
FONTS = {
    'Fraunces[SOFT,WONK,opsz,wght].ttf': f'{GF}/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf',
    'Fraunces-Italic[SOFT,WONK,opsz,wght].ttf': f'{GF}/fraunces/Fraunces-Italic%5BSOFT,WONK,opsz,wght%5D.ttf',
    'Jost[wght].ttf': f'{GF}/jost/Jost%5Bwght%5D.ttf',
    'Hahmlet[wght].ttf': f'{GF}/hahmlet/Hahmlet%5Bwght%5D.ttf',
    'Pretendard-Regular.otf': f'{PRET}/Pretendard-Regular.otf',
    'Pretendard-SemiBold.otf': f'{PRET}/Pretendard-SemiBold.otf',
}
FRAUNCES = f'{FONT_DIR}/Fraunces[SOFT,WONK,opsz,wght].ttf'
JOST = f'{FONT_DIR}/Jost[wght].ttf'
HAHMLET = f'{FONT_DIR}/Hahmlet[wght].ttf'

INK, IVORY, CHAMPAGNE, STONE = '#1C1B19', '#F4EFE7', '#B8976A', '#D9D2C5'
BLACK, WHITE = '#000000', '#FFFFFF'

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



def oval(cx, cy, rx, ry, kappa=0.5523):
    """kappa를 키우면 네모에 가까운 타원이 됩니다."""
    p = pathops.Path()
    kx, ky = rx * kappa, ry * kappa
    p.moveTo(cx + rx, cy)
    p.cubicTo(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry)
    p.cubicTo(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy)
    p.cubicTo(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry)
    p.cubicTo(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy)
    p.close()
    return p


def hslice(g, y, h=0.6):
    """글자 g를 높이 y에서 가로로 잘랐을 때의 좌우 끝 (세로획 굵기 측정용)."""
    b = inter(g, rect(-1e4, y - h, 1e4, y + h)).bounds
    return b[0], b[2]


# ---------------------------------------------------------------- wordmark ---
# 두 l은 그대로 두어 bellink로 또렷하게 읽히게 하고, 그 사이에 샴페인색 아치(문)를 넣습니다.
# 기본형(큰 크기)과 소형(작은 크기)은 Fraunces의 광학 크기(opsz)만 다르고 구조는 같습니다.
#   gap: 두 l 사이를 벌리는 양, inset: 기둥과 문 사이 틈, door: 문 높이(어센더 대비 비율)
DISPLAY = dict(opsz=144, wght=440, track=0.008, gap=11.0, inset=3.0, door=0.735)
SMALL = dict(opsz=36, wght=470, track=0.02, gap=12.0, inset=3.4, door=0.735)


def wordmark_parts(spec=DISPLAY, size=100):
    """(본체, 두 l 기둥, 문). 기준선 y=0, 크기 100 기준 좌표를 size로 비례 조정."""
    var = {'wght': spec['wght'], 'opsz': spec['opsz'], 'SOFT': 0, 'WONK': 0}
    g = glyph_paths(FRAUNCES, 'bellink', 100, var, spec['track'], extra={2: spec['gap']})
    l1, l2 = g[2], g[3]
    asc = l1.bounds[1]
    s1, s2 = hslice(l1, asc * 0.4), hslice(l2, asc * 0.4)
    # 문 쪽 아래 세리프를 잘라 기둥(문틀)처럼 정리
    l1 = diff(l1, rect(s1[1], asc * 0.3, 1e4, 1e4))
    l2 = diff(l2, rect(-1e4, asc * 0.3, s2[0], 1e4))
    pillars = union(l1, l2)
    x0, x1 = s1[1] + spec['inset'], s2[0] - spec['inset']
    door = arch(x0, x1 - x0, -asc * spec['door'], base=0)
    body = union(*[gg for i, gg in enumerate(g) if i not in (2, 3)])
    left = union(body, pillars).bounds[0]
    k = size / 100
    return [move(p, -left * k, 0, k) for p in (body, pillars, door)]


def wordmark_metrics(spec=DISPLAY, size=100):
    """가이드 도면용 기준선들."""
    var = {'wght': spec['wght'], 'opsz': spec['opsz'], 'SOFT': 0, 'WONK': 0}
    g = glyph_paths(FRAUNCES, 'bellink', 100, var, spec['track'], extra={2: spec['gap']})
    k = size / 100
    body, pillars, door = wordmark_parts(spec, size)
    return {
        'ascender': g[0].bounds[1] * k,
        'xheight': g[5].bounds[1] * k,     # n의 높이
        'door_top': door.bounds[1],
        'door': door.bounds,
        'pillars': pillars.bounds,
        'width': union(body, pillars, door).bounds[2],
    }


def colorize(parts, fg, accent):
    body, pillars, door = parts
    return [(body, fg), (pillars, fg), (door, accent)]


def wordmark(fg=INK, accent=CHAMPAGNE, spec=DISPLAY, size=100):
    return colorize(wordmark_parts(spec, size), fg, accent)


# ------------------------------------------------------------- lockups ---
def text_line(font, text, size, variations=None, tracking=0.0):
    p = union(*glyph_paths(font, text, size, variations, tracking))
    return move(p, -p.bounds[0], 0)


DESCRIPTOR = 'TRAVEL · STAY · ESTATE'


def descriptor_path(width):
    """워드마크 폭에 맞춘 Jost 대문자 설명문 (자간 넓게)."""
    p = text_line(JOST, DESCRIPTOR, 100, {'wght': 430}, 0.34)
    # 마지막 글자 뒤 자간은 폭 계산에서 제외되도록 실제 윤곽 폭 기준으로 맞춤
    s = width * 0.80 / p.bounds[2]
    return move(p, 0, 0, s)


def lockup_descriptor(fg=INK, accent=CHAMPAGNE, size=100):
    parts = wordmark(fg, accent, DISPLAY, size)
    w = bbox([p for p, _ in parts])[2]
    d = descriptor_path(w)
    d = move(d, (w - d.bounds[2]) / 2, -d.bounds[1] + 0.19 * size)
    return parts + [(d, fg)]


def korean_wordmark(fg=INK, size=100):
    p = text_line(HAHMLET, '벨링크', size, {'wght': 300}, 0.06)
    return [(p, fg)]


def lockup_korean(fg=INK, accent=CHAMPAGNE, size=100):
    """워드마크 | 벨링크 가로 조합."""
    parts = wordmark(fg, accent, DISPLAY, size)
    m = wordmark_metrics(DISPLAY, size)
    ko = text_line(HAHMLET, '벨링크', size * 0.52, {'wght': 300}, 0.06)
    kb = ko.bounds
    # 한글 높이의 중심을 워드마크 x-height 영역 중심에 맞춤
    target_mid = m['xheight'] / 2 - 0.02 * size
    ko = move(ko, 0, target_mid - (kb[1] + kb[3]) / 2)
    gap = 0.30 * size
    rule_x = m['width'] + gap
    rule = rect(rule_x, m['ascender'] * 0.92, rule_x + 0.012 * size, 0.08 * size)
    ko = move(ko, rule_x + gap, 0)
    return parts + [(rule, fg), (ko, fg)]


# ----------------------------------------------------------- monogram ---
def monogram_parts(h=100, spec=DISPLAY):
    """워드마크의 두 l 기둥과 그 사이 문만 떼어 낸 모노그램. (기둥, 문)을 높이 h로."""
    _, pillars, door = wordmark_parts(spec, 100)
    x0, y0, x1, y1 = union(pillars, door).bounds
    k = h / (y1 - y0)
    return move(pillars, -x0 * k, -y0 * k, k), move(door, -x0 * k, -y0 * k, k)


def monogram(fg=INK, accent=CHAMPAGNE, h=100):
    pillars, door = monogram_parts(h)
    return [(pillars, fg), (door, accent)]


# ------------------------------------------------------------- emblem ---
def text_on_arc(text, font, size, variations, cx, cy, radius, tracking=0.0, bottom=False):
    """원호 위의 글자. bottom=False면 12시 방향 중심으로 시계 방향(글자 위가 바깥),
    bottom=True면 6시 방향 중심으로 왼쪽에서 오른쪽으로 읽히게(글자 위가 안쪽) 놓습니다.
    radius는 글자 높이(대문자)의 가운데가 지나는 원의 반지름입니다."""
    key = (font, tuple(sorted((variations or {}).items())))
    glyph_paths(font, 'H', size, variations)
    face, f = _fonts[key]
    s = size / face.upem
    cap = f.get_glyph_extents(f.get_nominal_glyph(ord('H'))).y_bearing * s
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f, buf, {'kern': True})
    advs = [p.x_advance * s + tracking * size for p in buf.glyph_positions]
    total = sum(advs) - tracking * size
    out = pathops.Path()
    x = 0.0
    for info, adv in zip(buf.glyph_infos, advs):
        w = adv - tracking * size
        g = pathops.Path()
        # 글자 가운데를 원점에, 대문자 높이의 가운데를 y=0에 맞춤
        f.draw_glyph_with_pen(info.codepoint, TransformPen(g.getPen(), (s, 0, 0, -s, -w / 2, cap / 2)))
        offset = (x + w / 2 - total / 2) / radius
        if bottom:
            a = math.pi / 2 - offset
            rot = a - math.pi / 2
        else:
            a = -math.pi / 2 + offset
            rot = a + math.pi / 2
        c, sn = math.cos(rot), math.sin(rot)
        out.addPath(g.transform(c, sn, -sn, c, cx + radius * math.cos(a), cy + radius * math.sin(a)))
        x += adv
    out.simplify()
    return out


def emblem(fg=INK, accent=CHAMPAGNE, d=200):
    """원형 엠블럼(도장·스티커·포장용): 위쪽 BELLINK, 아래쪽 TRAVEL · STAY · ESTATE, 가운데 모노그램."""
    c = d / 2
    ring_outer = diff(circle(c, c, c), circle(c, c, c - d * 0.006))
    ring_inner = diff(circle(c, c, c * 0.68), circle(c, c, c * 0.68 - d * 0.004))
    r_text = c * 0.84
    top = text_on_arc('BELLINK', JOST, d * 0.075, {'wght': 430}, c, c, r_text, tracking=0.42)
    bottom = text_on_arc('TRAVEL · STAY · ESTATE', JOST, d * 0.054, {'wght': 430}, c, c, r_text, tracking=0.22, bottom=True)
    dots = union(circle(c - r_text, c, d * 0.009), circle(c + r_text, c, d * 0.009))
    pillars, door = monogram_parts(d * 0.33)
    mb = union(pillars, door).bounds
    off = (c - (mb[0] + mb[2]) / 2, c - (mb[1] + mb[3]) / 2)
    pillars, door = move(pillars, *off), move(door, *off)
    return [(ring_outer, fg), (ring_inner, fg), (top, fg), (bottom, fg), (dots, accent), (pillars, fg), (door, accent)]


# ------------------------------------------------------------ app icon ---
def app_icon(size=1024):
    pillars, door = monogram_parts(size * 0.56)
    mb = union(pillars, door).bounds
    off = ((size - (mb[2] - mb[0])) / 2 - mb[0], (size - (mb[3] - mb[1])) / 2 - mb[1])
    return [(move(pillars, *off), IVORY), (move(door, *off), CHAMPAGNE)]


def favicon_small():
    """16·32·48px 전용 단순화 모노그램. 16px 픽셀 격자에 맞춘 두 기둥과 그 사이 문."""
    pillars = union(rect(3, 2, 5, 14), rect(11, 2, 13, 14))
    door = arch(6, 4, 9, base=14)
    return [(rect(0, 0, 16, 16), INK), (pillars, IVORY), (door, CHAMPAGNE)]


# ------------------------------------------------------------- pattern ---
def pattern(fg=INK, accent=CHAMPAGNE, w=1200, h=800, cell=(100, 140)):
    """가는 선의 문(아치)을 엇갈려 반복하는 패턴. 일부 문에만 샴페인 점."""
    cw, ch = cell
    lines, dots = pathops.Path(), pathops.Path()
    t = 1.4
    aw, ah = cw * 0.44, ch * 0.56
    row = 0
    y = -ch * 0.2
    while y < h + ch:
        x = -cw if row % 2 else -cw / 2
        col = 0
        while x < w + cw:
            outer = arch(x, aw, ah, base=y + ah)
            inner = arch(x + t, aw - 2 * t, ah - t, base=y + ah + 0.01)
            lines.addPath(diff(outer, inner))
            if (row * 3 + col * 2) % 7 == 0:
                dots.addPath(circle(x + aw / 2, y + aw / 2 + 2, aw * 0.07))
            x += cw
            col += 1
        y += ch * 0.72
        row += 1
    frame = rect(0, 0, w, h)
    lines.simplify()
    dots.simplify()
    return [(inter(lines, frame), fg), (inter(dots, frame), accent)]



def rrect(x0, y0, x1, y1, r):
    p = pathops.Path()
    p.moveTo(x0 + r, y0)
    p.lineTo(x1 - r, y0)
    _arc(p, x1 - r, y0 + r, r, -math.pi / 2, 0)
    p.lineTo(x1, y1 - r)
    _arc(p, x1 - r, y1 - r, r, 0, math.pi / 2)
    p.lineTo(x0 + r, y1)
    _arc(p, x0 + r, y1 - r, r, math.pi / 2, math.pi)
    p.lineTo(x0, y0 + r)
    _arc(p, x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
    p.close()
    return p


def recolor(items, colour):
    return [(p, colour) for p, _ in items]


# ------------------------------------------------------- guide diagrams ---
def _paths(items):
    return ''.join(f'<path fill="{c}" d="{to_d(p)}"/>' for p, c in items)


def construction_svg():
    """워드마크 구조도: 기준선과 번호 주석 (가이드 3쪽)."""
    m = wordmark_metrics(DISPLAY, 100)
    items = wordmark()
    w = m['width']
    lines = [('BASELINE', 0), ('X-HEIGHT', m['xheight']), ('DOOR', m['door_top']), ('ASCENDER', m['ascender'])]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-14 {m["ascender"] - 22:.1f} {w + 70:.1f} {-m["ascender"] + 36:.1f}" width="100%">']
    for label, y in lines:
        out.append(f'<line x1="-14" x2="{w + 8:.1f}" y1="{y:.2f}" y2="{y:.2f}" stroke="{CHAMPAGNE}" stroke-width="0.28" stroke-dasharray="1.2 1.2"/>')
        out.append(f'<text x="{w + 11:.1f}" y="{y + 1.1:.2f}" font-family="J" font-size="3" letter-spacing="0.5" fill="#8A8074">{label}</text>')
    out.append(_paths(items))
    p0, p1 = m['pillars'][0], m['pillars'][2]
    d0, d1 = m['door'][0], m['door'][2]
    marks = [(1, ((p0 + p1) / 2, m['ascender'] - 10)), (2, ((d0 + d1) / 2, (m['door_top'] + 0) / 2 + 4)),
             (3, (-8, m['door_top']))]
    for n, (x, y) in marks:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="{IVORY}" stroke="{INK}" stroke-width="0.35"/>'
                   f'<text x="{x:.1f}" y="{y + 1.25:.1f}" text-anchor="middle" font-family="J" font-size="3.6" fill="{INK}">{n}</text>')
    out.append('</svg>')
    return ''.join(out)


def clearspace_svg():
    """여백 규정도: 사방으로 x-height 만큼 비움 (가이드 5쪽)."""
    m = wordmark_metrics(DISPLAY, 100)
    items = wordmark()
    x0, y0, x1, y1 = bbox([p for p, _ in items])
    X = -m['xheight']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0 - X - 6:.1f} {y0 - X - 6:.1f} {x1 - x0 + 2 * X + 12:.1f} {y1 - y0 + 2 * X + 12:.1f}" width="100%">',
           f'<rect x="{x0 - X:.1f}" y="{y0 - X:.1f}" width="{x1 - x0 + 2 * X:.1f}" height="{y1 - y0 + 2 * X:.1f}" fill="none" stroke="{CHAMPAGNE}" stroke-width="0.5" stroke-dasharray="2 1.6"/>',
           f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" fill="none" stroke="{STONE}" stroke-width="0.4"/>']
    for cx, cy in (((x0 + x1) / 2, y0 - X / 2), ((x0 + x1) / 2, y1 + X / 2), (x0 - X / 2, (y0 + y1) / 2), (x1 + X / 2, (y0 + y1) / 2)):
        out.append(f'<rect x="{cx - X / 2:.1f}" y="{cy - X / 2:.1f}" width="{X:.1f}" height="{X:.1f}" fill="{CHAMPAGNE}" fill-opacity="0.16"/>'
                   f'<text x="{cx:.1f}" y="{cy + 3:.1f}" text-anchor="middle" font-family="Fr" font-style="italic" font-size="9" fill="#8A6F45">x</text>')
    out.append(_paths(items) + '</svg>')
    return ''.join(out)


def plain_svg():
    """잘못된 사용 예: 합자를 풀고 그냥 입력한 글자."""
    p = text_line(FRAUNCES, 'bellink', 100, {'wght': 440, 'opsz': 144, 'SOFT': 0, 'WONK': 0}, 0.008)
    return svg_doc([(p, INK)])[0]


# ------------------------------------------------------------------ build ---
def main():
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, url in FONTS.items():
        if not os.path.exists(f'{FONT_DIR}/{name}'):
            print('download', name)
            urllib.request.urlretrieve(url, f'{FONT_DIR}/{name}')
    for d in (SVG_DIR, PNG_DIR, FAV_DIR, GUIDE_DIR, BUILD_DIR):
        os.makedirs(d, exist_ok=True)

    jobs = []

    def save(name, items, png_h, where=SVG_DIR):
        svg, w, h = svg_doc(items)
        with open(f'{where}/{name}.svg', 'w') as f:
            f.write(svg)
        if png_h:
            pw = round(w * png_h / h)
            html = f'{BUILD_DIR}/{name}.html'
            with open(html, 'w') as f:
                f.write(f'<html><body style="margin:0"><img src="file://{where}/{name}.svg" style="display:block;width:{pw}px;height:{png_h}px"></body></html>')
            jobs.append({'html': html, 'out': f'{PNG_DIR}/{name}.png', 'w': pw, 'h': png_h, 'transparent': True})

    # 워드마크
    save('bellink-wordmark', wordmark(), 300)
    save('bellink-wordmark-reverse', wordmark(IVORY), 300)
    save('bellink-wordmark-ink', wordmark(INK, INK), 300)
    save('bellink-wordmark-white', wordmark(WHITE, WHITE), 300)
    save('bellink-wordmark-small', wordmark(spec=SMALL), 300)
    save('bellink-wordmark-small-reverse', wordmark(IVORY, spec=SMALL), 300)
    # 조합형
    save('bellink-wordmark-descriptor', lockup_descriptor(), 400)
    save('bellink-wordmark-descriptor-reverse', lockup_descriptor(IVORY), 400)
    save('bellink-lockup-korean', lockup_korean(), 300)
    save('bellink-lockup-korean-reverse', lockup_korean(IVORY), 300)
    save('bellink-korean', korean_wordmark(), 200)
    save('bellink-korean-reverse', korean_wordmark(IVORY), 200)
    # 모노그램·엠블럼
    save('bellink-monogram', monogram(), 800)
    save('bellink-monogram-reverse', monogram(IVORY), 800)
    save('bellink-monogram-ink', monogram(INK, INK), 800)
    save('bellink-monogram-white', monogram(WHITE, WHITE), 800)
    save('bellink-emblem', emblem(), 1200)
    save('bellink-emblem-reverse', emblem(IVORY), 1200)
    # 앱 아이콘 (배경 포함)
    S = 1024
    icon = [(rrect(0, 0, S, S, S * 0.225), INK)] + app_icon(S)
    save('bellink-app-icon', icon, 1024)
    square = [(rect(0, 0, S, S), INK)] + app_icon(S)
    save('bellink-app-icon-square', square, None)
    # 패턴
    save('bellink-pattern-ivory', [(rect(0, 0, 1200, 800), IVORY)] + pattern(INK), 800)
    save('bellink-pattern-ink', [(rect(0, 0, 1200, 800), INK)] + pattern(CHAMPAGNE, IVORY), 800)
    with open(f'{BUILD_DIR}/pattern-line-champagne.svg', 'w') as f:
        f.write(svg_doc(pattern(CHAMPAGNE, CHAMPAGNE))[0])
    with open(f'{BUILD_DIR}/pattern-line-ink.svg', 'w') as f:
        f.write(svg_doc(pattern(INK, CHAMPAGNE))[0])

    # 파비콘
    svg, _, _ = svg_doc(favicon_small())
    with open(f'{FAV_DIR}/favicon.svg', 'w') as f:
        f.write(svg)
    for px in (16, 32, 48, 180, 192, 512):
        src = {16: 'favicon', 32: 'favicon', 48: 'favicon', 180: 'bellink-app-icon-square'}.get(px, 'bellink-app-icon')
        folder = FAV_DIR if src == 'favicon' else SVG_DIR
        html = f'{BUILD_DIR}/fav-{px}.html'
        with open(html, 'w') as f:
            f.write(f'<html><body style="margin:0"><img src="file://{folder}/{src}.svg" style="display:block;width:{px}px;height:{px}px"></body></html>')
        name = 'apple-touch-icon' if px == 180 else f'favicon-{px}'
        jobs.append({'html': html, 'out': f'{FAV_DIR}/{name}.png', 'w': px, 'h': px, 'transparent': True})

    # 브랜드 가이드
    with open(f'{HERE}/guide.html') as f:
        tpl = f.read()
    repl = {
        '{{FONT_DIR}}': FONT_DIR, '{{SVG}}': SVG_DIR, '{{BUILD}}': BUILD_DIR,
        '{{INLINE:construction}}': construction_svg(), '{{INLINE:clearspace}}': clearspace_svg(),
    }
    with open(f'{BUILD_DIR}/misuse-plain.svg', 'w') as f:
        f.write(plain_svg())
    with open(f'{BUILD_DIR}/misuse-color.svg', 'w') as f:
        f.write(svg_doc(wordmark(INK, '#2F6FE4'))[0])
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    with open(f'{BUILD_DIR}/guide.html', 'w') as f:
        f.write(tpl)
    jobs.append({'html': f'{BUILD_DIR}/guide.html', 'w': 1600, 'h': 1000, 'pdf': f'{OUT}/bellink-brand-guide.pdf',
                 'pages': f'{GUIDE_DIR}/page-%02d.png'})

    with open(f'{BUILD_DIR}/jobs.json', 'w') as f:
        json.dump(jobs, f)
    subprocess.run(['node', f'{HERE}/render.js', f'{BUILD_DIR}/jobs.json'], check=True)

    ico = shutil.which('magick') or shutil.which('convert')
    if ico:
        subprocess.run([ico] + [f'{FAV_DIR}/favicon-{px}.png' for px in (16, 32, 48)] + [f'{FAV_DIR}/favicon.ico'], check=True)
    print('done')


if __name__ == '__main__':
    main()
