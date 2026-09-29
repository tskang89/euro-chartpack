# -*- coding: utf-8 -*-
"""INSEE 업황지수(climat des affaires)를 프랑스 통계청에서 직접 받는다.

INSEE 는 열린 SDMX 종점을 두고 있고 인증키가 필요 없다.

    https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/{IDBANK}

계열 번호는 INSEE 의 dataflow 목록에서 찾았다.
  001565530  전체(tous secteurs)      — CLIMAT-AFFAIRES
  001585934  제조업(industrie manufacturière) — ENQ-CONJ-ACT-IND
  001587025  서비스(services)          — ENQ-CONJ-SERV

셋 다 같은 눈금이다 — 장기평균 = 100. ifo 와 달리 부문별도 지수라 한 그림에
얹을 수 있다.

응답은 SDMX 2.1 StructureSpecificData(XML)다. 네임스페이스가 계열마다 달라
ElementTree 로 태그 이름을 그대로 읽는 편이 낫다.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import requests

BASE = "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/{idbank}"
TIMEOUT = 90
RETRIES = 3
PACE = 0.4
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class InseeError(RuntimeError):
    pass


def series(idbank: str) -> dict[str, float]:
    """{'YYYY-MM': 값}. 월간 계열을 전제한다."""
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(BASE.format(idbank=idbank), timeout=TIMEOUT,
                                headers={"User-Agent": UA})
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code == 200 and resp.content:
                time.sleep(PACE)
                return _parse(resp.content, idbank)
            last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise InseeError(f"{idbank}: {last}")


def _parse(raw: bytes, idbank: str) -> dict[str, float]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InseeError(f"{idbank}: XML 을 읽지 못했다 ({exc})") from exc
    out: dict[str, float] = {}
    for el in root.iter():
        if not el.tag.endswith("}Obs") and not el.tag.endswith("Obs"):
            continue
        period, value = el.get("TIME_PERIOD"), el.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            out[period] = float(value)
        except ValueError:
            continue
    if not out:
        raise InseeError(f"{idbank}: 관측이 하나도 없다")
    return out
