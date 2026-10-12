# -*- coding: utf-8 -*-
"""세계은행에서 명목 GDP 와 총인구를 가져온다.

OECD 에도 연간 국민계정이 있지만 두 가지가 걸렸다.

  달러 계열이 PPP 기준이다. 시장환율 기준 명목 GDP 를 그대로 내주지 않는다.
  중국이 회원국 흐름에 없다. 인구는 2023년까지만 있다.

세계은행은 둘 다 해결한다. 시장환율 기준(NY.GDP.MKTP.CD)이고 중국도 다른
나라와 같은 자리에 있다. 키가 필요 없고 응답도 빠르다.

주의: 응답은 [메타, 자료] 두 칸짜리 배열이다. 자료가 없으면 둘째 칸이
null 로 온다 — 그때 [1] 을 그냥 꺼내면 터진다.
"""

from __future__ import annotations

import time

import requests

BASE = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"
TIMEOUT = 60
RETRIES = 3
PACE = 0.3

# 화면 블록 -> ISO3 코드
AREAS = {"US": "USA", "CN": "CHN", "JP": "JPN", "KR": "KOR"}

# 열세 블록 전부. 유로지역 집계는 EMU 다.
#
# GDP·인구는 유로지역 쪽을 Eurostat 에서 받으므로 위 AREAS(해외 넷)만 쓴다.
# 1인당 국민소득은 다르다 — 나라끼리 견주려고 보는 숫자이므로 한 잣대로
# 재야 한다. 유로 회원국만 Eurostat 으로 따로 받으면 환산 환율과 인구
# 정의가 달라져 견줄 수 없는 값이 된다(2026-10-12 소장님 지시).
ALL_AREAS = {"EZ": "EMU", "DE": "DEU", "FR": "FRA", "IT": "ITA", "ES": "ESP",
             "NL": "NLD", "BE": "BEL", "IE": "IRL", "AT": "AUT",
             "KR": "KOR", "US": "USA", "CN": "CHN", "JP": "JPN"}

GDP_USD = "NY.GDP.MKTP.CD"      # 명목 GDP, 경상 미달러 (시장환율)
POPULATION = "SP.POP.TOTL"      # 총인구

# 1인당 국민소득(GNI).
#
# 달러 계열은 Atlas 방식이다. 세계은행이 소득 분류에 쓰는 공식 계열이고,
# 환율 급변의 영향을 줄이려 3년 평균환율로 환산한다. 그래서 한국은행이
# 내는 1인당 GNI 와 끝자리가 조금 다르다(2024년 36,750 대 36,624달러).
# 시장환율 그대로의 1인당 값은 세계은행이 따로 내지 않으므로, GNI 총액을
# 인구로 내가 나누는 수밖에 없다 — 그러면 출처가 '내 계산' 이 된다.
# 공표된 계열을 그대로 쓰고 각주에 방식을 밝히는 쪽을 택했다.
GNI_PC = "NY.GNP.PCAP.CD"          # 1인당 GNI, Atlas 방식, 경상 미달러
GNI_PC_PPP = "NY.GNP.PCAP.PP.CD"   # 1인당 GNI, PPP, 경상 국제달러


class WorldBankError(RuntimeError):
    pass


def series(indicator: str, countries: list[str],
           start: str, end: str) -> dict[str, dict[str, float]]:
    """{ISO3: {연도: 값}}."""
    url = BASE.format(countries=";".join(countries), indicator=indicator)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT,
                                params={"format": "json",
                                        "date": f"{start}:{end}",
                                        "per_page": 500})
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            time.sleep(PACE)
            return _parse(resp.json(), indicator)
        last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise WorldBankError(f"{indicator}: {RETRIES}번 시도했으나 실패 ({last})")


def _parse(body, indicator: str) -> dict[str, dict[str, float]]:
    if not isinstance(body, list) or len(body) < 2 or not body[1]:
        raise WorldBankError(f"{indicator}: 응답에 값이 없다")
    out: dict[str, dict[str, float]] = {}
    for row in body[1]:
        value = row.get("value")
        if value is None:
            continue
        out.setdefault(row["countryiso3code"], {})[row["date"]] = float(value)
    if not out:
        raise WorldBankError(f"{indicator}: 값이 하나도 없다")
    return out
