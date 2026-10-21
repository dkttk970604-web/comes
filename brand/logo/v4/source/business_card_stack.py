"""BELLINK 명함 흰색 세로 쌓기판 (90 x 50 mm, 앞뒤).

    python3 brand/logo/v4/source/business_card_stack.py [정보.json] [출력 폴더]

보내주신 아트보드 3·4 형식을 다듬은 안입니다.
- 오른쪽 위: BELLINK 워드마크(명함용 굵기 680, 자간 0)
- 왼쪽 아래: 이름(11pt)과 직함(7.5pt)을 같은 기준선에, 그 아래 연락처와 주소(6.5pt). 글씨는 Pretendard SemiBold
- 오른쪽 아래: B 심볼(명함 워터마크용 심볼 A)을 아주 연하게. 투명도 대신 같은 밝기의 회색 단색으로 넣어 인쇄가 안정적입니다.
- 여백: 왼쪽·오른쪽 7mm, 워드마크 윗선까지 7.5mm, 마지막 줄 기준선까지 7.5mm

정보 파일을 주지 않으면 card-stack.example.json(예시 정보)으로 만듭니다.
실제 연락처가 담긴 정보 파일과 결과물은 저장소에 올리지 마세요(card-stack.json은 .gitignore에 있습니다).
"""
import json
import os
import sys

import business_card as bc
import business_card_white as w
import generate as g

HERE = bc.HERE
W, H, PT = w.W, w.H, w.PT
LEFT, RIGHT, TOP, BOTTOM = 7.0, 7.0, 7.5, 7.5
WM_WIDTH = 24.8                        # 워드마크 폭 (mm)
NAME, TITLE, SMALL = 11 * PT, 7.5 * PT, 6.5 * PT
LEAD, GAP, TITLE_GAP = 3.4, 6.2, 2.4   # 작은 글씨 줄 간격, 이름과 첫 줄 사이, 이름과 직함 사이
# B 심볼: 지름, 중심(mm), 진하기(검정의 몇 %). 오른쪽 약 10%, 아래 약 6%가 잘립니다.
MARK_D, MARK_CX, MARK_CY, MARK_TONE = 25.0, 80.0, 39.0, 0.05


def tone(t):
    """흰 종이 위 검정 t 비율을 단색 회색으로 (예: 0.10 → #E6E6E6)."""
    v = round(255 * (1 - t))
    return f'#{v:02X}{v:02X}{v:02X}'


def mark(d=MARK_D, cx=MARK_CX, cy=MARK_CY, t=MARK_TONE):
    sym = g.symbol_watermark()
    x0, y0, x1, y1 = sym.bounds
    k = d / (y1 - y0)
    return (g.move(sym, cx - (x0 + x1) / 2 * k, cy - (y0 + y1) / 2 * k, k), tone(t))


def side(d, mark_item=None):
    items = [mark_item or mark()]
    wm = g.wordmark(wght=bc.WM_WGHT, tracking=bc.WM_TRACK)
    s = WM_WIDTH / (wm.bounds[2] - wm.bounds[0])
    items.append((bc.at(wm, W - RIGHT - WM_WIDTH, TOP - wm.bounds[1] * s, s), w.INK))
    # 마지막 줄이 아래 여백에 오도록 아래에서부터 쌓습니다
    last = H - BOTTOM
    n = len(d['lines'])
    for i, line in enumerate(d['lines']):
        items.append((bc.at(w.pret_path(line, SMALL), LEFT, last - (n - 1 - i) * LEAD), w.INK))
    base = last - (n - 1) * LEAD - GAP
    name = w.pret_path(d['name'], NAME)
    items.append((bc.at(name, LEFT, base), w.INK))
    items.append((bc.at(w.pret_path(d['title'], TITLE), LEFT + bc.ink_width(name) + TITLE_GAP, base), w.INK))
    return items


def main():
    info_path = sys.argv[1] if len(sys.argv) > 1 else f'{HERE}/card-stack.example.json'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(HERE), 'business-card-stack')
    with open(info_path, encoding='utf-8') as f:
        info = json.load(f)
    if not os.path.exists(g.NOTO):
        g.main()
    sides = {k: side(info[k]) for k in ('front', 'back')}
    bc.render_cards(sides, out, name='bellink-business-card-stack', bg=w.PAPER)


if __name__ == '__main__':
    main()
