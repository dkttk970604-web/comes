# BELLINK 로고 v4 (진행 중)

보내주신 **BELLINK 워드마크**와 **원 안의 B 스케치**를 바탕으로 만든 안입니다.

![심볼과 로고 적용 예시](bellink-v4-examples.png)

심볼을 일곱 가지로 더 풀어 본 비교: [bellink-v4-symbol-variations.png](bellink-v4-symbol-variations.png)

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

명함 속 이름·주소와 SNS 화면은 예시입니다.

## 다시 만들기

```bash
pip install fonttools skia-pathops uharfbuzz
python3 brand/logo/v4/source/generate.py   # PNG 렌더링에는 Node.js + Playwright 필요
```

심볼의 선 굵기(`STROKE`), B의 위치와 비율(`A`, `YT`, `YM`, `YB`, `WU`, `WL`)을 바꿔 다시 실행하면 모든 파일이 함께 바뀝니다.
