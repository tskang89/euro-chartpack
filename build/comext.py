# -*- coding: utf-8 -*-
"""Comext(DS-045409) 에서 나라 대 나라 교역액을 가져온다.

Eurostat 의 보통 배포 API 와 **경로가 다르다**. /statistics/ 앞에 /comext/ 가
붙고, 인자 이름도 geo 가 아니라 reporter·partner·product·flow 다. 그래서
eurostat.py 를 그대로 못 쓴다.

  flow=1 수입, flow=2 수출   (Comext 관례. 헷갈리기 쉬워 상수로 둔다)
  indicators=VALUE_IN_EUROS  유로 단위 금액. 백만이 아니라 낱 유로다.

월별 양자 교역은 여기 말고 받을 데가 없다. ei_eteu27_2020_m 은 상대가
집계(WORLD·EXT_EU27)뿐이고, ext_lt_maineu 는 상대가 232개국이지만 연간이다.
연간 금액에 연평균 환율을 곱하면 월별로 환산해 더한 값과 달라진다.
"""

from __future__ import annotations

import time

import requests

BASE = ("https://ec.europa.eu/eurostat/api/comext/dissemination"
        "/statistics/1.0/data/DS-045409")
TIMEOUT = 120
RETRIES = 3
PACE = 0.5

IMPORT, EXPORT = "1", "2"


class ComextError(RuntimeError):
    pass


def monthly_value(reporter: str, partner: str, flow: str,
                  since: str) -> dict[str, float]:
    """{YYYY-MM: 유로 금액}. product 는 전 품목(TOTAL)."""
    params = {
        "format": "JSON", "lang": "EN",
        "reporter": reporter, "partner": partner, "product": "TOTAL",
        "flow": flow, "freq": "M", "indicators": "VALUE_IN_EUROS",
        "sinceTimePeriod": since,
    }
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(BASE, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _decode(resp.json(), f"{reporter}-{partner}")
        if resp.status_code < 500 and resp.status_code != 429:
            raise ComextError(f"{reporter}-{partner}: "
                              f"{resp.status_code} {resp.text[:160]}")
        last = str(resp.status_code)
        time.sleep(2 * (attempt + 1))
    raise ComextError(f"{reporter}-{partner}: {RETRIES}번 시도했으나 실패 ({last})")


def _decode(doc: dict, label: str) -> dict[str, float]:
    """JSON-stat 이지만 차원 이름이 달라 시간 축만 되짚으면 된다."""
    if not doc.get("value"):
        raise ComextError(f"{label}: 값이 없다")
    dims, sizes = doc["id"], doc["size"]
    ti = dims.index("time")
    back = {pos: code
            for code, pos in doc["dimension"]["time"]["category"]["index"].items()}
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    out: dict[str, float] = {}
    for flat, value in doc["value"].items():
        if value is None:
            continue
        rest, key = int(flat), []
        for i in range(len(sizes)):
            key.append(rest // strides[i])
            rest %= strides[i]
        out[back[key[ti]]] = value
    return out
