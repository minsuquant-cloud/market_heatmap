# -*- coding: utf-8 -*-
"""시장 히트맵 — Finviz 스타일 트리맵 (독립 페이지).

네모 크기 = 시가총액, 색 = 수익률(빨강 하락 / 초록 상승), 섹터 > 산업 > 종목 계층.

실행:
    & "C:\\Users\\minsu\\.conda\\envs\\works2\\python.exe" -m streamlit run heatmap_app.py

데이터
----
- 종목 목록: 위키피디아 Nasdaq-100 / S&P 500 구성종목 표 (실패 시 로컬 캐시 폴백)
- 섹터·산업·시가총액: yfinance Ticker.info — 종목당 요청이라 느리므로
  `results/heatmap_meta_<유니버스>.csv` 에 캐시(기본 7일 유지, 강제 갱신 버튼 제공)
- 수익률: yf.download 일괄 — 매 실행 시 최신

정직 고지: 데이터를 못 받은 종목은 조용히 빼지 않고 화면에 개수·목록을 표시한다.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="시장 히트맵", page_icon="🗺️", layout="wide")

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)
META_MAX_AGE_DAYS = 7          # 섹터·시총 캐시 유효기간
META_MIN_COVERAGE = 0.95       # 캐시가 이 비율 이상 덮으면 재사용 (영구 실패 종목 허용)

UNIVERSES = {
    "나스닥 100": {
        "url": "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
        "cache": RESULTS / "heatmap_meta_ndx.csv",
        "ticker_col_candidates": ("Ticker", "Symbol"),
    },
    "S&P 500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "cache": RESULTS / "heatmap_meta_spx.csv",
        "ticker_col_candidates": ("Symbol", "Ticker"),
    },
}

PERIODS = {"1일": 1, "1주": 5, "1개월": 21, "3개월": 63, "연초 이후": None}


# --------------------------------------------------------------------------- #
# 데이터
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tickers(universe: str) -> list[str]:
    """위키피디아 구성종목 표 → 티커 목록. 실패하면 메타 캐시의 티커로 폴백."""
    cfg = UNIVERSES[universe]
    try:
        import io
        import requests
        r = requests.get(cfg["url"], timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})  # UA 없으면 위키가 403
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        for t in tables:
            for col in cfg["ticker_col_candidates"]:
                if col in t.columns and len(t) > 50:
                    ticks = (t[col].astype(str).str.strip()
                             .str.replace(".", "-", regex=False))  # BRK.B → BRK-B
                    return sorted(ticks.unique().tolist())
    except Exception as e:
        fail_reason = str(e)
    else:
        fail_reason = "구성종목 표를 찾지 못함"
    if cfg["cache"].exists():                      # 폴백: 캐시에 있던 티커
        # 폴백을 조용히 넘기지 않는다 — 낡은 목록을 쓰고 있음을 알린다
        st.warning(f"위키피디아에서 구성종목을 받지 못해 **캐시의 옛 목록**을 사용합니다 "
                   f"(사유: {fail_reason}). 편입·편출이 반영되지 않았을 수 있습니다.")
        return pd.read_csv(cfg["cache"])["ticker"].tolist()
    return []


def load_meta(universe: str, tickers: list[str], force: bool = False) -> pd.DataFrame:
    """섹터·산업·시가총액. 캐시가 신선하면 그대로, 아니면 yfinance로 수집."""
    cache = UNIVERSES[universe]["cache"]
    if cache.exists() and not force:
        age = dt.date.today() - dt.date.fromtimestamp(cache.stat().st_mtime)
        meta = pd.read_csv(cache)
        # 전량 일치(부분집합)를 요구하면 영구 실패 종목이 하나만 있어도 캐시를
        # 영영 못 쓰고 매 실행 2~3분씩 재수집한다 → 커버리지 기준으로 완화
        covered = len(set(tickers) & set(meta["ticker"])) / max(len(tickers), 1)
        if age.days <= META_MAX_AGE_DAYS and covered >= META_MIN_COVERAGE:
            return meta

    rows, failed = [], []
    prog = st.progress(0.0, text="섹터·시가총액 수집 중 (최초 1회, 이후 캐시)")
    for i, t in enumerate(tickers):
        try:
            info = yf.Ticker(t).info
            rows.append({
                "ticker": t,
                "name": info.get("shortName") or t,
                "sector": info.get("sector") or "기타",
                "industry": info.get("industry") or "기타",
                "mcap": info.get("marketCap") or np.nan,
            })
        except Exception:
            failed.append(t)
        prog.progress((i + 1) / len(tickers),
                      text=f"섹터·시가총액 수집 {i+1}/{len(tickers)}")
    prog.empty()
    meta = pd.DataFrame(rows)
    if len(meta):
        meta.to_csv(cache, index=False)
    if failed:
        st.warning(f"메타데이터 실패 {len(failed)}종목 (제외): {', '.join(failed[:10])}"
                   + (" …" if len(failed) > 10 else ""))
    return meta


@st.cache_data(ttl=900, show_spinner="가격 수집 중…")
def fetch_returns(tickers: tuple[str, ...], period_label: str) -> pd.Series:
    """기간 수익률(%). 연초 이후는 당해 첫 거래일 종가 기준."""
    days = PERIODS[period_label]
    today = dt.date.today()
    start = (dt.date(today.year, 1, 1) if days is None
             else today - dt.timedelta(days=max(days * 2, 10) + 5))
    px_ = yf.download(list(tickers), start=str(start), auto_adjust=True,
                      progress=False)["Close"]
    if isinstance(px_, pd.Series):
        px_ = px_.to_frame(tickers[0])
    px_ = px_.dropna(how="all")
    if days is None:
        base = px_.iloc[0]
    else:
        base = px_.iloc[-(days + 1)] if len(px_) > days else px_.iloc[0]
    return (px_.iloc[-1] / base - 1.0) * 100.0


# --------------------------------------------------------------------------- #
# 화면
# --------------------------------------------------------------------------- #
st.title("🗺️ 시장 히트맵")
st.caption("네모 크기 = 시가총액 · 색 = 수익률 (빨강 하락 / 초록 상승) · 섹터 → 산업 → 종목")

c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
universe = c1.selectbox("유니버스", list(UNIVERSES.keys()))
period = c2.selectbox("수익률 기간", list(PERIODS.keys()))
depth = c3.selectbox("계층", ["섹터 > 산업 > 종목", "섹터 > 종목"], index=0)
force = c4.button("메타 갱신", help="섹터·시가총액 캐시를 강제로 다시 받는다 (수 분 소요)")

tickers = fetch_tickers(universe)
if not tickers:
    st.error("구성종목 목록을 받지 못했습니다 (위키피디아 접속 실패 + 캐시 없음). "
             "잠시 후 다시 시도하세요.")
    st.stop()

meta = load_meta(universe, tickers, force=force)
if meta.empty:
    st.error("섹터·시가총액을 한 종목도 받지 못했습니다 (yfinance 접속 실패로 보임). "
             "잠시 후 다시 시도하거나, 터미널에서 `python collect_meta.py`로 먼저 "
             "수집해 보세요.")
    st.stop()

rets = fetch_returns(tuple(sorted(meta["ticker"])), period)

df = meta.merge(rets.rename("chg").reset_index()
                .rename(columns={"index": "ticker", "Ticker": "ticker"}),
                on="ticker", how="left")

n_no_ret = int(df["chg"].isna().sum())
n_no_cap = int(df["mcap"].isna().sum())
df = df.dropna(subset=["chg", "mcap"])
if n_no_ret or n_no_cap:
    st.caption(f":material/warning: 제외 — 수익률 미수신 {n_no_ret}건 · 시가총액 미상 {n_no_cap}건 "
               f"(표시 {len(df)}/{len(meta)}종목)")

df["label"] = df["ticker"]
df["chg_txt"] = df["chg"].map(lambda v: f"{v:+.2f}%")

# px.Constant("전체")를 루트로 넣으면 상단 경로줄에 '전체' 버튼이 항상 떠 있어
# 어디로 확대해 들어갔든 한 번 클릭으로 처음 화면에 돌아온다.
# 이모지(🏠)는 plotly 트리맵 경로줄에서 글자가 깨져 나와 쓰지 않는다.
path = ([px.Constant("전체"), "sector", "industry", "label"]
        if depth.startswith("섹터 > 산업")
        else [px.Constant("전체"), "sector", "label"])

# Finviz 풍 색: -3% 빨강 ~ 0 진회색 ~ +3% 초록 (기간이 길면 스케일 자동 확대)
span = max(3.0, float(np.nanpercentile(np.abs(df["chg"]), 90)))
fig = px.treemap(
    df, path=path, values="mcap", color="chg",
    color_continuous_scale=["#e74c3c", "#3d3d3d", "#2ecc71"],
    range_color=(-span, span),
    custom_data=["name", "chg_txt", "mcap"],
    height=760,
)
fig.update_traces(
    texttemplate="<b>%{label}</b><br>%{customdata[1]}",
    hovertemplate="<b>%{customdata[0]}</b> (%{label})<br>"
                  "수익률: %{customdata[1]}<br>"
                  "시가총액: $%{customdata[2]:,.0f}<extra></extra>",
    textfont=dict(size=15),
    marker=dict(cornerradius=2),
    # 상단 경로줄(뒤로가기 내비게이션)을 크고 두껍게 — 축소가 안 보인다는 불편 해소
    pathbar=dict(visible=True, thickness=34, textfont=dict(size=16)),
)
fig.update_layout(margin=dict(t=44, l=0, r=0, b=0),
                  coloraxis_colorbar=dict(title="%"))
st.plotly_chart(fig, use_container_width=True)
st.caption("확대: 네모 클릭 · **축소: 맨 위 경로줄에서 「전체」(처음으로) 또는 상위 이름 클릭** · "
           "한 단계씩 돌아가려면 경로줄의 바로 왼쪽 항목을 누르면 된다")

# 요약 통계 — 그림이 주는 인상을 숫자로 검증할 수 있게
up = int((df["chg"] > 0).sum())
down = int((df["chg"] < 0).sum())
wavg = float(np.average(df["chg"], weights=df["mcap"]))
med = float(df["chg"].median())
s1, s2, s3, s4 = st.columns(4)
s1.metric("상승 / 하락", f"{up} / {down}")
s2.metric("시총가중 평균", f"{wavg:+.2f}%")
s3.metric("중앙값", f"{med:+.2f}%",
          help="시총가중 평균과 부호가 다르면 대형주와 나머지가 따로 움직인다는 뜻")
s4.metric("최고 / 최저",
          f"{df.loc[df['chg'].idxmax(), 'ticker']} {df['chg'].max():+.1f}% / "
          f"{df.loc[df['chg'].idxmin(), 'ticker']} {df['chg'].min():+.1f}%")

st.caption(f"기준: {dt.date.today()} 실행 · 가격 yfinance(지연 시세) · "
           f"섹터·시총 캐시 {META_MAX_AGE_DAYS}일 유지 · 구성종목 위키피디아 기준 — "
           "정보 제공 목적이며 투자 권유가 아닙니다.")
