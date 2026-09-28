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

# 연준은 금리를 점이 아니라 폭 25bp 의 목표범위로 정한다(예: 3.50~3.75%).
# BIS 는 그 중간값을 준다(3.625). 시장과 언론이 말하는 "미국 정책금리"는
# 상단이므로 여기서 상단으로 옮긴다 — 중간값 + 12.5bp.
#
# 범위 폭이 25bp 라는 전제 위에 서 있다. 2008년 이후 줄곧 그랬지만 전제는
# 전제다. 그래서 옮긴 값이 0.25 의 배수인지 검산하고, 아니면 손대지 않고
# 중간값을 그대로 둔 채 경고를 남긴다.
RANGE_UPPER = {"US": 0.125}
UPPER_STEP = 0.25


class BisError(RuntimeError):
    pass


def month_end(daily: dict[str, float]) -> dict[str, float]:
    """일별 계열을 월말 값으로. 날짜순이라 그달 마지막 관측이 남는다."""
    out: dict[str, float] = {}
    for day in sorted(daily):
        out[day[:7]] = daily[day]
    return out


MAX_FILL_MONTHS = 1


def fill_tail(rows: dict[str, float], months: list[str],
              area: str = "", log=print) -> dict[str, float]:
    """축 끝에 빈 달이 있으면 직전 금리로 채운다. 최대 한 달.

    BIS 가 나라마다 다른 속도로 싣는 탓에 생기는 구멍이다. 2026-09-28 에
    미국·유로·일본·중국은 9월 22일까지 와 있는데 한국은 8월 28일에서
    멈춰 있었다. 정책금리는 계단이라 바뀌기 전까지 직전 값이 그대로 효력을
    가지므로, 빈칸보다 직전 값이 사실에 가깝다.

    그래도 못 받은 구간에 결정이 있었다면 그것을 놓친다. 위험을 한 달로
    묶어 두고, 채웠다는 사실을 로그에 남긴다.
    """
    have = [m for m in months if rows.get(m) is not None]
    if not have or have[-1] == months[-1]:
        return rows
    gap = [m for m in months if m > have[-1]]
    if len(gap) > MAX_FILL_MONTHS:
        log(f"    └ {area} 정책금리가 {have[-1]} 에서 멈춰 있다 — {len(gap)}달은 "
            f"너무 멀어 채우지 않는다.")
        return rows
    out = dict(rows)
    for m in gap:
        out[m] = rows[have[-1]]
    log(f"    └ {area} 정책금리 {gap[0]} 은 아직 BIS 에 없다 — {have[-1]} 의 "
        f"{rows[have[-1]]} 를 그대로 둔다(바뀌기 전까지 유효).")
    return out


def policy_rates(areas: list[str], start: str) -> dict[str, dict[str, float]]:
    """{지역: {YYYY-MM: 정책금리}}.

    일별로 받아 월말 값을 쓴다. 월별 계열을 쓰면 두 가지가 늦는다.
      진행 중인 달이 통째로 없다. 9월 결정이 9월이 끝나야 보인다.
      이미 지난 달도 늦다 — 한국이 2026-08-28 에 3.00 으로 올렸는데 월별
      계열에는 그 달 값 자체가 없었다.
    ECB 금리도 같은 이유로 일별을 받아 월말을 쓰고 있다(ecb.py).
    """
    key = "D." + "+".join(areas)
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
            return {area: month_end(rows)
                    for area, rows in _parse(resp.json()).items()}
        last = f"HTTP {resp.status_code}"
        time.sleep(3 * (attempt + 1))
    raise BisError(f"정책금리 {key}: {RETRIES}번 시도했으나 실패 ({last})")


def to_upper(area: str, value: float, log=print) -> float:
    """목표범위를 쓰는 나라는 중간값을 상단으로 옮긴다."""
    shift = RANGE_UPPER.get(area)
    if shift is None:
        return value
    upper = value + shift
    # 상단은 0.25 의 배수여야 한다. 아니면 범위 폭이 달라진 것이다.
    if abs(round(upper / UPPER_STEP) * UPPER_STEP - upper) > 1e-6:
        log(f"  [경고] {area} 정책금리 {value} 를 상단으로 옮기면 {upper} 로 "
            f"0.25 의 배수가 아니다. 목표범위 폭이 바뀌었을 수 있다 — "
            f"중간값을 그대로 둔다.")
        return value
    return upper


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
