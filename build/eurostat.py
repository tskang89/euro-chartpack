# -*- coding: utf-8 -*-
"""Eurostat 배포 API 에서 시계열을 가져온다.

한 번 부를 때 나라를 모두 넣는다. 계열 30개 × 나라 9개를 따로 부르면 270번인데,
geo 를 여러 개 붙이면 30번으로 끝난다. Eurostat 은 같은 이름의 인자를 여러 번
받아 준다.

응답은 JSON-stat 이다. 값이 다차원 배열을 한 줄로 편 dict 로 오고, 키는 정수
위치다. 그래서 차원 크기로 자리를 되짚어야 어느 나라 어느 시점인지 알 수 있다.
"""

from __future__ import annotations

import time
import urllib.parse

import requests

BASE = ("https://ec.europa.eu/eurostat/api/dissemination"
        "/statistics/1.0/data/{dataset}")
TIMEOUT = 60
RETRIES = 4
PACE = 0.4          # 연속 호출 사이 간격. 배치 작업이라 서두를 이유가 없다.


class EurostatError(RuntimeError):
    pass


def fetch(dataset: str, geos: list[str], since: str | None = None,
          **filters) -> dict:
    """원본 JSON-stat 응답."""
    params: list[tuple[str, str]] = [("format", "JSON"), ("lang", "EN")]
    for g in geos:
        params.append(("geo", g))
    if since:
        params.append(("sinceTimePeriod", since))
    for k, v in filters.items():
        for one in (v if isinstance(v, (list, tuple)) else [v]):
            params.append((k, str(one)))

    url = BASE.format(dataset=dataset) + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return resp.json()
        # 429·5xx 는 잠시 뒤 다시. 400 은 질의가 틀린 것이라 다시 해도 같다.
        if resp.status_code < 500 and resp.status_code != 429:
            raise EurostatError(
                f"{dataset}: {resp.status_code} {resp.text[:200]}")
        last = f"{resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise EurostatError(f"{dataset}: {RETRIES}번 시도했으나 실패 ({last})")


def decode(doc: dict) -> dict[tuple, float]:
    """JSON-stat 을 {(차원코드, ...): 값} 으로 편다. 키 순서는 doc['id'] 와 같다."""
    dims = doc["id"]
    sizes = doc["size"]

    # 각 차원의 '자리 -> 코드' 표와, 평평한 색인에서의 보폭
    codes: list[list[str]] = []
    for dim in dims:
        index = doc["dimension"][dim]["category"]["index"]
        if isinstance(index, list):                  # 크기 1이면 list 로 오기도 한다
            codes.append(list(index))
        else:
            back = {pos: code for code, pos in index.items()}
            codes.append([back[i] for i in range(len(back))])

    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    out: dict[tuple, float] = {}
    for flat, value in doc["value"].items():
        if value is None:
            continue
        rest, key = int(flat), []
        for i in range(len(sizes)):
            key.append(codes[i][rest // strides[i]])
            rest %= strides[i]
        out[tuple(key)] = value
    return out


def by_geo_time(doc: dict) -> dict[str, dict[str, float]]:
    """{geo: {기간: 값}}. geo·time 을 뺀 나머지 차원은 하나로 좁혀져 있다고 본다."""
    dims = doc["id"]
    gi, ti = dims.index("geo"), dims.index("time")
    out: dict[str, dict[str, float]] = {}
    for key, value in decode(doc).items():
        out.setdefault(key[gi], {})[key[ti]] = value
    return out


def series(dataset: str, geos: list[str], since: str | None = None,
           **filters) -> dict[str, dict[str, float]]:
    """가장 흔한 쓰임 — {geo: {기간: 값}} 까지 한 번에."""
    return by_geo_time(fetch(dataset, geos, since, **filters))
