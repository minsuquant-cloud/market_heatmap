# -*- coding: utf-8 -*-
"""메타데이터(섹터·산업·시가총액) 자체 수집 — 앱 없이 터미널에서 미리 받아둔다.

용도
----
- 앱 첫 실행이 느린 게 싫으면 이걸 먼저 돌려 캐시를 만들어 둔다.
- 작업 스케줄러에 등록하면 매주 자동 갱신도 가능하다.
- 앱(heatmap_app.py)과 같은 캐시 파일을 쓰므로 서로 그대로 이어진다.

사용법
------
    python collect_meta.py                 # 나스닥 100
    python collect_meta.py --universe spx  # S&P 500
    python collect_meta.py --all           # 둘 다

출력: results/heatmap_meta_ndx.csv · results/heatmap_meta_spx.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)

UNIVERSES = {
    "ndx": {
        "label": "나스닥 100",
        "url": "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
        "cache": RESULTS / "heatmap_meta_ndx.csv",
    },
    "spx": {
        "label": "S&P 500",
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "cache": RESULTS / "heatmap_meta_spx.csv",
    },
}


def fetch_tickers(url: str) -> list[str]:
    """위키피디아 구성종목 표 → 티커 목록 (UA 헤더 없으면 위키가 403)."""
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    for t in pd.read_html(io.StringIO(r.text)):
        cols = [str(c) for c in t.columns]
        for col in ("Ticker", "Symbol"):
            if col in cols and len(t) > 50:
                ticks = (t[col].astype(str).str.strip()
                         .str.replace(".", "-", regex=False))   # BRK.B → BRK-B
                return sorted(ticks.unique().tolist())
    raise RuntimeError(f"구성종목 표를 찾지 못함: {url}")


def collect(key: str) -> None:
    cfg = UNIVERSES[key]
    print(f"\n=== {cfg['label']} ===")
    tickers = fetch_tickers(cfg["url"])
    print(f"구성종목 {len(tickers)}개 확인. 종목별 섹터·시가총액 수집 시작…")

    rows, failed = [], []
    t0 = time.time()
    for i, t in enumerate(tickers, 1):
        try:
            info = yf.Ticker(t).info
            rows.append({
                "ticker": t,
                "name": info.get("shortName") or t,
                "sector": info.get("sector") or "기타",
                "industry": info.get("industry") or "기타",
                "mcap": info.get("marketCap"),
            })
        except Exception:
            failed.append(t)
        # 진행 표시 (같은 줄 덮어쓰기)
        el = time.time() - t0
        eta = el / i * (len(tickers) - i)
        sys.stdout.write(f"\r  {i}/{len(tickers)}  경과 {el:4.0f}초  남은 예상 {eta:4.0f}초")
        sys.stdout.flush()
    print()

    meta = pd.DataFrame(rows)
    n_no_cap = int(meta["mcap"].isna().sum()) if len(meta) else 0
    # 수집이 전멸했을 때 빈 파일로 기존 캐시를 덮어쓰지 않는다
    # (네트워크 장애 한 번에 애써 모은 메타가 날아가던 문제)
    if len(meta):
        meta.to_csv(cfg["cache"], index=False)
        print(f"저장: {cfg['cache']}  ({len(meta)}종목)")
    else:
        print(f"✖ 수집 결과 0종목 — 기존 캐시를 보존하고 저장하지 않음: {cfg['cache']}")
    # 실패를 조용히 넘기지 않는다
    if failed:
        print(f"⚠ 수집 실패 {len(failed)}종목: {', '.join(failed[:10])}"
              + (" …" if len(failed) > 10 else ""))
    if n_no_cap:
        print(f"⚠ 시가총액 미상 {n_no_cap}종목 (앱에서 제외 표시됨)")


def main():
    ap = argparse.ArgumentParser(description="히트맵 메타데이터 자체 수집")
    ap.add_argument("--universe", choices=list(UNIVERSES), default="ndx",
                    help="ndx=나스닥100(기본) · spx=S&P500")
    ap.add_argument("--all", action="store_true", help="두 유니버스 모두 수집")
    args = ap.parse_args()

    targets = list(UNIVERSES) if args.all else [args.universe]
    for key in targets:
        collect(key)
    print("\n완료 — 앱을 켜면 이 캐시를 바로 사용합니다 (7일 유지).")


if __name__ == "__main__":
    main()
