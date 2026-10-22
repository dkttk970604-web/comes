"""BELLINK 명함 흰색 세로 쌓기판 (90 x 50 mm, 앞뒤).

    python3 brand/logo/v4/source/business_card_stack.py [정보.json] [출력 폴더]

보내주신 아트보드 3·4 형식을 다듬은 안입니다.
- 오른쪽 위: BELLINK 워드마크(명함용 굵기 680, 자간 0)
- 왼쪽 아래: 이름(11pt)과 직함(7.5pt)을 같은 기준선에, 그 아래 아이콘을 붙인 연락처와 주소(6.5pt). 글씨는 Pretendard SemiBold
  이름 윗선은 오른쪽 아래 심볼 윗선에, 마지막 줄은 심볼 바닥(아래 여백)에 맞춰, 정보 덩어리가 심볼 높이 안에 들어갑니다.
- 오른쪽 아래: 심볼을 아주 연하게. 기본은 원형 B 심볼(B와 원이 한 선으로 이어진 모양, best + link),
  'arch'를 고르면 아치 심볼(B를 눕혀 다리처럼 만든 모양). 투명도 대신 같은 밝기의 회색 단색으로 넣어 인쇄가 안정적입니다.
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
# 오른쪽 아래 심볼: 종류('b' 또는 'arch'), 폭(mm), 진하기(검정의 몇 %). 잘리지 않게, 오른쪽 끝은 워드마크
# 오른쪽 끝에, 바닥은 마지막 줄 기준선에 맞춥니다. 원은 직선에 딱 맞추면 안쪽으로 들어가 보여 조금 넘깁니다.
MARK_KIND, MARK_W, MARK_TONE, OVERSHOOT = 'b', 17.0, 0.07, 0.3
# 연락처 줄: 아이콘 크기, 아이콘 왼쪽 끝에서 글자까지, 한 줄에 두 항목일 때 사이 간격 (mm)
ICON, ICON_TEXT, ITEM_GAP = 2.0, 3.2, 4.0


def tone(t):
    """흰 종이 위 검정 t 비율을 단색 회색으로 (예: 0.10 → #E6E6E6)."""
    v = round(255 * (1 - t))
    return f'#{v:02X}{v:02X}{v:02X}'


def mark(kind=MARK_KIND, width=MARK_W, right=W - RIGHT + OVERSHOOT, bottom=H - BOTTOM + OVERSHOOT, t=MARK_TONE):
    """오른쪽 아래 심볼. right, bottom은 심볼 오른쪽 끝과 바닥의 위치(mm)입니다."""
    sym = w.arch_symbol() if kind == 'arch' else g.symbol_watermark()
    x0, y0, x1, y1 = sym.bounds
    k = width / (x1 - x0)
    return (g.move(sym, right - x1 * k, bottom - y1 * k, k), tone(t))


def contact_line(line, y):
    """[아이콘, 글자, 아이콘, 글자, ...] 한 줄. 아이콘은 phone·email·address·instagram, 빈 문자열이면 아이콘 없이 들여 씁니다."""
    out, x = [], LEFT
    for kind, text in zip(line[::2], line[1::2]):
        if kind:
            out.append((g.move(bc.ICONS[kind](), x, y - 0.8 - ICON / 2, ICON / 10), w.INK))
        p = w.pret_path(text, SMALL)
        out.append((bc.at(p, x + ICON_TEXT, y), w.INK))
        x += ICON_TEXT + bc.ink_width(p) + ITEM_GAP
    return out


def side(d, mark_item=None):
    items = [mark_item or mark()]
    wm = g.wordmark(wght=bc.WM_WGHT, tracking=bc.WM_TRACK)
    s = WM_WIDTH / (wm.bounds[2] - wm.bounds[0])
    items.append((bc.at(wm, W - RIGHT - WM_WIDTH, TOP - wm.bounds[1] * s, s), w.INK))
    # 마지막 줄이 아래 여백에 오도록 아래에서부터 쌓습니다
    last = H - BOTTOM
    n = len(d['lines'])
    for i, line in enumerate(d['lines']):
        items += contact_line(line, last - (n - 1 - i) * LEAD)
    name = w.pret_path(d['name'], NAME)
    sym = items[0][0]
    if sym.bounds[3] > sym.bounds[1]:
        # 이름 윗선을 심볼 윗선에 맞춥니다(원은 그만큼 위로 넘어가 있으므로 OVERSHOOT만큼 내림). 앞뒤 이름 높이가 같아집니다.
        base = sym.bounds[1] + OVERSHOOT - name.bounds[1]
    else:
        base = last - (n - 1) * LEAD - GAP
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
