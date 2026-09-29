# -*- coding: utf-8 -*-
"""진행 중인 달을 최근일 값으로 채운다.

월간 계열은 그달이 끝나야 값이 나온다. 그래서 9월 말에 차트를 열면 오른쪽
끝이 8월이다. 환율·주가·미국 국채금리는 날마다 값이 있으니, 진행 중인 달
칸에 최근일 값을 넣고 그 날짜를 축에 적는다 — '26.09' 대신 '9.29'.

날짜를 적는 것이 핵심이다. 지난 달들은 월평균(환율·금리)이거나 월말
종가(주가)인데 마지막 점은 하루치다. 축 이름이 달라지면 그 차이가 눈에
들어온다. 숨기고 이어 붙이면 없는 움직임을 만든 것이 된다.

무엇을 채우고 무엇을 안 채우는가 — 이어 붙여도 되는지 달마다 견줘 보고
정했다.

  주가        같은 Yahoo 종가다. 진행 중인 달은 '지금까지의 종가'다.
  환율        같은 ECB 기준환율이다. 대미달러 환율만 OECD 월평균이라
              출처가 다른데, ECB 일별을 교차(자국통화÷달러)해 월평균을
              내 보니 엔·위안은 소수점까지, 원은 0.1% 안에서 같았다.
  미국 10년물 Yahoo ^TNX 의 월평균이 OECD 계열과 14개월 내내 1bp 안에서
              같았다. 같은 계열로 봐도 된다.

  유로지역 10년물은 채우지 않는다. Maastricht 수렴기준 금리는 정의 자체가
  월평균이라 일별 판이 없다. 분데스방크가 내는 일별 독일 금리(Svensson
  곡선)를 대신 쓸까 했으나, 8월 평균이 3.25 로 Eurostat 의 3.19 와 6bp
  어긋난다 — 다른 계열이다. 이어 붙이면 없는 금리 변동이 생긴다.
"""

from __future__ import annotations

import datetime
import time

import requests

import ecb

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEOUT = 30
PACE = 0.7
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class DailyError(RuntimeError):
    pass


# ------------------------------------------------------------------ Yahoo
def yahoo_last(symbol: str) -> tuple[str, float]:
    """최근 거래일의 종가. (날짜, 값).

    날짜는 거래소 현지 기준이다. 유닉스 시각을 그냥 UTC 로 읽으면 아시아
    증시가 하루 앞당겨진다 — meta.gmtoffset 을 더해야 한다. 월별 집계에서
    이미 한 번 겪은 일이다(stocks.py).
    """
    last = None
    for attempt in range(3):
        try:
            resp = requests.get(CHART.format(symbol=symbol),
                                params={"range": "10d", "interval": "1d"},
                                timeout=TIMEOUT, headers={"User-Agent": UA})
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _yahoo_parse(resp.json(), symbol)
        last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise DailyError(f"{symbol}: {last}")


def _yahoo_parse(doc: dict, symbol: str) -> tuple[str, float]:
    res = ((doc.get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise DailyError(f"{symbol}: 응답에 값이 없다")
    meta = res.get("meta", {})
    off = meta.get("gmtoffset", 0) or 0
    closes = res["indicators"]["quote"][0]["close"]
    rows = [(t + off, c) for t, c in zip(res["timestamp"], closes)
            if c is not None]
    if not rows:
        raise DailyError(f"{symbol}: 최근 10일에 종가가 없다")
    if _still_open(meta) and len(rows) > 1:
        # 장중이면 오늘 봉은 아직 종가가 아니라 그 순간의 값이다. 그것을
        # '9.29 종가'라 적으면 틀린 말이 된다. 마감된 직전 거래일을 쓴다.
        rows = rows[:-1]
    ts, close = rows[-1]
    day = datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%d")
    return day, float(close)


def _still_open(meta: dict) -> bool:
    """지금 그 거래소의 정규장이 열려 있는가.

    야후가 주는 currentTradingPeriod.regular 의 시작·끝(유닉스 시각)과 지금을
    견준다. 정보가 없으면 '닫혔다'고 본다 — 값을 버리는 쪽이 아니라 쓰는
    쪽으로 기울여야 차트가 비지 않는다.
    """
    reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    start, end = reg.get("start"), reg.get("end")
    if start is None or end is None:
        return False
    now = time.time()
    return start <= now < end


# ------------------------------------------------------------------ ECB 환율
def ecb_last(currency: str, since: str) -> tuple[str, float]:
    """1유로당 해당 통화, 최근 고시일 기준."""
    rows = ecb.series("EXR", f"D.{currency}.EUR.SP00.A", since)
    if not rows:
        raise DailyError(f"EXR {currency}: 값이 없다")
    day = max(rows)
    return day, rows[day]


def ecb_cross_last(currency: str, since: str) -> tuple[str, float]:
    """1달러당 해당 통화. ECB 기준환율 둘을 교차해 낸다.

    OECD 가 내는 대미달러 환율과 같은 값인지 2026-05~08 로 견줘 봤다.
    엔·위안은 소수점까지, 원은 0.1% 안에서 같았다.
    """
    loc = ecb.series("EXR", f"D.{currency}.EUR.SP00.A", since)
    usd = ecb.series("EXR", "D.USD.EUR.SP00.A", since)
    both = sorted(set(loc) & set(usd))
    if not both:
        raise DailyError(f"EXR {currency}/USD: 겹치는 날이 없다")
    day = both[-1]
    return day, loc[day] / usd[day]
