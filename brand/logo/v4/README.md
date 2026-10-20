# BELLINK 로고 v4 (진행 중)

보내주신 **BELLINK 워드마크**와 **원 안의 B 스케치**를 바탕으로 만든 안입니다.

![심볼과 로고 적용 예시](bellink-v4-examples.png)

심볼을 일곱 가지로 더 풀어 본 비교: [bellink-v4-symbol-variations.png](bellink-v4-symbol-variations.png)

## BELLINK 글자로 만드는 심볼 아이디어

![글자로 만드는 심볼 아이디어](bellink-v4-letter-symbol-ideas.png)

LL 고리, BL 모노그램, BL 열쇠, E 세 사업, K 만나는 점, BK 처음과 끝, i 위치 핀.

## 고리 부분 다시 보기 (선택 중)

![고리 부분 다시 보기](bellink-v4-ring-revisit.png)

체인처럼 보이려면 엮이는 자리가 두 곳이어야 합니다. G1은 기둥에 두 원 고리가 좌우 두 곳에서 엮이고, G3은 보통 B 모양을 지키면서 아래 칸이 기둥 위를 지나고 오른쪽에서 위 칸 곡선 아래로 들어갑니다.

## 더 B답게 엮은 고리 (선택 중)

![더 B답게 엮은 고리](bellink-v4-b-linked-classic.png)

기둥은 곧은 한 줄, B의 비율도 그대로 두고, 아래 칸의 윗선이 기둥 뒤로 들어와 위 칸의 곡선 앞으로 나가도록 해 안에서 두 칸이 고리처럼 걸리게 했습니다.

## B 한 글자로 엮은 고리 (선택 중)

![B 한 글자로 엮은 고리](bellink-v4-single-b-link.png)

B의 위 칸과 아래 칸을 각각 닫힌 고리로 만들고, 아래 고리의 기둥을 살짝 왼쪽에 세워 체인처럼 서로 걸었습니다. 왼쪽에서는 아래 고리가 위 고리의 기둥 뒤로, 오른쪽에서는 위 고리의 곡선 앞으로 지나갑니다.

## 서로 이어진 두 B (선택 중)

![서로 이어진 두 B](bellink-v4-linked-b.png)

- **A 맞댄 B**: 두 B가 등을 맞대고 기둥 하나를 함께 씀 (좌우 대칭)
- **B 돌려 맞댄 B**: 한 B를 거꾸로 돌려 기둥을 함께 씀 (점대칭)
- **C 고리로 걸린 B**: 마주 본 두 B의 볼이 가운데서 체인 고리처럼 걸림

C를 바탕으로 더 풀어 본 안 (둥근 고리, 깊게 걸린, 엇갈려 걸린, 가는 선, 투톤, 원 안의 고리):

![고리로 걸린 B 더 보기](bellink-v4-linked-b-more.png)

## 고리 심볼 (선택 중)

![고리처럼 잇는 심볼](bellink-v4-loop-symbols.png)

- **한 줄 고리** (`-loop`): B의 기둥이 내려오다 부드럽게 꺾여 그대로 원이 되고, 한 바퀴 돌아 열린 채 끝납니다.
- **소용돌이 고리** (`-spiral`): B의 아래 곡선이 끊기지 않고 바깥으로 이어져 원을 감습니다.

## 구성

- **워드마크**: 보내주신 이미지를 벡터로 재현했습니다. Noto Sans KR SemiBold(600), 자간 -0.02em로 글자 폭과 전체 길이가 원본과 일치합니다.
- **심볼 B (추천)**: 원 안의 한 줄 굵기 B. B의 기둥이 아래로 내려와 원과 이어집니다. B(best)와 원(link, 연결)이 한 선으로 묶인 모양입니다.
- **심볼 A**: 스케치 그대로. 원이 왼쪽 아래에서 B의 밑으로 감겨 들어갑니다.
- **색**: 검정 `#10100E`, 크림 `#FFFFE5` (보내주신 이미지에서 추출)

## 파일

`svg/`(원본)와 `png/`(투명 배경)에 같은 이름으로 있습니다. `-cream`이 붙은 파일은 어두운 바탕용입니다.

| 파일 | 쓰임 |
|---|---|
| `bellink-logo-horizontal` | 심볼 + 워드마크 가로형 |
| `bellink-logo-vertical` | 심볼 위, 워드마크 아래 세로형 |
| `bellink-wordmark` | 워드마크만 |
| `bellink-symbol` | 심볼 B (추천) |
| `bellink-symbol-alt` | 심볼 A (스케치 그대로) |
| `bellink-app-icon` | 앱 아이콘 (검정 바탕 + 크림 심볼) |
| `bellink-symbol-loop`, `bellink-logo-horizontal-loop`, `bellink-logo-vertical-loop` | 한 줄 고리 심볼과 로고 조합 |
| `bellink-symbol-spiral`, `bellink-logo-horizontal-spiral`, `bellink-logo-vertical-spiral` | 소용돌이 고리 심볼과 로고 조합 |

명함 속 이름·주소와 SNS 화면은 예시입니다.

## 다시 만들기

```bash
pip install fonttools skia-pathops uharfbuzz
python3 brand/logo/v4/source/generate.py   # PNG 렌더링에는 Node.js + Playwright 필요
```

심볼의 선 굵기(`STROKE`), B의 위치와 비율(`A`, `YT`, `YM`, `YB`, `WU`, `WL`)을 바꿔 다시 실행하면 모든 파일이 함께 바뀝니다.
