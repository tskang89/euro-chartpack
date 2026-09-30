# -*- coding: utf-8 -*-
"""OECD SDMX 에서 유로지역 밖 나라의 시계열을 가져온다.

Eurostat 은 EU 밖을 내지 않는다. 미국·중국·일본·한국은 여기서 받는다.

SDMX-JSON 은 Eurostat 의 JSON-stat 과 구조가 다르다. 값이 "3:1:0:2:..." 처럼
차원 자리를 콜론으로 이은 키에 달려 있어서, 자리마다 코드표를 되짚어야 한다.

주의할 것 둘.

  500 이 자주 난다. 자료가 없어서가 아니라 뽑는 양이 많을 때 그렇다. 기간을
  좁히거나 잠시 뒤 다시 하면 된다. 그래서 재시도를 넣었다.

  같은 지표라도 나라마다 있는 조합이 다르다. 일본은 KEI 에 소비자물가가 없고
  중국은 실업률이 없다. 없는 것을 0 으로 채우지 않고 빈칸으로 둔다.
"""

from __future__ import annotations

import time

import requests

BASE = "https://sdmx.oecd.org/public/rest/data/{flow}/{key}"
TIMEOUT = 120
RETRIES = 4
PACE = 0.6

KEI = "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0"
FINMARK = "OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0"
# 분기 국민계정. 나라를 키로 좁히면 500 이 나고 "all" 로 받아 걸러야 한다.
QNA_G20 = "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20,1.1"
# 연간 인구. OECD 회원국만 있어 중국이 빠진다.
POP = "OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE3_POP_EMPNC,2.0"
# 물가는 분류 개편 때문에 나라마다 흐름이 갈린다. sources.OECD_FALLBACK 참고.
PRICES_99 = "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0"
PRICES_18 = "OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL,1.0"
# 국제수지. UNIT_MEASURE=USD_EXC 가 시장환율 기준 달러다(PPP 아님).
BOP = "OECD.SDD.TPS,DSD_BOP@DF_BOP,1.0"
# 주택가격. 지수로 오므로 전년비 상승률은 빌드에서 만든다.
HOUSE = "OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,1.0"


# 한 나라·한 기간에 값이 둘 이상 온 자리. series() 가 채우고 build.py 가
# 로그로 내보낸다. 거기서 ops 덩어리를 타고 주간 점검까지 간다.
#
# 이것을 두는 까닭은 조용히 틀리는 고장을 막기 위해서다. SDMX 는 차원을
# 덜 좁혀도 200 으로 응답하고 여러 계열을 함께 준다. 받는 쪽이 딕셔너리에
# 넣으면 마지막 것만 남는데, 그 '마지막'은 응답 순서에 달려 있어 나라마다
# 다른 계열이 실릴 수도 있다. 값이 있으므로 차트는 멀쩡해 보인다.
CLASHES: list[str] = []


class OecdError(RuntimeError):
    pass


def fetch(flow: str, key: str, start: str, end: str | None = None) -> dict:
    params = {"startPeriod": start, "dimensionAtObservation": "AllDimensions"}
    if end:
        params["endPeriod"] = end
    url = BASE.format(flow=flow, key=key)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(
                url, params=params, timeout=TIMEOUT,
                headers={"Accept": "application/vnd.sdmx.data+json"})
        except requests.RequestException as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return resp.json()
        if resp.status_code == 404:
            raise OecdError(f"{flow} {key}: 그런 계열이 없다 (404)")

        last = f"HTTP {resp.status_code}"
        if resp.status_code == 429:
            # 호출 제한. 3초씩 쉬는 정도로는 안 풀린다 — 한 번 걸리면 뒤따르는
            # 계열이 줄줄이 같이 넘어진다. Retry-After 가 오면 그만큼 기다리고,
            # 없으면 20초부터 배로 늘린다.
            wait = int(resp.headers.get("Retry-After") or 0) or 20 * (2 ** attempt)
            time.sleep(min(wait, 180))
            continue
        time.sleep(3 * (attempt + 1))
    raise OecdError(f"{flow} {key}: {RETRIES}번 시도했으나 실패 ({last})")


def decode(doc: dict) -> dict[tuple, float]:
    """{(차원코드, ...): 값}. 키 순서는 응답의 차원 순서와 같다."""
    struct = doc["data"]["structures"][0]["dimensions"]["observation"]
    codes = [[v["id"] for v in dim["values"]] for dim in struct]
    out: dict[tuple, float] = {}
    for flat, value in doc["data"]["dataSets"][0]["observations"].items():
        v = value[0]
        if v is None:
            continue
        out[tuple(codes[i][int(pos)] for i, pos in enumerate(flat.split(":")))] = v
    return out


def series(flow: str, key: str, start: str, end: str | None = None,
           **match) -> dict[str, dict[str, float]]:
    """{REF_AREA: {기간: 값}}.

    match 에 준 차원은 그 값과 같은 관측만 남긴다. 예를 들어
    series(KEI, "USA+KOR.M...", "2021-09", MEASURE="CP", TRANSFORMATION="GY")
    """
    doc = fetch(flow, key, start, end)
    struct = doc["data"]["structures"][0]["dimensions"]["observation"]
    order = [d["id"] for d in struct]
    ai, ti = order.index("REF_AREA"), order.index("TIME_PERIOD")

    out: dict[str, dict[str, float]] = {}
    seen: dict[tuple[str, str], tuple] = {}
    for tup, value in decode(doc).items():
        row = dict(zip(order, tup))
        if any(row.get(k) != v for k, v in match.items()):
            continue
        area, period = row[order[ai]], row[order[ti]]
        # 같은 나라·같은 기간에 값이 둘 이상 오면 차원이 덜 좁혀진 것이다.
        # 조용히 덮어쓰면 마지막에 온 것이 남는데, 그것이 무엇인지 아무도
        # 모른다. 실제로 산업생산에서 그랬다 — ACTIVITY 를 안 박아 두어
        # 건설업 지수가 '산업생산'이라는 이름을 달고 여러 달 나갔다.
        old = seen.get((area, period))
        if old is not None and out[area][period] != value:
            differ = [k for k in order
                      if dict(zip(order, old)).get(k) != row.get(k)
                      and k not in (order[ai], order[ti])]
            CLASHES.append(
                f"{flow.split(',')[-1]} {match} — {area} {period} 에 값이 둘 "
                f"({out[area][period]} vs {value}). 갈리는 차원: "
                f"{'·'.join(differ) or '알 수 없음'}")
        seen[(area, period)] = tup
        out.setdefault(area, {})[period] = value
    return out
