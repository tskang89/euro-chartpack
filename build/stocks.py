# -*- coding: utf-8 -*-
"""주가지수 월말 종가.

여기만 공식 통계가 아니다. Eurostat 에도 ECB 에도 개별국 주가지수는 없다.
OECD 는 9개 지역을 다 내주지만 '월평균 지수(2015=100)'라서 월말 종가와는
다른 물건이다 — 지금 차트의 뜻이 바뀐다. Stooq 는 자바스크립트 작업증명을
요구해 스크립트로 못 받는다. 그래서 Yahoo 를 쓴다.

비공식 경로라 언제든 막힐 수 있다. 막히면 그 달을 비워 두고 빌드 로그에
크게 남긴다. 조용히 옛 숫자를 최신인 척 보여 주는 것보다 빈칸이 낫다.

시간대 함정: Yahoo 의 월봉 타임스탬프는 그 달 첫 거래일 00:00 '거래소 현지
시각'이다. UTC 로 그냥 바꾸면 서머타임 때 전달로 밀려 한 달씩 어긋난다
(2026-06 값이 2026-05 에 붙는다). meta.gmtoffset 을 더해야 한다.
"""

from __future__ import annotations

import datetime
import time

import requests

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEOUT = 30
RETRIES = 3
PACE = 0.8
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")

# 화면 블록 -> 지수. 수준이 저장값과 맞는지 확인하고 넣은 것이다.
SYMBOLS = {
    "EZ": "^STOXX50E",   # EURO STOXX 50
    "DE": "^GDAXI",      # DAX
    "FR": "^FCHI",       # CAC 40
    "IT": "FTSEMIB.MI",  # FTSE MIB
    "ES": "^IBEX",       # IBEX 35
    "NL": "^AEX",        # AEX
    "BE": "^BFX",        # BEL 20
    "IE": "^ISEQ",       # ISEQ Overall
    "AT": "^ATX",        # ATX
}


class StockError(RuntimeError):
    pass


def monthly_close(symbol: str, start: str, end: str) -> dict[str, float]:
    """{YYYY-MM: 월말 종가}. start·end 는 'YYYY-MM'."""
    p1 = int(datetime.datetime(int(start[:4]), int(start[5:7]), 1,
                               tzinfo=datetime.UTC).timestamp()) - 86400 * 40
    ey, em = int(end[:4]), int(end[5:7])
    p2 = int(datetime.datetime(ey + (em // 12), em % 12 + 1, 1,
                               tzinfo=datetime.UTC).timestamp())

    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(
                CHART.format(symbol=requests.utils.quote(symbol, safe="")),
                params={"interval": "1mo", "period1": p1, "period2": p2},
                headers={"User-Agent": UA}, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _parse(resp.json(), symbol)
        last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise StockError(f"{symbol}: {RETRIES}번 시도했으나 실패 ({last})")


def _parse(doc: dict, symbol: str) -> dict[str, float]:
    result = (doc.get("chart") or {}).get("result") or []
    if not result:
        err = ((doc.get("chart") or {}).get("error") or {}).get("description")
        raise StockError(f"{symbol}: 값이 없다 ({err or '응답이 비었다'})")
    r = result[0]
    offset = r.get("meta", {}).get("gmtoffset", 0)      # 위 '시간대 함정' 참고
    closes = r["indicators"]["quote"][0]["close"]
    out: dict[str, float] = {}
    for stamp, close in zip(r["timestamp"], closes):
        if close is None:
            continue
        month = datetime.datetime.fromtimestamp(
            stamp + offset, datetime.UTC).strftime("%Y-%m")
        out[month] = close
    if not out:
        raise StockError(f"{symbol}: 종가가 하나도 없다")
    return out


def all_closes(start: str, end: str, log=print) -> dict[str, dict[str, float]]:
    """{블록: {월: 종가}}. 한 지수가 실패해도 나머지는 계속 받는다."""
    out: dict[str, dict[str, float]] = {}
    for block, symbol in SYMBOLS.items():
        try:
            out[block] = monthly_close(symbol, start, end)
        except StockError as exc:
            log(f"  [경고] 주가지수 {block} ({symbol}) — {exc}")
    return out
