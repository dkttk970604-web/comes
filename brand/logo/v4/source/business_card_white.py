"""BELLINK 명함 흰색판 (90 x 50 mm, 앞뒤).

    python3 brand/logo/v4/source/business_card_white.py [정보.json] [출력 폴더]

보내주신 일러스트레이터 명함 화면을 재서 글씨체, 크기, 위치를 그대로 옮겼습니다.
- 글씨: Pretendard SemiBold. 앞면 왼쪽 8pt, 뒷면 왼쪽 7.5pt, 오른쪽(연락처·주소) 6.5pt
- 왼쪽 위: 이름과 직함. 오른쪽 위: 연락처와 주소. 두 덩어리의 첫 줄 기준선을 맞춥니다.
- 아래: 왼쪽에 BELLINK 워드마크, 오른쪽에 아치 심볼. 워드마크 기준선과 심볼 바닥을 맞춥니다.
- 글자는 모두 윤곽선이고, 인쇄용 PDF는 재단 여유 1mm씩을 더한 92 x 52 mm 두 쪽입니다.

정보 파일을 주지 않으면 card-white.example.json(예시 정보)으로 만듭니다.
실제 연락처가 담긴 정보 파일과 결과물은 저장소에 올리지 마세요(card-white.json은 .gitignore에 있습니다).
"""
import json
import math
import os
import sys
import urllib.request

import pathops
import uharfbuzz as hb
from fontTools.pens.transformPen import TransformPen

import business_card as bc
import generate as g

HERE = bc.HERE
W, H = bc.W, bc.H
INK, PAPER = '#000000', '#FFFFFF'
PRET = f'{g.FONT_DIR}/Pretendard-SemiBold.otf'
PRET_URL = 'https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static/Pretendard-SemiBold.otf'
PT = 25.4 / 72                         # 1pt (mm)

# 위치 (mm). 화면에서 잰 값입니다.
LEFT_X, RIGHT_X = 6.3, 50.4            # 왼쪽 덩어리, 오른쪽 덩어리의 시작
SIDES = {
    #        왼쪽 글자 크기, 왼쪽 첫 줄 기준선, 왼쪽 줄 간격, 오른쪽 글자 크기, 오른쪽 줄 간격
    'front': dict(left_size=8.0 * PT, top=8.9, left_lead=3.9, right_size=6.5 * PT, right_lead=3.38),
    'back': dict(left_size=7.5 * PT, top=7.85, left_lead=4.0, right_size=6.5 * PT, right_lead=3.38),
}
BOTTOM = 6.25                          # 아래 여백: 워드마크 기준선과 심볼 바닥
WM_X, WM_CAP = 6.4, 3.06               # 워드마크 왼쪽 끝, 대문자 높이
SYM_RIGHT, SYM_H = 6.2, 5.08           # 심볼 오른쪽 여백, 높이

_face = None


def pret_path(text, size):
    """Pretendard SemiBold로 조판한 글자 윤곽선. 시작점 x=0, 기준선 y=0."""
    global _face
    if _face is None:
        if not os.path.exists(PRET):
            os.makedirs(g.FONT_DIR, exist_ok=True)
            urllib.request.urlretrieve(PRET_URL, PRET)
        _face = hb.Face(hb.Blob.from_file_path(PRET))
    font = hb.Font(_face)
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
        x += pos.x_advance * s
    out.simplify()
    return out


def arch_symbol():
    """아치 심볼: 위 모서리가 둥근 두 칸을 붙이고 가운데 아래를 아치로 뚫은 모양. 높이 24 기준 단위."""
    w, h, r, a, top = 39.0, 24.0, 8.0, 8.0, 15.0   # 폭, 높이, 위 모서리 반지름, 아치 반폭, 아치 꼭대기 높이
    m, yc = w / 2, h - (top - a)
    p = pathops.Path()
    p.moveTo(0, h)
    p.lineTo(0, r)
    g._arc(p, r, r, r, math.pi, 1.5 * math.pi)
    p.lineTo(m - r, 0)
    g._arc(p, m - r, r, r, 1.5 * math.pi, 2 * math.pi)
    g._arc(p, m + r, r, r, math.pi, 1.5 * math.pi)
    p.lineTo(w - r, 0)
    g._arc(p, w - r, r, r, 1.5 * math.pi, 2 * math.pi)
    p.lineTo(w, h)
    p.lineTo(m + a, h)
    p.lineTo(m + a, yc)
    g._arc(p, m, yc, a, 0, -math.pi)
    p.lineTo(m - a, h)
    p.close()
    p.simplify()
    return p


def footer():
    """아래 줄: BELLINK 워드마크(명함용 굵기·자간)와 아치 심볼."""
    wm = g.wordmark(wght=bc.WM_WGHT, tracking=bc.WM_TRACK)
    s = WM_CAP / -wm.bounds[1]
    base = H - BOTTOM
    sym = arch_symbol()
    k = SYM_H / (sym.bounds[3] - sym.bounds[1])
    sw = (sym.bounds[2] - sym.bounds[0]) * k
    return [(bc.at(wm, WM_X, base, s), INK),
            (g.move(sym, W - SYM_RIGHT - sw - sym.bounds[0] * k, base - sym.bounds[3] * k, k), INK)]


def side(name, info):
    st = SIDES[name]
    items = []
    for i, line in enumerate(info['left']):
        items.append((bc.at(pret_path(line, st['left_size']), LEFT_X, st['top'] + i * st['left_lead']), INK))
    for i, line in enumerate(info['right']):
        items.append((bc.at(pret_path(line, st['right_size']), RIGHT_X, st['top'] + i * st['right_lead']), INK))
    return items + footer()


def main():
    info_path = sys.argv[1] if len(sys.argv) > 1 else f'{HERE}/card-white.example.json'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(HERE), 'business-card-white')
    with open(info_path, encoding='utf-8') as f:
        info = json.load(f)
    if not os.path.exists(g.NOTO):
        g.main()
    sides = {k: side(k, info[k]) for k in ('front', 'back')}
    bc.render_cards(sides, out, name='bellink-business-card-white', bg=PAPER)


if __name__ == '__main__':
    main()
