# 시장 히트맵 (Market Heatmap)

Finviz 스타일 트리맵 — 네모 크기 = 시가총액, 색 = 수익률(빨강 하락 / 초록 상승),
섹터 > 산업 > 종목 계층. **자체 수집·자체 실행되는 독립 앱** (외부 프로젝트 의존 없음).

## 처음 설치 (어느 컴퓨터든 3줄)

```powershell
git clone https://github.com/minsuquant-cloud/market_heatmap.git
cd market_heatmap
py -3.12 -m venv .venv                          # 레포별 가상환경
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 실행

```powershell
# 방법 1 — 그냥 켠다 (첫 실행만 데이터 수집으로 2~3분, 이후 몇 초)
.venv\Scripts\python.exe -m streamlit run heatmap_app.py

# 방법 2 — 데이터를 미리 받아두고 켠다 (앱이 즉시 뜸)
.venv\Scripts\python.exe collect_meta.py            # 나스닥 100
.venv\Scripts\python.exe collect_meta.py --all      # S&P 500까지
.venv\Scripts\python.exe -m streamlit run heatmap_app.py
```

→ 브라우저에서 http://localhost:8501

> 가상환경을 활성화(`.venv\Scripts\activate`)했다면 `python`·`streamlit`을 그대로 써도 된다.

## 화면 사용법

- **확대**: 네모 클릭 (섹터 → 산업 → 종목)
- **축소**: 맨 위 경로줄에서 「전체」(처음으로) 또는 상위 이름(한 단계) 클릭
- **유니버스**: 나스닥 100 / S&P 500 · **기간**: 1일 ~ 연초 이후
- 하단 메트릭: 시총가중 평균 vs 중앙값이 벌어지면 대형주와 나머지가 따로 움직인다는 뜻

## 데이터 — 전부 자체 수집 (사전 준비물 없음)

| 항목 | 출처 | 갱신 주기 |
|---|---|---|
| 구성종목 | 위키피디아 리스트 문서 | 1시간 캐시 |
| 섹터·산업·시가총액 | yfinance (종목별) | `results/heatmap_meta_*.csv` 7일 캐시 — 「메타 갱신」 버튼 또는 `collect_meta.py`로 강제 |
| 수익률 | yfinance (일괄) | 15분 캐시 — 켤 때마다 사실상 최신 |

- 원리: **움직이는 것(가격)은 매번, 안 움직이는 것(섹터·이름)은 받아놓고 재사용.**
- 실패한 종목은 조용히 빼지 않고 화면·터미널에 개수와 목록을 표시한다.
- 매주 자동 갱신을 원하면 Windows 작업 스케줄러에 `python collect_meta.py --all` 등록.

## 파일 구성

```
heatmap_app.py     화면 (Streamlit 트리맵)
collect_meta.py    데이터 수집 CLI (앱 없이 미리 수집·자동화용)
requirements.txt   의존성 (pip install -r 로 한 번에)
results/           수집된 캐시 (git 제외 — 각자 자기 컴퓨터에서 수집)
```

정보 제공 목적이며 투자 권유가 아님. yfinance는 지연 시세.
