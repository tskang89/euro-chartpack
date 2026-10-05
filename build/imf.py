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

# 일반정부 지출·수입. 유로지역 집계까지 한 출처로 덮으려고 여기서 받는다
# (2026-10-05). Eurostat 에도 gov_10a_main 이 있지만, 그러면 유로 탭과 해외
# 탭의 출처가 갈려 같은 그림을 두 기준으로 보게 된다.
#
# 코드 이름이 헷갈린다. 'GGX_GDP'·'exp' 도 비슷한 이름으로 있는데 전자는
# 우리가 보는 나라가 하나도 없고(67개국뿐) 후자는 2024년에서 멈춰 있다.
# 아래 둘만 13개 블록을 모두, 지난해까지 빠짐없이 덮는다.
EXPEND = "G_X_G01_GDP_PT"   # 일반정부 총지출, GDP 대비 %
REVENUE = "GGR_G01_GDP_PT"  # 일반정부 총수입, GDP 대비 %
GDP_USD = "NGDPD"           # 명목 GDP, 10억 달러

# 달러 금액은 IMF 가 따로 내주지 않는다. 'GDP 대비 %' × '달러 GDP' 로 낸다 —
# 환율을 끌어다 쓰는 것보다 정확하다. 두 값이 같은 WEO 판에서 나오므로
# 분모가 어긋날 일이 없다.
#
# 유로지역 집계는 'EURO' 다. 'EA' 는 없고, 'EU' 는 있지만 재정 지표가 비어
# 있다(2026-10-05 확인). EU 와 유로지역은 범위가 다르므로 섞어서도 안 된다.
ALL_AREAS = {
    "EZ": "EURO", "DE": "DEU", "FR": "FRA", "IT": "ITA", "ES": "ESP",
    "NL": "NLD", "BE": "BEL", "IE": "IRL", "AT": "AUT",
    "US": "USA", "CN": "CHN", "JP": "JPN", "KR": "KOR",
}


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
