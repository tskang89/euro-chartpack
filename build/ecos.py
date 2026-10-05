# -*- coding: utf-8 -*-
"""한국은행 ECOS 에서 한국 통계를 가져온다.

유로지역 탭에는 품목별 소비자물가 막대가 있는데 한국 탭에는 없었다. OECD 는
한국의 헤드라인·근원만 주고 품목 구성을 주지 않는다. 품목별로 보려면 한국
통계를 직접 받아야 한다.

ECOS 는 무료지만 인증키가 있어야 한다(https://ecos.bok.or.kr/api/ → 인증키
신청). 키가 없으면 이 구획만 조용히 빠지고 나머지 차트팩은 그대로 만들어진다.

주의: ECOS 는 **지수**를 준다. 상승률은 여기서 전년동월과 견줘 낸다. 그래서
원하는 달보다 한 해 앞서부터 받아야 한다.
"""

from __future__ import annotations

import os
import time

import requests

BASE = ("https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/{rows}/"
        "{table}/{cycle}/{start}/{end}/{item}")
TIMEOUT = 60
RETRIES = 3
PACE = 0.25          # 연속 호출 사이 간격


class EcosError(RuntimeError):
    pass


def have_key() -> bool:
    return bool(os.environ.get("ECOS_API_KEY"))


def series(table: str, item: str, cycle: str,
           start: str, end: str, rows: int = 700) -> dict[str, float]:
    """{기간: 값}. 기간 표기는 주기에 따라 YYYYMM·YYYYMMDD 등 원문 그대로."""
    key = os.environ.get("ECOS_API_KEY")
    if not key:
        raise EcosError("ECOS_API_KEY 가 없다")
    url = BASE.format(key=key, rows=rows, table=table, cycle=cycle,
                      start=start, end=end, item=item)
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT,
                                headers={"Accept": "application/json"})
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code == 200:
                try:
                    doc = resp.json()
                except ValueError as exc:
                    # 한도를 넘으면 JSON 이 아닌 것이 200 으로 오기도 한다.
                    last = f"JSON 아님 ({exc})"
                    time.sleep(2 * (attempt + 1))
                    continue
                if "RESULT" in doc:          # 키가 틀렸거나 한도를 넘었다
                    code = doc["RESULT"].get("CODE", "")
                    msg = doc["RESULT"].get("MESSAGE", doc["RESULT"])
                    # INFO-200 은 '해당하는 데이터가 없습니다'인데, 자료가
                    # 정말 없을 때뿐 아니라 **호출이 몰려 막혔을 때도** 같은
                    # 것이 온다. 둘을 가릴 길이 응답에 없으므로 한 번 쉬었다
                    # 다시 묻는다 — 돌아오면 막혔던 것이다.
                    #
                    # 2026-10-05 에 10년물 국채금리가 이것으로 떨어졌다.
                    # 같은 빌드의 다른 ECOS 호출은 멀쩡했고, 몇 시간 전
                    # 빌드에서는 같은 계열이 들어왔다.
                    if code == "INFO-200" and attempt + 1 < RETRIES:
                        last = f"{code} {msg}"
                        time.sleep(3 * (attempt + 1))
                        continue
                    raise EcosError(msg)
                time.sleep(PACE)
                got = (doc.get("StatisticSearch") or {}).get("row") or []
                return {r["TIME"]: float(r["DATA_VALUE"]) for r in got
                        if r.get("DATA_VALUE") not in (None, "")
                        and r.get("TIME")}
            last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise EcosError(f"{table}/{item}: {last}")


def yoy(index: dict[str, float], month: str) -> float | None:
    """그 달의 전년동월비(%). 한 해 전 값이 없으면 None.

    ECOS 의 월 표기는 'YYYYMM' 이다. 문자열을 잘라 연도만 1 줄인다.
    """
    prev = f"{int(month[:4]) - 1}{month[4:]}"
    a, b = index.get(month), index.get(prev)
    if a is None or b in (None, 0):
        return None
    return (a / b - 1) * 100


def latest_month(index: dict[str, float]) -> str | None:
    """전년동월이 함께 있는 가장 최근 달."""
    for m in sorted(index, reverse=True):
        if f"{int(m[:4]) - 1}{m[4:]}" in index:
            return m
    return None
