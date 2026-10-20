"""BELLINK 로고 (v4): 보내주신 워드마크 + 스케치를 다듬은 원형 B 심볼.

    pip install fonttools skia-pathops uharfbuzz
    python3 brand/logo/v4/source/generate.py

- 워드마크: 보내주신 BELLINK 이미지를 Noto Sans KR SemiBold(600), 자간 -0.02em로 벡터 재현
- 심볼 B(추천): 원 안의 모노라인 B. B의 기둥이 아래로 내려와 원과 이어집니다
- 심볼 A: 스케치 그대로. 원이 왼쪽 아래에서 B의 밑으로 감겨 들어갑니다
- 고리 심볼: 한 줄 고리(B의 기둥이 원이 됨), 소용돌이 고리(B의 아래 곡선이 원이 됨)
PNG 렌더링에는 Node.js + Playwright가 필요합니다. 폰트(Noto Sans KR, SIL OFL)는 처음 실행할 때 내려받습니다.
"""
import json
import math
import os
import subprocess
import urllib.request

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from pathops import LineCap, LineJoin

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SVG_DIR, PNG_DIR, FONT_DIR, BUILD_DIR = f'{OUT}/svg', f'{OUT}/png', f'{HERE}/fonts', f'{HERE}/.build'
NOTO = f'{FONT_DIR}/NotoSansKR[wght].ttf'
NOTO_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf'

BLACK, CREAM = '#10100E', '#FFFFE5'   # 보내주신 이미지에서 뽑은 바탕색과 글자색
STROKE = 14.5                          # 심볼 선 굵기 (원 지름 200 기준)


# ---------------------------------------------------------------- geometry ---
def _arc(p, cx, cy, r, a0, a1):
    segs = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2) - 1e-9))
    da = (a1 - a0) / segs
    k = 4 / 3 * math.tan(da / 4)
    for i in range(segs):
        t0 = a0 + i * da
        t1 = t0 + da
        x0, y0 = cx + r * math.cos(t0), cy + r * math.sin(t0)
        x3, y3 = cx + r * math.cos(t1), cy + r * math.sin(t1)
        p.cubicTo(x0 - k * r * math.sin(t0), y0 + k * r * math.cos(t0),
                  x3 + k * r * math.sin(t1), y3 - k * r * math.cos(t1), x3, y3)


def circle(cx, cy, r):
    p = pathops.Path()
    p.moveTo(cx + r, cy)
    _arc(p, cx, cy, r, 0, 2 * math.pi)
    p.close()
    return p


def line(*points):
    p = pathops.Path()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    return p


def stroke(p, w):
    q = pathops.Path(p)
    q.stroke(w, LineCap.BUTT_CAP, LineJoin.ROUND_JOIN, 4)
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


def to_d(path):
    pen = SVGPathPen(None, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
    path.draw(pen)
    return pen.getCommands()


# ------------------------------------------------------------------ symbol ---
R = 100.0                               # 원 반지름 (중심선)
A, YT, YM, YB = 0.36 * R, -0.56 * R, 0.0, 0.58 * R   # B 기둥 위치, 위·가운데·아래 높이
WU, WL = 0.62 * R, 0.72 * R             # 위·아래 볼의 폭


def b_letter():
    """모노라인 B 중심선: 기둥 + 위 볼 + 아래 볼(조금 더 넓게). 왼쪽 위 모서리는 둥글게 이어짐."""
    ru, rl = (YM - YT) / 2, (YB - YM) / 2
    xu, xl = -A + WU - ru, -A + WL - rl
    p = pathops.Path()
    p.moveTo(-A, YM)
    p.lineTo(-A, YT)
    p.lineTo(xu, YT)
    _arc(p, xu, YT + ru, ru, -math.pi / 2, math.pi / 2)
    p.lineTo(-A, YM)
    p.moveTo(-A, YM)
    p.lineTo(xl, YM)
    _arc(p, xl, YM + rl, rl, -math.pi / 2, math.pi / 2)
    p.lineTo(-A, YB)
    p.moveTo(-A, YT)
    p.lineTo(-A, YB)
    return stroke(p, STROKE)


def symbol_b():
    """추천: 닫힌 원 + B의 기둥이 원 바닥까지 내려와 이어짐."""
    h = math.sqrt(R * R - A * A)
    return union(stroke(circle(0, 0, R), STROKE), b_letter(), stroke(line((-A, YB), (-A, h)), STROKE))


def symbol_a(q_deg=160.0):
    """스케치 그대로: 원이 왼쪽 아래에서 B의 밑으로 감겨 들어가고, 기둥이 원 바닥까지 이어짐."""
    h = math.sqrt(R * R - A * A)
    a1, aq = math.atan2(h, -A), math.radians(q_deg)
    p = pathops.Path()
    p.moveTo(-A, h)
    _arc(p, 0, 0, R, a1, aq - 2 * math.pi)
    qx, qy = R * math.cos(aq), R * math.sin(aq)
    tx, ty = math.sin(aq), -math.cos(aq)
    dist = math.hypot(-A - qx, YB - qy)
    p.cubicTo(qx + tx * 0.34 * dist, qy + ty * 0.34 * dist, -A - 0.46 * dist, YB, -A, YB)
    p.lineTo(-A, h)
    p.close()
    return union(stroke(p, STROKE), b_letter())


def _stroke_round(p, w):
    q = pathops.Path(p)
    q.stroke(w, LineCap.ROUND_CAP, LineJoin.ROUND_JOIN, 4)
    q.convertConicsToQuads()
    q.simplify()
    return q


def _bowls():
    ru, rl = (YM - YT) / 2, (YB - YM) / 2
    xu, xl = -A + WU - ru, -A + WL - rl
    p = pathops.Path()
    p.moveTo(-A, YM)
    p.lineTo(-A, YT)
    p.lineTo(xu, YT)
    _arc(p, xu, YT + ru, ru, -math.pi / 2, math.pi / 2)
    p.lineTo(-A, YM)
    p.moveTo(-A, YM)
    p.lineTo(xl, YM)
    _arc(p, xl, YM + rl, rl, -math.pi / 2, math.pi / 2)
    p.lineTo(-A, YB)
    return p


def symbol_loop(t=16.0, gap=38.0):
    """4 한 줄 고리: B의 기둥이 내려오다 부드럽게 꺾여 원이 되고, 한 바퀴 돌아 열린 채 끝남."""
    aj = math.radians(100)
    jx, jy = R * math.cos(aj), R * math.sin(aj)
    dx, dy = math.sin(aj), -math.cos(aj)
    y_bend = YB + (jy - YB) * 0.15
    k = (jy - y_bend) * 0.8
    p = pathops.Path()
    p.moveTo(-A, YT)
    p.lineTo(-A, y_bend)
    p.cubicTo(-A, y_bend + k, jx - dx * k * 0.9, jy - dy * k * 0.9, jx, jy)
    _arc(p, 0, 0, R, aj, aj - 2 * math.pi + math.radians(gap))
    return union(_stroke_round(p, t), stroke(_bowls(), t))


def symbol_spiral(t=16.0, start=164.0, sweep=300.0):
    """7 소용돌이 고리: B의 아래 곡선이 끊기지 않고 이어져 바깥 원을 감음."""
    ru, rl = (YM - YT) / 2, (YB - YM) / 2
    xu, xl = -A + WU - ru, -A + WL - rl
    p = pathops.Path()
    p.moveTo(-A, YM)
    p.lineTo(xl, YM)
    _arc(p, xl, YM + rl, rl, -math.pi / 2, math.pi / 2)
    a = math.radians(start)
    ex, ey = R * math.cos(a), R * math.sin(a)
    k = 0.5 * math.hypot(ex - xl, ey - YB)
    p.cubicTo(xl - k * 1.1, YB, ex + math.sin(a) * k, ey - math.cos(a) * k, ex, ey)
    _arc(p, 0, 0, R, a, a + math.radians(sweep))
    up = pathops.Path()
    up.moveTo(-A, YM)
    up.lineTo(-A, YT)
    up.lineTo(xu, YT)
    _arc(up, xu, YT + ru, ru, -math.pi / 2, math.pi / 2)
    up.lineTo(-A, YM)
    up.moveTo(-A, YT)
    up.lineTo(-A, YB)
    return union(_stroke_round(p, t), stroke(up, t))


def normalise(p, h):
    x0, y0, x1, y1 = p.bounds
    s = h / (y1 - y0)
    return move(p, -x0 * s, -y0 * s, s)


# ---------------------------------------------------------------- wordmark ---
def wordmark(size=100, wght=600, tracking=-0.02):
    face = hb.Face(hb.Blob.from_file_path(NOTO))
    font = hb.Font(face)
    font.set_variations({'wght': wght})
    buf = hb.Buffer()
    buf.add_str('BELLINK')
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True})
    s = size / face.upem
    out, x = pathops.Path(), 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = pathops.Path()
        font.draw_glyph_with_pen(info.codepoint, TransformPen(g.getPen(), (s, 0, 0, -s, x, 0)))
        out.addPath(g)
        x += pos.x_advance * s + tracking * size
    out.simplify()
    return move(out, -out.bounds[0], -out.bounds[3])   # 왼쪽 x=0, 기준선 y=0


def lockup_horizontal(sym, ratio=1.55, gap=0.42):
    wm = wordmark()
    cap = -wm.bounds[1]
    s = normalise(sym, cap * ratio)
    s = move(s, 0, -cap / 2 - cap * ratio / 2)
    return [s, move(wm, s.bounds[2] + gap * cap, 0)]


def lockup_vertical(sym, ratio=2.7, gap=0.55):
    wm = wordmark()
    cap = -wm.bounds[1]
    s = normalise(sym, cap * ratio)
    s = move(s, (wm.bounds[2] - s.bounds[2]) / 2, -cap - gap * cap - cap * ratio)
    return [s, wm]


# ------------------------------------------------------------------ output ---
def svg_doc(paths, fill, bg=None):
    b = union(*paths).bounds
    w, h = b[2] - b[0], b[3] - b[1]
    n = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')
    rect = f'<rect x="{n(b[0])}" y="{n(b[1])}" width="{n(w)}" height="{n(h)}" fill="{bg}"/>' if bg else ''
    body = ''.join(f'<path fill="{fill}" d="{to_d(p)}"/>' for p in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{n(b[0])} {n(b[1])} {n(w)} {n(h)}" width="{n(w)}" height="{n(h)}" '
            f'role="img" aria-label="BELLINK"><title>BELLINK</title>{rect}{body}</svg>\n'), w, h


def main():
    os.makedirs(FONT_DIR, exist_ok=True)
    if not os.path.exists(NOTO):
        print('download Noto Sans KR')
        urllib.request.urlretrieve(NOTO_URL, NOTO)
    for d in (SVG_DIR, PNG_DIR, BUILD_DIR):
        os.makedirs(d, exist_ok=True)

    sym_b, sym_a = normalise(symbol_b(), 200), normalise(symbol_a(), 200)
    items = {
        'bellink-symbol': ([sym_b], 800), 'bellink-symbol-alt': ([sym_a], 800),
        'bellink-wordmark': ([wordmark()], 300),
        'bellink-logo-horizontal': (lockup_horizontal(sym_b), 400),
        'bellink-logo-vertical': (lockup_vertical(sym_b), 800),
        'bellink-symbol-loop': ([normalise(symbol_loop(), 200)], 800),
        'bellink-symbol-spiral': ([normalise(symbol_spiral(), 200)], 800),
        'bellink-logo-horizontal-loop': (lockup_horizontal(symbol_loop()), 400),
        'bellink-logo-horizontal-spiral': (lockup_horizontal(symbol_spiral()), 400),
        'bellink-logo-vertical-loop': (lockup_vertical(symbol_loop()), 800),
        'bellink-logo-vertical-spiral': (lockup_vertical(symbol_spiral()), 800),
    }
    jobs = []
    for name, (paths, ph) in items.items():
        for suffix, fill in (('', BLACK), ('-cream', CREAM)):
            svg, w, h = svg_doc(paths, fill)
            with open(f'{SVG_DIR}/{name}{suffix}.svg', 'w') as f:
                f.write(svg)
            pw = round(w * ph / h)
            html = f'{BUILD_DIR}/{name}{suffix}.html'
            with open(html, 'w') as f:
                f.write(f'<html><body style="margin:0"><img src="file://{SVG_DIR}/{name}{suffix}.svg" style="display:block;width:{pw}px;height:{ph}px"></body></html>')
            jobs.append({'html': html, 'out': f'{PNG_DIR}/{name}{suffix}.png', 'w': pw, 'h': ph, 'transparent': True})
    # 앱 아이콘: 검정 바탕 + 크림 심볼
    icon = move(normalise(symbol_b(), 1024 * 0.64), 1024 * 0.18, 1024 * 0.18)
    rect = pathops.Path()
    rect.moveTo(0, 0); rect.lineTo(1024, 0); rect.lineTo(1024, 1024); rect.lineTo(0, 1024); rect.close()
    with open(f'{SVG_DIR}/bellink-app-icon.svg', 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" role="img" aria-label="BELLINK">'
                f'<title>BELLINK</title><rect width="1024" height="1024" rx="230" fill="{BLACK}"/><path fill="{CREAM}" d="{to_d(icon)}"/></svg>\n')
    html = f'{BUILD_DIR}/app-icon.html'
    with open(html, 'w') as f:
        f.write(f'<html><body style="margin:0"><img src="file://{SVG_DIR}/bellink-app-icon.svg" style="display:block;width:1024px;height:1024px"></body></html>')
    jobs.append({'html': html, 'out': f'{PNG_DIR}/bellink-app-icon.png', 'w': 1024, 'h': 1024, 'transparent': True})
    with open(f'{BUILD_DIR}/jobs.json', 'w') as f:
        json.dump(jobs, f)
    subprocess.run(['node', f'{HERE}/render.js', f'{BUILD_DIR}/jobs.json'], check=True)
    print('done')


if __name__ == '__main__':
    main()
