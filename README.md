# 시장 히트맵 (Market Heatmap)

Finviz 스타일 트리맵 — 네모 크기 = 시가총액, 색 = 수익률(빨강 하락 / 초록 상승),
섹터 > 산업 > 종목 계층. 독립 실행 앱 (tech_dashboard에서 2026-07-24 분리).

## 실행

```powershell
cd C:\Users\minsu\Documents\market_heatmap
& "C:\Users\minsu\.conda\envs\works2\python.exe" -m streamlit run heatmap_app.py
```

→ 브라우저에서 http://localhost:8501 (이미 다른 앱이 8501을 쓰면 자동으로 다음 포트)

## 화면 사용법

- **확대**: 네모 클릭 (섹터 → 산업 → 종목)
- **축소**: 맨 위 경로줄에서 「🏠 전체」(처음으로) 또는 상위 이름(한 단계) 클릭
- **유니버스**: 나스닥 100 / S&P 500 · **기간**: 1일 ~ 연초 이후
- 하단 메트릭: 시총가중 평균 vs 중앙값이 벌어지면 대형주와 나머지가 따로 움직인다는 뜻

## 데이터

| 항목 | 출처 | 갱신 |
|---|---|---|
| 구성종목 | 위키피디아 리스트 문서 | 1시간 캐시 |
| 섹터·산업·시가총액 | yfinance Ticker.info | `results/heatmap_meta_*.csv`에 7일 캐시 (「메타 갱신」 버튼으로 강제) |
| 수익률 | yfinance 일괄 다운로드 | 15분 캐시 |

- 최초 실행(또는 메타 갱신)만 종목별 수집으로 2~3분 걸림. S&P500은 첫 회 5분+.
- 실패한 종목은 조용히 빼지 않고 화면에 개수를 표시한다.
- 정보 제공 목적이며 투자 권유가 아님. yfinance는 지연 시세.

## 의존성

works2 콘다 환경 사용 (streamlit · plotly · yfinance · pandas · lxml · requests).
