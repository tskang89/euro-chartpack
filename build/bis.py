# -*- coding: utf-8 -*-
"""BIS 에서 각국 중앙은행 정책금리를 가져온다.

OECD 에도 단기금리가 있지만 그것은 콜금리·은행간금리라 정책금리 그 자체가
아니고, 중국이 빠진다. BIS 의 WS_CBPOL 은 중앙은행이 정한 금리를 그대로 내고
중국(LPR)까지 들어 있다.

믿을 만한지 확인한 방법: 유로지역(XM)을 같이 받아 ECB 예금금리와 견줬더니
2.00 -> 2.25 까지 한 자리도 다르지 않았다.

주의: Accept 헤더를 정확히 'application/vnd.sdmx.data+json' 으로 줘야 한다.
버전을 덧붙이면(;version=1.0.0) 406 이 온다. 응답 구조도 OECD 와 달라서
값이 계열별로 묶여 있고 차원이 series / observation 으로 갈라져 있다.
"""

from __future__ import annotations

import time

import requests

BASE = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/{key}"
TIMEOUT = 90
RETRIES = 3
PACE = 0.4

# 화면 블록 -> BIS 지역 코드. 유로지역은 XM 이다.
AREAS = {"US": "US", "CN": "CN", "JP": "JP", "KR": "KR"}


class BisError(RuntimeError):
    pass


def policy_rates(areas: list[str], start: str) -> dict[str, dict[str, float]]:
    """{지역: {YYYY-MM: 정책금리}}. 월별."""
    key = "M." + "+".join(areas)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(
                BASE.format(key=key), params={"startPeriod": start},
                timeout=TIMEOUT,
                headers={"Accept": "application/vnd.sdmx.data+json"})
        except requests.RequestException as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _parse(resp.json())
        last = f"HTTP {resp.status_code}"
        time.sleep(3 * (attempt + 1))
    raise BisError(f"정책금리 {key}: {RETRIES}번 시도했으나 실패 ({last})")


def _parse(doc: dict) -> dict[str, dict[str, float]]:
    data = doc.get("data") or doc
    sets = data.get("dataSets") or []
    struct = data.get("structure") or {}
    if not sets or not struct:
        raise BisError("응답에 값이 없다")
    dims = struct["dimensions"]
    names = [x["id"] for x in dims["series"]]
    codes = [[v["id"] for v in x["values"]] for x in dims["series"]]
    times = [v["id"] for v in dims["observation"][0]["values"]]

    out: dict[str, dict[str, float]] = {}
    for key, series in sets[0]["series"].items():
        lab = {names[i]: codes[i][int(p)] for i, p in enumerate(key.split(":"))}
        rows = {}
        for pos, value in series["observations"].items():
            v = value[0]
            if v is None:
                continue
            # 문자열로 오는 일이 있다.
            rows[times[int(pos)]] = float(v)
        out[lab["REF_AREA"]] = rows
    return out
