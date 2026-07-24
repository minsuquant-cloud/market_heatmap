# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Finviz 스타일 시장 히트맵 — 나스닥 100 / S&P 500 구성종목을 트리맵으로 그린다(네모 크기 = 시가총액, 색 = 수익률, 섹터 → 산업 → 종목 계층). tech_dashboard에서 분리해 나온 **독립 앱**으로, 외부 프로젝트 데이터에 의존하지 않고 스스로 수집한다.

## 실행 환경

레포 자체 `.venv` 사용 (Python 3.12). streamlit 1.60 / plotly 6.9 / yfinance 1.5 / pandas 3.0.

```powershell
.venv\Scripts\python.exe -m streamlit run heatmap_app.py   # 앱 (localhost:8501)
.venv\Scripts\python.exe collect_meta.py                   # 메타 수집: 나스닥100
.venv\Scripts\python.exe collect_meta.py --universe spx    # S&P500
.venv\Scripts\python.exe collect_meta.py --all             # 둘 다
```

테스트 스위트·린터는 없다.

## 아키텍처

파일 3개뿐인 플랫 구조. 핵심은 **캐시 계층 분리**다:

| 데이터 | 출처 | 캐시 |
|---|---|---|
| 구성종목 티커 | 위키피디아 리스트 문서 | `@st.cache_data(ttl=3600)` |
| 섹터·산업·시가총액 | yfinance `Ticker.info` (종목당 1요청, 느림) | `results/heatmap_meta_{ndx,spx}.csv` 7일 |
| 수익률 | yfinance `download` (일괄, 빠름) | `@st.cache_data(ttl=900)` |

설계 원칙은 **"움직이는 것(가격)은 매번, 안 움직이는 것(섹터·시총)은 받아놓고 재사용"**. 그래서 메타 수집만 파일 캐시로 빠져 있고, `collect_meta.py`와 `heatmap_app.py`가 **같은 CSV 파일을 공유**한다 — 한쪽에서 수집하면 다른 쪽이 그대로 이어받는다. 유니버스 정의(`UNIVERSES` dict)가 두 파일에 각각 있으므로 URL·캐시 경로를 바꿀 땐 양쪽을 함께 고쳐야 한다.

`collect_meta.py`는 앱 없이 캐시를 미리 만들어두는 CLI다 (작업 스케줄러 등록용).

## 알아둘 것

- **위키피디아는 User-Agent 헤더가 없으면 403**을 준다 — `fetch_tickers()`의 UA 설정을 지우지 말 것.
- 티커 표기 변환: `BRK.B` → `BRK-B` (yfinance 형식). `.` → `-` 치환이 양쪽 파일에 있다.
- **실패를 조용히 넘기지 않는 것이 이 프로젝트의 방침**이다. 메타 수집 실패·시가총액 미상 종목은 화면과 터미널에 개수와 목록을 표시한다(`st.warning`, `st.caption`). 이 표시를 제거하지 말 것.
- 트리맵 루트에 `px.Constant("전체")`를 넣는 것은 축소 내비게이션을 위한 의도적 장치다(경로줄에서 한 번에 처음 화면 복귀). 라벨에 이모지를 쓰면 plotly 경로줄에서 글자가 깨지므로(🏠 → "선제") 넣지 말 것.
- 색 스케일은 ±3%가 기본이되 기간이 길면 90퍼센타일로 자동 확대된다(`span`).
- `results/`는 git 제외 — 각자 컴퓨터에서 수집한다.
