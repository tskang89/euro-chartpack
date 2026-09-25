# -*- coding: utf-8 -*-
"""ECB Data Portal 에서 환율과 정책금리를 가져온다.

Eurostat 과 달리 키가 점으로 이어진 한 줄이다(EXR.M.USD.EUR.SP00.A).
자리마다 뜻이 정해져 있어서, 틀리면 빈 응답이 오지 오류가 나지 않는다.
그래서 받은 뒤에 개수를 꼭 본다.
"""

from __future__ import annotations

import time

import requests

BASE = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
TIMEOUT = 60
RETRIES = 4
PACE = 0.3


class EcbError(RuntimeError):
    pass


def series(flow: str, key: str, start: str | None = None) -> dict[str, float]:
    """{기간: 값}. 기간 표기는 흐름에 따라 2026-08 이거나 2026-08-31 이다."""
    params = {"format": "jsondata"}
    if start:
        params["startPeriod"] = start

    url = BASE.format(flow=flow, key=key)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT,
                                headers={"Accept": "application/json"})
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _parse(resp.json(), f"{flow}/{key}")
        if resp.status_code == 404:
            raise EcbError(f"{flow}/{key}: 그런 계열이 없다 (404)")
        if resp.status_code < 500 and resp.status_code != 429:
            raise EcbError(f"{flow}/{key}: {resp.status_code} {resp.text[:160]}")
        last = str(resp.status_code)
        time.sleep(2 * (attempt + 1))
    raise EcbError(f"{flow}/{key}: {RETRIES}번 시도했으나 실패 ({last})")


def _parse(doc: dict, label: str) -> dict[str, float]:
    sets = doc.get("dataSets") or []
    if not sets or not sets[0].get("series"):
        raise EcbError(f"{label}: 응답에 값이 없다. 키 자리가 틀렸을 수 있다.")
    obs = list(sets[0]["series"].values())[0]["observations"]
    times = doc["structure"]["dimensions"]["observation"][0]["values"]
    out = {}
    for pos, values in obs.items():
        v = values[0]
        if v is not None:
            out[times[int(pos)]["id"]] = v
    return out


# ------------------------------------------------------------------ 쓰기 좋은 꼴
def monthly_fx(currency: str, start: str) -> dict[str, float]:
    """월평균 기준환율. 1유로당 해당 통화."""
    return series("EXR", f"M.{currency}.EUR.SP00.A", start)


def annual_fx(currency: str, start: str) -> dict[str, float]:
    """연평균 기준환율."""
    return series("EXR", f"A.{currency}.EUR.SP00.A", start)


def quarterly_fx(currency: str, start: str) -> dict[str, float]:
    """분기평균 기준환율.

    ECB 가 내는 분기 계열을 그대로 쓴다. 월평균 석 달을 산술평균하면 값이
    미세하게 달라진다(2021-Q1 은 1.20485 대 1.20559). ECB 는 분기를 영업일
    기준으로 내는데 달마다 영업일 수가 다르기 때문이다. 그 차이가 경상수지
    달러 환산에서 0.1십억 달러씩 어긋나 저장값과 안 맞았다.
    """
    return series("EXR", f"Q.{currency}.EUR.SP00.A", start)


def policy_rates(start: str) -> dict[str, dict[str, float]]:
    """{'dfr': {날짜: 값}, 'mro': {날짜: 값}} — 일별 수준."""
    return {
        "dfr": series("FM", "D.U2.EUR.4F.KR.DFR.LEV", start),
        "mro": series("FM", "D.U2.EUR.4F.KR.MRR_FR.LEV", start),
    }


def month_end(daily: dict[str, float]) -> dict[str, float]:
    """일별 계열을 월말 값으로. 정책금리는 '그달 말 기준'으로 보여 준다."""
    out: dict[str, float] = {}
    for day in sorted(daily):
        out[day[:7]] = daily[day]          # 날짜순이라 마지막이 월말 값
    return out
