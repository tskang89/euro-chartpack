# -*- coding: utf-8 -*-
"""IMF DataMapper 에서 일반정부 재정 지표를 가져온다.

여기까지 오는 데 두 번 헛걸음을 했다.

  세계은행   중앙정부 기준이고 중국·일본이 통째로 비어 있다.
  OECD       국민계정에 일반정부(S13) 조합이 0건이다.

IMF 는 World Economic Outlook 을 DataMapper 로 내주는데, 키가 필요 없고
일반정부(general government) 기준이라 나라 사이 비교가 된다. 네 나라 모두
빈칸 없이 나온다.

응답은 {"values": {지표: {나라: {연도: 값}}}} 꼴이다. 연도가 문자열 키다.

주의: WEO 는 전망치를 함께 싣는다. 지난 연도까지만 쓰고 앞선 해는 가져오지
않는다 — 차트 축이 지난 5개년이라 자연히 그렇게 된다.
"""

from __future__ import annotations

import time

import requests

BASE = "https://www.imf.org/external/datamapper/api/v1/{indicator}/{countries}"
TIMEOUT = 60
RETRIES = 3
PACE = 0.3

AREAS = {"US": "USA", "CN": "CHN", "JP": "JPN", "KR": "KOR"}

DEBT = "GGXWDG_NGDP"        # 일반정부 총부채, GDP 대비 %
BALANCE = "GGXCNL_NGDP"     # 일반정부 순대출(+)/순차입(−), GDP 대비 %


class ImfError(RuntimeError):
    pass


def series(indicator: str, countries: list[str]) -> dict[str, dict[str, float]]:
    """{ISO3: {연도: 값}}."""
    url = BASE.format(indicator=indicator, countries="/".join(countries))
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
            return _parse(resp.json(), indicator)
        last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise ImfError(f"{indicator}: {RETRIES}번 시도했으나 실패 ({last})")


def _parse(body, indicator: str) -> dict[str, dict[str, float]]:
    values = (body or {}).get("values", {}).get(indicator)
    if not values:
        raise ImfError(f"{indicator}: 응답에 값이 없다")
    out: dict[str, dict[str, float]] = {}
    for area, rows in values.items():
        clean = {y: float(v) for y, v in (rows or {}).items() if v is not None}
        if clean:
            out[area] = clean
    if not out:
        raise ImfError(f"{indicator}: 값이 하나도 없다")
    return out
