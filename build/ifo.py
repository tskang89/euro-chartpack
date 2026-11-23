# -*- coding: utf-8 -*-
"""ifo 업황지수를 ifo 연구소에서 직접 받는다.

ifo 는 API 를 내지 않는다. 홈페이지는 자바스크립트 봇 검사(Client Challenge)가
걸려 있어 문서를 받아도 껍데기만 온다. 그런데 **엑셀 파일 자체는 그 검사를
지나지 않는다** — 직접 주소로 부르면 그대로 내려온다.

    https://www.ifo.de/sites/default/files/secure/timeseries/gsk-e-YYYYMM.xlsx

달마다 주소가 바뀌므로 이번 달부터 거꾸로 짚어 처음 잡히는 것을 쓴다. 발표는
매달 말이라 달이 바뀐 직후에는 지난달 파일이 최신이다.

들어 있는 것:
  'ifo Business Climate' 시트  독일 전체 업황지수 (2015=100, 계절조정)
  'Sectors' 시트               제조업·서비스업 등 부문별

부문별은 **지수가 아니라 잔액(balance)** 이다. 좋다고 답한 비율에서 나쁘다고
답한 비율을 뺀 값이라 −30~+30 언저리를 오간다. 전체 지수(85~100)와 한 축에
놓으면 읽히지 않으므로 화면에서 따로 그린다. 단위가 다른 것을 같은 그림에
얹지 않는다.
"""

from __future__ import annotations

import datetime
import io
import json
import pathlib
import time

import requests

URL = ("https://www.ifo.de/sites/default/files/secure/timeseries/"
       "gsk-e-{ym}.xlsx")
SNAPSHOT = pathlib.Path(__file__).resolve().parent.parent / "data" / "ifo.json"
TIMEOUT = 90
LOOK_BACK = 4          # 이번 달부터 몇 달까지 거슬러 찾아볼 것인가
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 'Sectors' 시트에서 업황지수(Business Climate)가 있는 열. 1부터 센다.
SECTOR_COL = {"man": 8, "srv": 11}      # 제조업, 서비스업


class IfoError(RuntimeError):
    pass


def _fetch(ym: str) -> bytes | None:
    """그 달 파일을 받는다. 없으면 None.

    없는 달을 부르면 봇 검사 페이지(HTML)가 200 으로 온다. 그래서 상태
    코드가 아니라 내용을 봐야 한다 — xlsx 는 zip 이라 'PK' 로 시작한다.
    """
    try:
        resp = requests.get(URL.format(ym=ym), timeout=TIMEOUT,
                            headers={"User-Agent": UA})
    except requests.RequestException:
        return None
    if resp.status_code != 200 or not resp.content.startswith(b"PK"):
        return None
    return resp.content


def workbook(today: datetime.date | None = None, log=print):
    """가장 최근 판을 받아 (엑셀, 기준연월) 로 돌려준다."""
    today = today or datetime.date.today()
    y, m = today.year, today.month
    for _ in range(LOOK_BACK):
        ym = f"{y}{m:02d}"
        raw = _fetch(ym)
        if raw:
            import openpyxl
            log(f"    ifo 원본 gsk-e-{ym}.xlsx ({len(raw):,}바이트)")
            return openpyxl.load_workbook(io.BytesIO(raw), data_only=True), ym
        time.sleep(0.5)
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    raise IfoError(f"최근 {LOOK_BACK}달치 파일을 하나도 받지 못했다")


def _month_key(cell) -> str | None:
    """' 09/2026' 또는 날짜 값을 'YYYY-MM' 으로."""
    if cell is None:
        return None
    if isinstance(cell, datetime.datetime):
        return f"{cell.year}-{cell.month:02d}"
    text = str(cell).strip()
    if "/" in text:
        mm, _, yy = text.partition("/")
        try:
            return f"{int(yy)}-{int(mm):02d}"
        except ValueError:
            return None
    return None


def _column(ws, col: int, first_row: int = 9) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in ws.iter_rows(min_row=first_row, max_row=ws.max_row,
                            max_col=col, values_only=True):
        key = _month_key(row[0])
        if key is None:
            continue
        value = row[col - 1]
        if isinstance(value, (int, float)):
            out[key] = float(value)
    return out


def _extract(wb) -> dict[str, dict[str, float]]:
    out = {"all": _column(wb["ifo Business Climate"], 2)}
    sectors = wb["Sectors"]
    for key, col in SECTOR_COL.items():
        out[key] = _column(sectors, col)
    return out


def fresh(today: datetime.date | None = None,
          log=print) -> tuple[dict[str, dict[str, float]], str]:
    """ifo 에서 바로 받아 (계열, 기준연월). 막히면 IfoError 를 낸다.

    저장분으로 물러서지 않는다 — tools/ifo_snapshot.py 가 이것을 쓴다.
    """
    wb, ym = workbook(today, log=log)
    return _extract(wb), ym


def read_snapshot(log=print) -> dict[str, dict[str, float]] | None:
    """사무소 PC 가 올려 둔 저장분. 없거나 깨졌으면 None."""
    try:
        doc = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        got = {k: {m: float(v) for m, v in doc["series"][k].items()}
               for k in ("all", "man", "srv")}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log(f"    ifo 저장분을 읽지 못했다 — {exc}")
        return None
    log(f"    ifo 저장분 gsk-e-{doc.get('ym','?')}.xlsx "
        f"({doc.get('saved','?')[:10]} 사무소에서 올림)")
    return got


def write_snapshot(got: dict, ym: str) -> bool:
    """저장분을 쓴다. 내용이 그대로면 건드리지 않고 False."""
    doc = {"ym": ym,
           "saved": datetime.datetime.now(datetime.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
           "series": {k: got[k] for k in ("all", "man", "srv")}}
    body = json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True)
    if SNAPSHOT.exists():
        try:
            was = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            if was.get("ym") == ym and was.get("series") == doc["series"]:
                return False           # 'saved' 만 달라진 것은 쓰지 않는다
        except ValueError:
            pass
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(body + "\n", encoding="utf-8")
    return True


def series(today: datetime.date | None = None, log=print,
           allow_snapshot: bool = True) -> dict[str, dict[str, float]]:
    """{'all': {월: 지수}, 'man': {월: 잔액}, 'srv': {월: 잔액}}.

    **2026-11-23 부터 GitHub 런너에서는 ifo 가 열리지 않는다.** 그날 빌드가
    넉 달치를 하나도 받지 못했다. 같은 시각 사무소 IP 로는 202610·202609 가
    그대로 내려왔다(각 102KB, PK). 일곱 시간 뒤 런너에서 다시 해도 같았으니
    일시적인 것이 아니라 Azure IP 를 막은 것으로 본다 — 주소에 박힌
    `/secure/` 가 본디 접근 제어가 걸린 경로다. 2026-11-20 까지는 런너에서도
    받혔다.

    그래서 사무소 PC 가 평일 06:40·11:00 에 `tools/ifo_snapshot.py` 로 받아
    `data/ifo.json` 에 올리고, 런너는 직접 받기가 막히면 그것을 읽는다.
    저장분마저 없으면 IfoError 를 그대로 내보낸다 — 그때는 build.py 가
    이전 판 값을 물려 쓴다.
    """
    try:
        wb, _ym = workbook(today, log=log)
    except IfoError:
        if not allow_snapshot:
            raise
        got = read_snapshot(log=log)
        if got is None:
            raise
        return got
    return _extract(wb)
