# -*- coding: utf-8 -*-
"""차트팩을 다시 만든다.

  python build/build.py              index.html 을 새로 쓴다
  python build/build.py --check      쓰지 않고 지금 index.html 과 대조만 한다

--check 는 "고친 데가 없는데 숫자가 달라졌다"를 잡으려는 것이다. Eurostat 이
값을 수정하면 달라지는 게 맞으므로, 다르다고 해서 곧 오류는 아니다. 무엇이
얼마나 달라졌는지 보고 사람이 판단한다.

아직 API 로 옮기지 못한 계열은 이전 판에서 그대로 물려 온다(sources.CARRY_OVER).
물려 온 계열은 로그에 남긴다 — 조용히 낡아 가는 것이 제일 나쁘다.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "build"))

import bis                                                       # noqa: E402
import daily                                                     # noqa: E402
import ecos                                                      # noqa: E402
import ifo                                                       # noqa: E402
import insee                                                     # noqa: E402
import worldbank                                                 # noqa: E402
import comext                                                    # noqa: E402
import ecb                                                       # noqa: E402
import imf                                                       # noqa: E402
import eurostat                                                  # noqa: E402
import oecd                                                      # noqa: E402
import sources                                                   # noqa: E402
import stocks                                                    # noqa: E402

TEMPLATE = BASE / "template.html"
OUTPUT = BASE / "index.html"

DATA_RE = re.compile(r"const DATA = (\{.*?\});\n", re.S)


# 이번 빌드에서 어긋난 것. 페이지에 함께 실어 주간 점검이 읽게 한다.
#
# Actions 로그에만 찍으면 아무도 열어 보지 않는다. 한국 품목별 물가가
# '[실패] 한국 품목별 물가 — KR' 한 줄만 남기고 차트 셋을 통째로 떨어뜨린
# 채로 여러 날 지났다. 값이 틀리는 것이 아니라 없어지는 고장은 눈에 띄지
# 않으므로, 기계가 세어 두어야 한다.
TROUBLE: list[str] = []

# 이 말이 든 줄만 모은다. 물려 쓴 계열도 넣는다 — 값은 있지만 새 값이
# 아니라는 뜻이고, 그것이 며칠 이어지면 출처가 죽은 것이다.
TROUBLE_MARKS = ("[실패]", "물려 쓴다", "[경고]")


def log(msg: str) -> None:
    print(msg, flush=True)
    if any(mark in msg for mark in TROUBLE_MARKS):
        TROUBLE.append(" ".join(msg.split()))


# ------------------------------------------------------------------ 기간 축
def previous() -> dict:
    """지금 index.html 에 박혀 있는 데이터. 기간 축과 물려 쓸 계열의 출처다."""
    m = DATA_RE.search(OUTPUT.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("index.html 에서 DATA 를 찾지 못했다.")
    return json.loads(m.group(1))


def half_up(value: float, digits: int, mode: str = "binary"):
    """사람이 쓰는 반올림 — 5는 올린다.

    파이썬 기본 round 는 5를 짝수 쪽으로 보낸다(601866.5 -> 601866). 통계표는
    올림 쪽이라 601867 이어야 한다.

    Decimal(str(v)) 가 아니라 Decimal(v) 로 감싸는 것이 중요하다. 앞의 것은
    2.405 를 글자 그대로 2.405 로 보아 2.41 로 올리지만, 부동소수점이 실제로
    담고 있는 값은 2.40499999… 라서 2.40 이 맞다. 원본 차트팩도 그 값으로
    반올림했다. str 를 거치면 없는 정밀도를 지어내는 셈이 된다."""
    q = Decimal(1).scaleb(-digits)
    base = Decimal(str(value)) if mode == "decimal" else Decimal(value)
    d = base.quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if digits <= 0 else float(d)


def pick(got: dict, geo: str, periods: list[str], scale: float = 1.0,
         digits: int = sources.ROUND_DEFAULT):
    """{기간: 값} 을 기간 축에 맞춰 줄로 편다. 없는 시점은 None.

    화면이 보여 주는 자릿수까지만 남긴다. 원값을 그대로 두면 Eurostat 이
    꼬리 자리만 손봐도 판이 달라져, 진짜 변화와 구별할 수 없게 된다.
    """
    rows = got.get(geo, {})
    out = []
    for p in periods:
        v = rows.get(p)
        out.append(None if v is None else half_up(v * scale, digits))
    return out


def gather(spec: dict, periods: list[str], since: str, label: str) -> tuple[dict, dict]:
    """({계열: {블록: [반올림 값...]}}, {계열: {블록: [원값...]}})

    원값을 함께 내는 것은 스프레드 때문이다. 반올림한 금리끼리 빼면 1bp 가
    어긋난다(3.176-3.121 은 6bp 인데, 3.18-3.12 로 빼면 6bp 가 아니라 5~7bp 로
    갈린다). 뺄셈을 먼저 하고 그다음에 반올림해야 한다.
    """
    out: dict[str, dict[str, list]] = {}
    raw: dict[str, dict[str, list]] = {}
    for key, entry in spec.items():
        dataset, filters = entry[0], entry[1]
        scale = entry[2] if len(entry) > 2 else 1.0
        codes = sorted(set(sources.CODES) |
                       set(sources.GEO_OVERRIDE.get(key, {}).values()))
        try:
            got = eurostat.series(dataset, codes, since=since, **filters)
        except eurostat.EurostatError as exc:
            log(f"  [실패] {label} {key} ({dataset}) — {exc}")
            continue
        digits = sources.ROUND.get(key, sources.ROUND_DEFAULT)
        override = sources.GEO_OVERRIDE.get(key, {})
        out[key] = {blk: pick(got, override.get(blk, geo), periods, scale, digits)
                    for blk, geo in sources.GEO.items()}
        raw[key] = {blk: [got.get(override.get(blk, geo), {}).get(p) for p in periods]
                    for blk, geo in sources.GEO.items()}
        have = sum(1 for blk in out[key] for v in out[key][blk] if v is not None)
        log(f"  {label} {key:7} {dataset:16} 값 {have:4}/{len(sources.GEO)*len(periods)}")
    return out, raw


def shift_month(month: str, step: int) -> str:
    y, m = int(month[:4]), int(month[5:7]) + step
    return f"{y + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}"


def roll_axis(prev: dict) -> dict:
    """기간 축을 자료가 실제로 있는 데까지 민다.

    달력으로 계산하지 않고 '값이 있는 마지막 시점'에서 되짚는다. 통계마다
    발표가 늦는 정도가 달라, 달력으로 밀면 아직 나오지도 않은 달이 빈칸으로
    붙는다.

    기준은 그 주기에서 가장 빨리 나오는 것으로 잡는다 — 월간은 HICP, 분기는
    GDP, 연간은 명목 GDP, 이민은 그 자체. 주가지수 축(monthsS)만 한 달 더
    길다. 진행 중인 달의 시세를 보여 주기 때문이다.
    """
    meta = json.loads(json.dumps(prev["meta"]))
    ez = sources.GEO["EZ"]

    def last_of(dataset, **filters):
        got = eurostat.series(dataset, [ez], since="2015", **filters).get(ez, {})
        return max(got) if got else None

    m_end = last_of("prc_hicp_minr", coicop18="TOTAL", unit="RCH_A")
    q_end = last_of("namq_10_gdp", s_adj="SCA", unit="CLV_PCH_PRE", na_item="B1GQ")
    y_end = last_of("nama_10_gdp", unit="CP_MEUR", na_item="B1GQ")
    im = eurostat.series("migr_imm1ctz", ["DE"], since="2015",
                         **sources.IMM_FILTERS).get("DE", {})
    ym_end = max(im) if im else None

    # 월간 축은 '자료가 있는 마지막 달'이 아니라 '이번 달'까지 간다.
    #
    # 앞서는 HICP 발표월에 맞췄는데, 그러면 발표가 빠른 계열이 느린 계열의
    # 달력에 갇힌다. 9월에 ECB·연준·한은이 금리를 올렸는데 축이 8월에서
    # 끝나 차트에 들어갈 자리가 없었다. 정책 변화가 한 달 늦게 보이는 것은
    # 사무소 브리핑에서 그냥 넘길 일이 아니다.
    #
    # 대가는 느린 계열의 오른쪽 끝에 빈칸이 생기는 것이다. 그건 "아직 발표
    # 전"이라는 사실 그대로라 오히려 읽을 값이 있다.
    #
    # hicpItemMonth 는 축과 별개다. 품목별 물가 막대는 '값이 있는 마지막 달'을
    # 써야 하므로 HICP 발표월을 그대로 둔다.
    today_m = datetime.date.today().strftime("%Y-%m")
    n = len(meta["months"])
    meta["months"] = [shift_month(today_m, -(n - 1 - i)) for i in range(n)]
    meta["monthsS"] = list(meta["months"])
    if m_end:
        meta["hicpItemMonth"] = m_end
    if q_end:
        y, q = int(q_end[:4]), int(q_end[-1])
        n = len(meta["qs"])
        seq = []
        for i in range(n - 1, -1, -1):
            qq = q - i
            seq.append(f"{y + (qq - 1) // 4}-Q{(qq - 1) % 4 + 1}")
        meta["qs"] = seq
    if y_end:
        n = len(meta["years"])
        meta["years"] = [str(int(y_end) - (n - 1 - i)) for i in range(n)]
    if ym_end:
        n = len(meta["yearsM"])
        meta["yearsM"] = [str(int(ym_end) - (n - 1 - i)) for i in range(n)]
        meta["immYear"] = ym_end

    moved = [k for k in ("months", "qs", "years", "yearsM")
             if meta[k] != prev["meta"][k]]
    log(f"  기간 축 — 월 {meta['months'][-1]} / 분기 {meta['qs'][-1]} / "
        f"연 {meta['years'][-1]} / 이민 {meta['yearsM'][-1]}"
        + (f"  (밀린 축: {moved})" if moved else "  (그대로)"))
    meta["asOf"] = datetime.date.today().isoformat()
    return meta


def build(prev: dict) -> dict:
    meta = roll_axis(prev)
    months, qs, years = meta["months"], meta["qs"], meta["years"]

    data: dict = {"meta": meta}
    for blk in sources.GEO:
        data[blk] = {}

    log(f"월간 {len(months)}개월 ({months[0]}~{months[-1]})")
    monthly, raw = gather(sources.MONTHLY, months, months[0], "월")
    log(f"분기 {len(qs)}분기 ({qs[0]}~{qs[-1]})")
    quarterly, _ = gather(sources.QUARTERLY, qs, qs[0], "분기")
    log(f"연간 {len(years)}개년 ({years[0]}~{years[-1]})")
    annual, _ = gather(sources.ANNUAL, years, years[0], "연")

    for group in (monthly, quarterly, annual):
        for key, per_block in group.items():
            for blk, values in per_block.items():
                data[blk][key] = values

    # 스프레드는 받아오는 것이 아니라 빼서 만든다. 독일 대비 bp.
    # 반올림 전 값으로 뺀다. 자세한 것은 gather 의 설명.
    if "y10" in raw:
        de = raw["y10"]["DE"]
        for blk in sources.GEO:
            data[blk]["spr"] = [
                None if (a is None or b is None) else half_up((a - b) * 100, 0)
                for a, b in zip(raw["y10"][blk], de)]
        log("  파생  spr     (10년물 − 독일 10년물, bp)")

    # --- 품목별 소비자물가 (가로 막대) ---
    item_month = meta[sources.ITEM_MONTH_KEY]
    codes = sorted({c for v in sources.ITEMS.values() for c in v})
    try:
        doc = eurostat.fetch("prc_hicp_minr",
                             sorted(set(sources.CODES)), since=item_month,
                             coicop18=codes, unit="RCH_A")
        dims = doc["id"]
        gi, ci, ti = dims.index("geo"), dims.index("coicop18"), dims.index("time")
        tbl = {(k[gi], k[ci]): v for k, v in eurostat.decode(doc).items()
               if k[ti] == item_month}
        for key, wanted in sources.ITEMS.items():
            for blk, geo in sources.GEO.items():
                data[blk][key] = [
                    None if tbl.get((geo, c)) is None else half_up(tbl[(geo, c)], 1)
                    for c in wanted]
            log(f"  품목 {key:7} prc_hicp_minr    {item_month} 기준 {len(wanted)}항목")
    except eurostat.EurostatError as exc:
        log(f"  [실패] 품목별 물가 — {exc}")

    # --- 독일 ifo · 프랑스 INSEE 업황지수 ---
    try:
        got = ifo.series(log=log)
        for key, name in sources.SURVEY_DE.items():
            rows = got.get(name) or {}
            data["DE"][key] = [None if rows.get(m) is None
                               else half_up(rows[m], 1) for m in months]
            have = sum(1 for v in data["DE"][key] if v is not None)
            log(f"  독일 {key:5} ifo 업황     값 {have}/{len(months)}")
    except (ifo.IfoError, KeyError, ValueError, ImportError) as exc:
        log(f"  [실패] 독일 ifo — {exc}")

    for key, idbank in sources.SURVEY_FR.items():
        try:
            rows = insee.series(idbank)
        except insee.InseeError as exc:
            log(f"  [실패] 프랑스 {key} — {exc}")
            continue
        data["FR"][key] = [None if rows.get(m) is None
                           else half_up(rows[m], 1) for m in months]
        have = sum(1 for v in data["FR"][key] if v is not None)
        log(f"  프랑스 {key:5} INSEE {idbank}  값 {have}/{len(months)}")

    # --- 한국 품목별 소비자물가 (ECOS) ---
    #
    # 키가 없으면 이 구획만 빠진다. 차트팩은 공개 저장소라 키를 코드에 둘 수
    # 없고, Actions Secret 이 없는 곳(손으로 돌리는 PC 등)에서도 나머지는
    # 만들어져야 한다.
    if ecos.have_key():
        try:
            fill_kr_items(data, meta)
        except (ecos.EcosError, KeyError, ValueError) as exc:
            log(f"  [실패] 한국 품목별 물가 — {exc}")
        try:
            fill_kr_trade(data, meta)
        except (ecos.EcosError, KeyError, ValueError) as exc:
            log(f"  [실패] 대한국 교역 — {exc}")
    else:
        log("  한국 품목별 물가 — ECOS_API_KEY 가 없어 건너뛴다")

    # --- 경상수지 ---
    try:
        fxq = ecb.quarterly_fx("USD", f"{years[0]}-Q1")
        for blk, geo in sources.GEO.items():
            partner = sources.CA_PARTNER.get(geo, sources.CA_DEFAULT)
            eur = eurostat.series("ei_bpm6ca_q", [geo], since=f"{years[0]}-Q1",
                                  unit="MIO_EUR", partner=partner,
                                  **sources.CA_FILTERS).get(geo, {})
            pct = eurostat.series("ei_bpm6ca_q", [geo], since=f"{years[0]}-Q1",
                                  unit="PC_GDP", partner=partner,
                                  **sources.CA_FILTERS).get(geo, {})
            # 분기 금액을 그 분기 환율로 달러 환산(10억 달러)
            usd = {q: v / 1000 * fxq[q] for q, v in eur.items() if q in fxq}
            data[blk]["caQ"] = [None if q not in usd else half_up(usd[q], 1) for q in qs]
            data[blk]["caQp"] = [None if pct.get(q) is None else half_up(pct[q], 1)
                                 for q in qs]
            # 연간은 분기 환산액의 합. 네 분기가 다 있어야 한 해로 친다.
            ann: dict[str, list] = {}
            for q, v in usd.items():
                ann.setdefault(q[:4], []).append(v)
            data[blk]["caA"] = [half_up(sum(ann[y]), 1) if len(ann.get(y, [])) == 4
                                else None for y in years]
            # GDP 대비 비율은 유로끼리 나눈다. 달러 환산액을 쓰면 환율이
            # 분자에만 걸려 비율이 뒤틀린다. 분기 비율을 평균 내는 것도 안 된다
            # — 분기마다 다른 GDP 를 같은 무게로 세게 된다.
            eur_ann: dict[str, list] = {}
            for q, v in eur.items():
                eur_ann.setdefault(q[:4], []).append(v)
            gdp = data[blk].get("gdpEur") or [None] * len(years)
            out = []
            for i, y in enumerate(years):
                g = gdp[i] if i < len(gdp) else None
                qv = eur_ann.get(y, [])
                out.append(half_up(sum(qv) / g * 100, 1)
                           if len(qv) == 4 and g else None)
            data[blk]["caAp"] = out
        log("  분기 caQ/caQp/caA/caAp  ei_bpm6ca_q + ECB EXR (달러 환산)")
    except (eurostat.EurostatError, ecb.EcbError) as exc:
        log(f"  [실패] 경상수지 — {exc}")

    # --- 이민 (연간, 기간 축이 다르다) ---
    ym = meta.get("yearsM") or []
    if ym:
        try:
            geos = sorted(set(sources.EA_MEMBERS) | set(sources.GEO.values()))
            imm = eurostat.series("migr_imm1ctz", geos, since=ym[0],
                                  **sources.IMM_FILTERS)
            pop = eurostat.series("demo_gind", geos, since=ym[0],
                                  indic_de="AVG")

            # 유로지역은 21개국을 모두 더한다. 한 나라라도 빠진 해는 비운다.
            ez_imm, ez_pop, missing = [], [], []
            for y in ym:
                gone = [g for g in sources.EA_MEMBERS
                        if imm.get(g, {}).get(y) is None]
                if gone:
                    ez_imm.append(None)
                    ez_pop.append(None)
                    missing = gone          # 가장 최근 해의 미발표국을 남긴다
                    continue
                ez_imm.append(sum(imm[g][y] for g in sources.EA_MEMBERS))
                ez_pop.append(sum(pop[g][y] for g in sources.EA_MEMBERS
                                  if pop.get(g, {}).get(y) is not None))

            for blk, geo in sources.GEO.items():
                if blk == "EZ":
                    rows = {y: v for y, v in zip(ym, ez_imm) if v is not None}
                    pops = {y: v for y, v in zip(ym, ez_pop) if v is not None}
                else:
                    rows, pops = imm.get(geo, {}), pop.get(geo, {})
                data[blk]["imm"] = [None if rows.get(y) is None
                                    else half_up(rows[y] / 1000, 1) for y in ym]
                data[blk]["immR"] = [
                    None if (rows.get(y) is None or not pops.get(y))
                    else half_up(rows[y] / pops[y] * 100, 2) for y in ym]
            meta["immMissing"] = missing
            log(f"  연  imm/immR migr_imm1ctz     유로지역 "
                f"{len(sources.EA_MEMBERS)}개국"
                + (f", {meta['immYear']}년 미발표 {missing}" if missing else ""))
        except eurostat.EurostatError as exc:
            log(f"  [실패] 이민 — {exc}")

    # --- 교역 ---
    try:
        fxm = ecb.monthly_fx("USD", f"{years[0]}-01")
        ds_e, f_e, p_e = sources.TRADE_EURO
        ds_c, f_c, p_c = sources.TRADE_COUNTRY

        def usd(rows: dict, scale: float) -> dict[str, float]:
            """월별 유로 금액을 그달 환율로 달러 환산."""
            return {m: v * scale * fxm[m] for m, v in rows.items() if m in fxm}

        def roll(usd_rows: dict) -> tuple[list, list]:
            """(연간 합, 분기 합). 달이 다 차지 않은 구간은 내지 않는다."""
            ya: dict[str, list] = {}
            qa: dict[str, list] = {}
            for m, v in usd_rows.items():
                y, mm = m[:4], int(m[5:7])
                ya.setdefault(y, []).append(v)
                qa.setdefault(f"{y}-Q{(mm - 1) // 3 + 1}", []).append(v)
            return ([half_up(sum(ya[y]), 0) if len(ya.get(y, [])) == 12 else None
                     for y in years],
                    [half_up(sum(qa[q]), 0) if len(qa.get(q, [])) == 3 else None
                     for q in qs])

        since = f"{years[0]}-01"
        for blk, geo in sources.GEO.items():
            euro = blk == "EZ"
            ds, filt, part = (ds_e, f_e, p_e) if euro else (ds_c, f_c, p_c)
            trA: dict[str, list] = {}
            trQ: dict[str, list] = {}
            for flow, tot_key, ext_key in (("EXP", "ex", "xex"),
                                           ("IMP", "im", "xim")):
                ext = eurostat.series(ds, [geo], since=since, stk_flow=flow,
                                      partner=part["extra"], **filt).get(geo, {})
                if euro:
                    intra = eurostat.series(ds, [geo], since=since, stk_flow=flow,
                                            partner=part["intra"],
                                            **filt).get(geo, {})
                    tot = {m: intra.get(m, 0) + ext.get(m, 0)
                           for m in set(intra) | set(ext)}
                else:
                    tot = eurostat.series(ds, [geo], since=since, stk_flow=flow,
                                          partner=part["total"],
                                          **filt).get(geo, {})
                trA[tot_key], trQ[tot_key] = roll(usd(tot, 1.0))
                trA[ext_key], trQ[ext_key] = roll(usd(ext, 1.0))
            data[blk]["trA"], data[blk]["trQ"] = trA, trQ

            # 대한국 교역. 유로지역은 같은 데이터셋에 상대국이 있고,
            # 개별국은 Comext 를 따로 부른다.
            kr: dict[str, list] = {}
            for flow, key in (("EXP", "ex"), ("IMP", "im")):
                if euro:
                    rows = eurostat.series(ds_e, [geo], since=since,
                                           stk_flow=flow, partner=sources.KR,
                                           **f_e).get(geo, {})
                    kr[key], _ = roll(usd(rows, 1.0))
                else:
                    cf = comext.EXPORT if flow == "EXP" else comext.IMPORT
                    rows = comext.monthly_value(geo, sources.KR, cf, since)
                    kr[key], _ = roll(usd(rows, 1e-6))   # 낱 유로 -> 백만
            data[blk]["kr"] = kr
        log("  교역 trA/trQ/kr  ext_st_easitc·ei_eteu27_2020_m·Comext (달러 환산)")
    except (eurostat.EurostatError, ecb.EcbError, comext.ComextError) as exc:
        log(f"  [실패] 교역 — {exc}")

    # --- 주가지수 (월말 종가) ---
    # 기간 축이 또 다르다. monthsS 는 진행 중인 달까지 포함해 한 달 더 길다.
    msx = meta.get("monthsS") or months
    closes = stocks.all_closes(msx[0], msx[-1], log)
    for blk in sources.GEO:
        rows = closes.get(blk)
        if not rows:
            # 받지 못한 지수는 이전 판을 시점에 맞춰 물려 쓴다. 자리로
            # 맞추면 축이 밀린 날 옛 종가가 새 달의 값인 척 앉는다.
            old_msx = prev.get("meta", {}).get("monthsS") or []
            for fld in ("stk", "stkR"):
                old = prev.get(blk, {}).get(fld) or []
                at = dict(zip(old_msx, old)) if len(old) == len(old_msx) else {}
                data[blk][fld] = [at.get(m) for m in msx]
            continue
        data[blk]["stk"] = [None if msx[i] not in rows else half_up(rows[msx[i]], 1)
                            for i in range(len(msx))]
        # 등락률은 반올림 전 종가로 낸다. 첫 달은 직전 달 종가가 있어야 한다.
        y, m = int(msx[0][:4]), int(msx[0][5:7])
        before = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
        chain = [rows.get(before)] + [rows.get(x) for x in msx]
        data[blk]["stkR"] = [
            None if (chain[i] is None or chain[i - 1] is None)
            else half_up((chain[i] / chain[i - 1] - 1) * 100, 1)
            for i in range(1, len(chain))]
    if closes:
        log(f"  월  stk/stkR  Yahoo Finance    {len(closes)}/{len(stocks.SYMBOLS)}개 지수")

    # --- 유로지역 밖 네 나라 (미국·중국·일본·한국) ---
    def carried(blk: str, name: str, axis_key: str) -> list:
        """이전 판의 계열을 이번 축의 같은 시점에 다시 앉힌다.

        자리(인덱스)가 아니라 시점(2026-08 같은 이름)으로 맞춘다. 앞서는
        길이만 같으면 통째로 물려줬는데, 축이 2026-08 에서 2026-09 로 밀린
        날 8월 값이 9월 자리에 앉았다. 길이는 똑같이 60 이라 걸러지지 않았다.

        그렇다고 축이 밀렸을 때 통째로 비우면, OECD 가 429 를 한 번 낼 때마다
        차트가 사라진다. 이전 판에 기간 축도 함께 저장돼 있으니 시점표로
        만들어 옮겨 실으면 둘 다 피할 수 있다. 새로 생긴 달은 빈칸이 되는데,
        그건 '아직 못 받았다'는 사실 그대로다.
        """
        axis = meta[axis_key]
        old = prev.get(blk, {}).get(name)
        old_axis = prev.get("meta", {}).get(axis_key) or []
        if not old or len(old) != len(old_axis):
            return [None] * len(axis)
        at = dict(zip(old_axis, old))
        return [at.get(p) for p in axis]

    def keep_old(name: str, axis_key: str) -> None:
        """받지 못한 계열은 이전 판 값을 시점에 맞춰 물려 쓴다."""
        for blk in sources.OECD_AREAS:
            data[blk][name] = carried(blk, name, axis_key)
        got = sum(1 for blk in sources.OECD_AREAS
                  for v in data[blk][name] if v is not None)
        if got:
            log(f"    └ {name} — 이전 판에서 {got}개를 시점에 맞춰 물려 썼다.")

    key = "+".join(sources.OECD_AREAS.values()) + ".M......."
    flows = {"KEI": oecd.KEI, "FINMARK": oecd.FINMARK}
    for blk in sources.OECD_AREAS:
        data.setdefault(blk, {})
    for name, (flow, match, digits) in sources.OECD_MONTHLY.items():
        try:
            got = oecd.series(flows[flow], key, months[0], **match)
        except oecd.OecdError as exc:
            log(f"  [실패] 해외 {name} — {exc} (이전 값을 물려 쓴다)")
            keep_old(name, "months")
            continue
        have = 0
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk][name] = [None if rows.get(m) is None
                               else half_up(rows[m], digits) for m in months]
            have += sum(1 for v in data[blk][name] if v is not None)
        empty = [b for b, a in sources.OECD_AREAS.items() if not got.get(a)]
        log(f"  해외 {name:6} OECD {flow:8} 값 {have:4}/"
            f"{len(sources.OECD_AREAS)*len(months)}"
            + (f"  없음: {empty}" if empty else ""))

    # 주 계열이 통째로 빈 블록은 예비 출처에서 다시 받는다.
    for name, per_block in sources.OECD_FALLBACK.items():
        for blk, (fflow, fkey, digits) in per_block.items():
            cur = data.get(blk, {}).get(name)
            if cur and any(v is not None for v in cur):
                continue                      # 주 계열로 이미 채워졌다
            try:
                got = oecd.series(fflow, fkey, months[0])
            except oecd.OecdError as exc:
                log(f"  [실패] 예비 {blk}.{name} — {exc}")
                continue
            rows = next(iter(got.values()), {})
            data[blk][name] = [None if rows.get(m) is None
                               else half_up(rows[m], digits) for m in months]
            have = sum(1 for v in data[blk][name] if v is not None)
            log(f"  예비 {blk}.{name:6} {fflow.split('@')[-1][:24]:24} "
                f"값 {have}/{len(months)}")

    # 정책금리 (BIS). OECD 단기금리는 콜·은행간금리라 정책금리가 아니고
    # 중국이 빠진다. 자세한 것은 bis.py.
    try:
        got = bis.policy_rates(list(bis.AREAS.values()), months[0])
        for blk, area in bis.AREAS.items():
            rows = bis.fill_tail(got.get(area, {}), months, area, log)
            data[blk]["cbr"] = [
                None if rows.get(m) is None
                else half_up(bis.to_upper(area, rows[m], log), 2)
                for m in months]
        have = sum(1 for b in bis.AREAS for v in data[b]["cbr"] if v is not None)
        log(f"  해외 cbr    BIS WS_CBPOL  정책금리 값 {have}/"
            f"{len(bis.AREAS)*len(months)}")
    except bis.BisError as exc:
        log(f"  [실패] 해외 정책금리 — {exc} (이전 값을 물려 쓴다)")
        keep_old("cbr", "months")

    # 대미달러 환율
    flow, match, dig = sources.OECD_FX
    try:
        got = oecd.series(flows[flow], key, months[0], **match)
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk]["fxU"] = [None if rows.get(m) is None
                                else half_up(rows[m], dig) for m in months]
        miss = [b for b, a in sources.OECD_AREAS.items() if not got.get(a)]
        log(f"  해외 fxU    OECD KEI      대미달러 환율"
            + (f"  없음: {miss} (미국은 자기 통화)" if miss else ""))
    except oecd.OecdError as exc:
        log(f"  [실패] 해외 환율 — {exc} (이전 값을 물려 쓴다)")
        keep_old("fxU", "months")

    # 경상수지 (분기·연간)
    for freq, axis_key, name in (("Q", "qs", "caQ"), ("A", "years", "caA")):
        axis = meta[axis_key]
        try:
            got = oecd.series(oecd.BOP,
                              sources.OECD_CA_KEY.format(freq=freq), axis[0])
        except oecd.OecdError as exc:
            log(f"  [실패] 해외 {name} — {exc} (이전 값을 물려 쓴다)")
            keep_old(name, axis_key)
            continue
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk][name] = [None if rows.get(p) is None
                               else half_up(rows[p] / 1000, 1) for p in axis]
        have = sum(1 for b in sources.OECD_AREAS for v in data[b][name]
                   if v is not None)
        log(f"  해외 {name:6} OECD BOP      값 {have}/"
            f"{len(sources.OECD_AREAS)*len(axis)}")

    # 주택가격. 지수로 와서 전년비 상승률을 직접 만든다. 앞 해가 있어야
    # 첫 해 값이 나오므로 한 해 일찍부터 받는다.
    try:
        got = oecd.series(oecd.HOUSE, "USA+CHN+JPN+KOR.A...",
                          str(int(years[0]) - 1), years[-1],
                          MEASURE="HPI", UNIT_MEASURE="IX")
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            out = []
            for y in years:
                cur, prev_y = rows.get(y), rows.get(str(int(y) - 1))
                out.append(None if (cur is None or not prev_y)
                           else half_up((cur / prev_y - 1) * 100, 1))
            data[blk]["hpi"] = out
        have = sum(1 for b in sources.OECD_AREAS for v in data[b]["hpi"]
                   if v is not None)
        log(f"  해외 hpi    OECD 주택가격  전년비 값 {have}/"
            f"{len(sources.OECD_AREAS)*len(years)}")
    except oecd.OecdError as exc:
        log(f"  [실패] 해외 주택가격 — {exc} (이전 값을 물려 쓴다)")
        keep_old("hpi", "years")

    # 근원물가. 흐름이 둘로 갈려 있어 받은 것을 합친다.
    for name, specs in sources.OECD_CORE.items():
        axis_key = "months" if name.endswith("M") else "years"
        axis = meta[axis_key]
        merged = {}
        for fname, fkey in specs:
            try:
                merged.update(oecd.series(getattr(oecd, fname), fkey, axis[0]))
            except oecd.OecdError as exc:
                log(f"  [경고] 근원물가 {name} {fkey[:12]} — {exc}")
        if not merged:
            log(f"  [실패] 해외 {name} — 받은 것이 없다 (이전 값을 물려 쓴다)")
            keep_old(name, axis_key)
            continue
        for blk, area in sources.OECD_AREAS.items():
            rows = merged.get(area)
            if not rows:
                # 이 나라만 못 받았다. 빈칸으로 덮지 않고 이전 값을 시점에
                # 맞춰 옮겨 싣는다 — 까닭은 carried 에 적어 두었다.
                data[blk][name] = carried(blk, name, axis_key)
                continue
            data[blk][name] = [None if rows.get(p) is None
                               else half_up(rows[p], 1) for p in axis]
        miss = [b for b, a in sources.OECD_AREAS.items() if not merged.get(a)]
        have = sum(1 for b in sources.OECD_AREAS for v in data[b][name]
                   if v is not None)
        log(f"  해외 {name:6} OECD 물가     근원 값 {have}/"
            f"{len(sources.OECD_AREAS)*len(axis)}"
            + (f"  없음: {miss}" if miss else ""))

    # 연간 실질 GDP 성장률
    try:
        got = oecd.series(oecd.QNA_G20, "all", years[0],
                          **sources.OECD_ANNUAL_GROWTH)
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk]["ga"] = [None if rows.get(y) is None
                               else half_up(rows[y], 1) for y in years]
        have = sum(1 for b in sources.OECD_AREAS for v in data[b]["ga"]
                   if v is not None)
        log(f"  해외 ga     OECD QNA(연)  값 {have}/"
            f"{len(sources.OECD_AREAS)*len(years)}")
    except oecd.OecdError as exc:
        log(f"  [실패] 해외 연간 성장률 — {exc} (이전 값을 물려 쓴다)")
        keep_old("ga", "years")

    # 연간 실업률
    try:
        got = oecd.series(oecd.KEI, "USA+CHN+JPN+KOR.A.......", years[0],
                          **sources.OECD_ANNUAL_UNEMP)
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk]["unA"] = [None if rows.get(y) is None
                                else half_up(rows[y], 1) for y in years]
        miss = [b for b, a in sources.OECD_AREAS.items() if not got.get(a)]
        log("  해외 unA    OECD KEI(연)  연간 실업률"
            + (f"  없음: {miss}" if miss else ""))
    except oecd.OecdError as exc:
        log(f"  [실패] 해외 연간 실업률 — {exc} (이전 값을 물려 쓴다)")
        keep_old("unA", "years")

    # 연간 소비자물가
    cpi_a = {}
    for _, (fname, fkey) in sources.OECD_ANNUAL_CPI.items():
        try:
            cpi_a.update(oecd.series(getattr(oecd, fname), fkey, years[0]))
        except oecd.OecdError as exc:
            log(f"  [경고] 연간 물가 {fkey[:12]} — {exc}")
    if cpi_a:
        for blk, area in sources.OECD_AREAS.items():
            rows = cpi_a.get(area, {})
            data[blk]["cpiA"] = [None if rows.get(y) is None
                                 else half_up(rows[y], 1) for y in years]
        have = sum(1 for b in sources.OECD_AREAS for v in data[b]["cpiA"]
                   if v is not None)
        log(f"  해외 cpiA   OECD 물가     값 {have}/"
            f"{len(sources.OECD_AREAS)*len(years)}")
    else:
        keep_old("cpiA", "years")

    # 명목 GDP 와 총인구는 세계은행에서 받는다.
    #
    # OECD 연간 국민계정은 달러 계열이 PPP 기준이고(시장환율 명목 GDP 가
    # 없다), 중국이 회원국 흐름에 빠져 인구도 2023년까지만 나온다. 세계은행은
    # 둘 다 해결한다. 자세한 것은 worldbank.py.
    for ind, name, scale, digits, label in (
            (worldbank.GDP_USD, "gdpUSD", 1e12, 2, "명목 GDP(조 달러)"),
            (worldbank.POPULATION, "pop", 1e6, 2, "총인구(백만)")):
        try:
            got = worldbank.series(ind, list(worldbank.AREAS.values()),
                                   years[0], years[-1])
        except worldbank.WorldBankError as exc:
            log(f"  [실패] 세계은행 {name} — {exc} (이전 값을 물려 쓴다)")
            keep_old(name, "years")
            continue
        for blk, area in worldbank.AREAS.items():
            rows = got.get(area, {})
            data[blk][name] = [None if rows.get(y) is None
                               else half_up(rows[y] / scale, digits)
                               for y in years]
        have = sum(1 for b in worldbank.AREAS for v in data[b][name]
                   if v is not None)
        log(f"  해외 {name:6} 세계은행       {label} 값 {have}/"
            f"{len(worldbank.AREAS)*len(years)}")

    # 재정 (IMF WEO, 일반정부 기준)
    for ind, name, label in ((imf.DEBT, "debt", "정부부채/GDP"),
                             (imf.BALANCE, "bal", "재정수지/GDP")):
        try:
            got = imf.series(ind, list(imf.AREAS.values()))
        except imf.ImfError as exc:
            log(f"  [실패] IMF {name} — {exc} (이전 값을 물려 쓴다)")
            keep_old(name, "years")
            continue
        for blk, area in imf.AREAS.items():
            rows = got.get(area, {})
            data[blk][name] = [None if rows.get(y) is None
                               else half_up(rows[y], 1) for y in years]
        have = sum(1 for b in imf.AREAS for v in data[b][name] if v is not None)
        log(f"  해외 {name:6} IMF WEO       {label} 값 {have}/"
            f"{len(imf.AREAS)*len(years)}")

    # 경상수지 / GDP. 분모는 언제나 그 해 연간 명목 GDP 다. 그래서 이 계산은
    # 명목 GDP 를 받은 뒤라야 한다 — 앞에 두었다가 전부 빈칸이 된 적이 있다.
    #
    # 분기는 연율로 맞춘다. 분기 금액을 연간 GDP 의 1/4 로 나눠야 연간 비율과,
    # 유로 탭의 분기 비율과 같은 눈금에서 읽힌다.
    for blk in sources.OECD_AREAS:
        by_year = {y: g for y, g in zip(years, data[blk].get("gdpUSD") or []) if g}
        ca_a = data[blk].get("caA") or []
        data[blk]["caAp"] = [
            None if (c is None or not by_year.get(y))
            else half_up(c / (by_year[y] * 1000) * 100, 1)
            for y, c in zip(years, ca_a)]
        ca_q = data[blk].get("caQ") or []
        data[blk]["caQp"] = [
            None if (c is None or not by_year.get(q[:4]))
            else half_up(c / (by_year[q[:4]] * 1000 / 4) * 100, 1)
            for q, c in zip(qs, ca_q)]
    got_a = sum(1 for b in sources.OECD_AREAS for v in data[b]["caAp"] if v is not None)
    got_q = sum(1 for b in sources.OECD_AREAS for v in data[b]["caQp"] if v is not None)
    log(f"  해외 caAp/caQp  경상수지 ÷ 연간 명목 GDP  값 {got_a}/"
        f"{len(sources.OECD_AREAS)*len(years)}, {got_q}/"
        f"{len(sources.OECD_AREAS)*len(qs)}")

    # 연간·분기 교역은 월별 달러 금액을 더해서 만든다. 유로지역과 달리
    # 역내·역외 구분이 없으므로 전체(ex·im)만 둔다.
    for blk in sources.OECD_AREAS:
        ex, im = data[blk].get("exUSD"), data[blk].get("imUSD")
        if not ex or not im:
            continue
        ya, qa = {}, {}
        for i, m in enumerate(months):
            y, mm = m[:4], int(m[5:7])
            q = f"{y}-Q{(mm - 1) // 3 + 1}"
            ya.setdefault(y, []).append((ex[i], im[i]))
            qa.setdefault(q, []).append((ex[i], im[i]))

        def roll(bucket, need, axis):
            out = {"ex": [], "im": []}
            for k in axis:
                rows = bucket.get(k, [])
                full = len(rows) == need and all(
                    a is not None and b is not None for a, b in rows)
                out["ex"].append(half_up(sum(a for a, _ in rows), 1) if full else None)
                out["im"].append(half_up(sum(b for _, b in rows), 1) if full else None)
            return out

        data[blk]["trA"] = roll(ya, 12, years)
        data[blk]["trQ"] = roll(qa, 3, qs)
    log("  해외 trA/trQ   월별 달러 교역액을 연·분기로 합산")

    # 대유로 환율 (ECB 기준환율)
    for blk, cur in sources.ECB_FX_PER_EUR.items():
        try:
            rows = ecb.monthly_fx(cur, months[0])
        except ecb.EcbError as exc:
            log(f"  [경고] 대유로 환율 {blk} ({cur}) — {exc}")
            keep_old("fxE", "months")
            continue
        data[blk]["fxE"] = [None if rows.get(m) is None
                            else half_up(rows[m], 2) for m in months]
    log(f"  해외 fxE    ECB EXR       대유로 환율 {list(sources.ECB_FX_PER_EUR)}")

    # 미국 환율 칸은 달러지수로 채운다.
    for blk, symbol in sources.DOLLAR_INDEX.items():
        try:
            rows = stocks.monthly_close(symbol, months[0], months[-1])
        except stocks.StockError as exc:
            log(f"  [경고] 달러지수 {blk} ({symbol}) — {exc}")
            continue
        data[blk]["fxU"] = [None if m not in rows else half_up(rows[m], 2)
                            for m in months]
        have = sum(1 for v in data[blk]["fxU"] if v is not None)
        log(f"  해외 fxU    Yahoo {symbol:10} 달러지수 값 {have}/{len(months)}")

    # 분기 실질 GDP 성장률
    for name, match in sources.OECD_QUARTERLY.items():
        try:
            got = oecd.series(oecd.QNA_G20, "all", qs[0], **match)
        except oecd.OecdError as exc:
            log(f"  [실패] 해외 {name} — {exc} (이전 값을 물려 쓴다)")
            keep_old(name, "qs")
            continue
        have = 0
        for blk, area in sources.OECD_AREAS.items():
            rows = got.get(area, {})
            data[blk][name] = [None if rows.get(q) is None
                               else half_up(rows[q], 1) for q in qs]
            have += sum(1 for v in data[blk][name] if v is not None)
        log(f"  해외 {name:6} OECD QNA      값 {have:4}/"
            f"{len(sources.OECD_AREAS)*len(qs)}")

    # 주가는 유로지역과 같은 자리를 쓰므로 같은 출처(Yahoo 월말 종가)로 받는다.
    msx2 = meta.get("monthsS") or months
    for blk, symbol in sources.OECD_STOCKS.items():
        try:
            rows = stocks.monthly_close(symbol, msx2[0], msx2[-1])
        except stocks.StockError as exc:
            log(f"  [경고] 해외 주가 {blk} ({symbol}) — {exc}")
            data[blk]["stk"] = [None] * len(msx2)
            data[blk]["stkR"] = [None] * len(msx2)
            continue
        data[blk]["stk"] = [None if m not in rows else half_up(rows[m], 1)
                            for m in msx2]
        y, m0 = int(msx2[0][:4]), int(msx2[0][5:7])
        before = f"{y - 1}-12" if m0 == 1 else f"{y}-{m0 - 1:02d}"
        chain = [rows.get(before)] + [rows.get(x) for x in msx2]
        data[blk]["stkR"] = [
            None if (chain[i] is None or chain[i - 1] is None)
            else half_up((chain[i] / chain[i - 1] - 1) * 100, 1)
            for i in range(1, len(chain))]
    log(f"  해외 stk/stkR  Yahoo Finance    {len(sources.OECD_STOCKS)}개 지수")

    # --- ECB: 환율과 정책금리 ---
    try:
        for key, (cur, dig) in sources.FX_MONTHLY.items():
            got = ecb.monthly_fx(cur, months[0])
            mode = sources.ROUND_MODE.get(key, "binary")
            meta[key] = [None if got.get(p) is None else half_up(got[p], dig, mode)
                         for p in months]
        for key, cur in sources.FX_ANNUAL.items():
            got = ecb.annual_fx(cur, years[0])
            meta[key] = [got.get(y) for y in years]
        rates = {k: ecb.month_end(ecb.series("FM", key, months[0]))
                 for k, key in sources.POLICY.items()}
        for key, got in rates.items():
            meta[key] = [None if got.get(p) is None else half_up(got[p], 2)
                         for p in months]
        daily = ecb.series("FM", sources.POLICY["dfr"], months[0])
        last = sorted(daily)[-1]
        meta["pol"] = {"date": _decision_date(daily), "dfr": daily[last],
                       "mro": ecb.series("FM", sources.POLICY["mro"],
                                         months[0])[last]}
        log(f"  ECB   환율·정책금리      최근 결정 {meta['pol']['date']}")
    except ecb.EcbError as exc:
        log(f"  [실패] ECB — {exc}")

    fill_daily(data, meta)

    # SDMX 는 차원을 덜 좁혀도 200 으로 답하고 여러 계열을 함께 준다. 받는
    # 쪽에서 마지막 것만 남으므로 값은 멀쩡해 보이는데 내용이 다른 것일 수
    # 있다. oecd.series 가 그런 자리를 세어 두었으면 여기서 드러낸다.
    for clash in oecd.CLASHES:
        log(f"  [경고] 계열이 겹친다 — {clash}")

    # 아직 못 옮긴 계열은 이전 판에서 그대로
    carried = []
    for blk in sources.GEO:
        for key in sources.CARRY_OVER:
            if key in prev.get(blk, {}):
                data[blk][key] = prev[blk][key]
                carried.append(key)
    if carried:
        log(f"  이전 판에서 물려 온 계열: {sorted(set(carried))}")

    # 화면 코드가 기대하는 계열이 빠지면 차트가 빈 칸으로 뜬다. 미리 잡는다.
    # dl 은 차트 계열이 아니라 '진행 중인 달을 언제 값으로 채웠나'를 적어 두는
    # 기록이다. 이 검사는 fill_daily 보다 먼저 도므로 그때는 당연히 비어 있는데,
    # 빠진 계열로 보고 **전날 날짜를 물려받는다**. 그러면 오늘 채우지 못한
    # 계열의 축에 어제 날짜가 남아, 없는 값을 있는 것처럼 적게 된다.
    expected = set(prev["EZ"]) - {"dl"}
    for blk in sources.GEO:          # 유로 블록만. 해외 블록은 계열 구성이 다르다.
        missing = expected - set(data[blk])
        if missing:
            log(f"  [경고] {blk} 에 없는 계열: {sorted(missing)} — 이전 판에서 채운다")
            for key in missing:
                data[blk][key] = prev[blk][key]
    return data


def _decision_date(daily: dict[str, float]) -> str:
    """값이 마지막으로 바뀐 날 = 그 금리를 정한 결정이 발효된 날."""
    days = sorted(daily)
    last = daily[days[-1]]
    for day in reversed(days):
        if daily[day] != last:
            return days[days.index(day) + 1]
    return days[0]


# ------------------------------------------------------------------ 대조
def compare(new: dict, old: dict) -> int:
    diffs = 0
    for blk in sources.GEO:
        for key in sorted(set(old.get(blk, {})) & set(new.get(blk, {}))):
            a, b = old[blk][key], new[blk][key]
            if not isinstance(a, list) or not isinstance(b, list):
                continue
            if len(a) != len(b):
                log(f"  [길이] {blk}.{key}: {len(a)} -> {len(b)}")
                diffs += 1
                continue
            bad = [(i, x, y) for i, (x, y) in enumerate(zip(a, b))
                   if (x is None) != (y is None)
                   or (x is not None and abs(x - y) > 1e-6)]
            if bad:
                diffs += 1
                head = ", ".join(f"[{i}] {x}->{y}" for i, x, y in bad[:3])
                log(f"  [다름] {blk}.{key}: {len(bad)}곳 — {head}")
    return diffs


def fill_kr_items(data: dict, meta: dict, log=log) -> None:
    """한국 품목별 물가를 ECOS 에서 받아 전년동월비로 바꾼다.

    ECOS 는 지수를 주므로 상승률은 여기서 낸다. 한 해 전 값이 필요하므로
    26개월을 받아 둔다. 기준 달은 '전년동월이 함께 있는 가장 최근 달' 로
    잡되, 항목마다 발표가 어긋날 수 있으므로 총지수에서 정하고 나머지는
    그 달에 맞춘다 — 항목마다 다른 달을 쓰면 막대끼리 견줄 수 없다.
    """
    blk = sources.KR_ITEM_BLOCK
    today = datetime.date.today()
    start = f"{today.year - 3}01"
    end = f"{today.year}{today.month:02d}"

    head_code, head_table = sources.KR_ITEMS["itH"][0]
    # 기준 달은 총지수에서 정한다. 항목마다 다른 달을 쓰면 막대끼리 견줄 수
    # 없다. 이것마저 실패하면 구획을 통째로 건너뛴다 — 기준 달 없이는 아무
    # 막대도 뜻이 없다.
    base = ecos.latest_month(
        ecos.series(head_table, head_code, "M", start, end))
    if not base:
        raise ecos.EcosError("총지수에서 기준 달을 정하지 못했다")
    meta["krItemMonth"] = f"{base[:4]}-{base[4:]}"

    for key, items in sources.KR_ITEMS.items():
        values = []
        for code, table in items:
            try:
                idx = ecos.series(table, code, "M", start, end)
            except Exception as exc:          # noqa: BLE001
                # 한 항목이 실패했다고 구획 전체를 잃으면 안 된다. ECOS 는
                # 호출이 몰리면 JSON 이 아닌 것을 200 으로 돌려주기도 한다.
                log(f"    └ {key} {code} — {type(exc).__name__}: {exc}")
                values.append(None)
                continue
            rate = ecos.yoy(idx, base)
            values.append(None if rate is None else half_up(rate, 1))
        # setdefault 로 받는다. sources.GEO 에는 유로지역 아홉 곳만 있고 한국
        # 칸은 해외 구획(아래쪽)에서 만들어지는데, 이 함수는 그보다 먼저
        # 돈다. data[blk] 로 바로 쓰면 KeyError 가 나고, 바깥의 except 가
        # KeyError 를 잡아 '[실패] 한국 품목별 물가' 한 줄만 남긴 채 품목
        # 차트 셋이 통째로 빠진다 — 값이 틀리는 것이 아니라 없어지므로
        # 화면을 열어 보지 않으면 모른다. 실제로 그렇게 한 번 나갔다.
        data.setdefault(blk, {})[key] = values
        have = sum(1 for v in values if v is not None)
        log(f"  품목 KR.{key:4} ECOS {sources.KR_CPI_TABLE}   "
            f"{meta['krItemMonth']} 기준 {have}/{len(values)}항목")


def fill_kr_trade(data: dict, meta: dict) -> None:
    """미국·중국·일본의 대한국 수출입을 ECOS 에서 거울상으로 받는다.

    한국이 신고한 값이므로 방향이 뒤집힌다 — 한국의 대미 '수입'이 미국의
    대한국 '수출'이다. 유로지역 차트는 유럽이 신고한 값이라 같은 교역도
    금액이 어긋나는데, 그것은 각주에 적는다.

    한 나라가 실패해도 나머지는 남긴다. 셋이 한 묶음일 이유가 없다.
    """
    years = meta["years"]
    for blk, code in sources.KR_TRADE_AREAS.items():
        kr: dict[str, list] = {}
        try:
            for key, item in sources.KR_TRADE_FLOW.items():
                rows = ecos.series(sources.KR_TRADE_TABLE, f"{item}/{code}",
                                   "A", years[0], years[-1])
                # 천달러 -> 백만달러. 화면에서 다시 1e3 으로 나눠 십억이 된다.
                kr[key] = [None if rows.get(y) is None
                           else half_up(rows[y] / 1e3, 1) for y in years]
        except Exception as exc:                      # noqa: BLE001
            log(f"    └ {blk} 대한국 교역 — {type(exc).__name__}: {exc}")
            continue
        data.setdefault(blk, {})["kr"] = kr
        have = sum(1 for v in kr["ex"] if v is not None)
        log(f"  대한국 {blk}  ECOS {sources.KR_TRADE_TABLE}   "
            f"{years[0]}~{years[-1]} {have}/{len(years)}개년")


def fill_daily(data: dict, meta: dict, log=log) -> None:
    """진행 중인 달 칸을 최근일 값으로 채운다.

    까닭과 '무엇을 채우고 무엇을 안 채우는가'는 daily.py 머리글에 적었다.
    여기서는 채운 날짜를 계열별로 남기는 것이 중요하다 — 화면이 그 날짜로
    축 이름을 바꿔 하루치 값임을 드러낸다.
    """
    months = meta["months"]
    cur = months[-1]
    since = shift_month(cur, -2) + "-01"

    def put(bucket, block, name, day, value, digits):
        """마지막 달 칸에 값과 날짜를 함께 넣는다."""
        if day[:7] != cur:
            log(f"    └ {block}.{name} 최근일 {day} 은 {cur} 이 아니다 — 건너뛴다.")
            return False
        bucket[name][-1] = half_up(value, digits)
        data[block].setdefault("dl", {})[name] = day
        return True

    log("\n진행 중인 달을 최근일로 채운다:")

    # 주가지수 — 같은 Yahoo 종가라 그대로 이어진다.
    got = []
    for blk, sym in list(stocks.SYMBOLS.items()) + list(sources.OECD_STOCKS.items()):
        try:
            day, close = daily.yahoo_last(sym)
        except daily.DailyError as exc:
            log(f"    └ {blk} 주가({sym}) — {exc}")
            continue
        if put(data[blk], blk, "stk", day, close, 1):
            # 등락률은 직전 달 종가에서 다시 낸다.
            prev_close = data[blk]["stk"][-2]
            if prev_close:
                data[blk]["stkR"][-1] = half_up(
                    (close / prev_close - 1) * 100, 1)
                data[blk].setdefault("dl", {})["stkR"] = day
            got.append(f"{blk} {day[5:]}")
    log(f"  주가   {len(got)}개  " + ", ".join(got))

    # 달러지수 — 주가와 같은 Yahoo 종가.
    for blk, sym in sources.DOLLAR_INDEX.items():
        try:
            day, close = daily.yahoo_last(sym)
            put(data[blk], blk, "fxU", day, close, 2)
            log(f"  달러지수 {blk} {day}")
        except daily.DailyError as exc:
            log(f"    └ {blk} 달러지수({sym}) — {exc}")

    # 미국 10년물 — ^TNX. OECD 계열과 1bp 안에서 같다(daily.py 참고).
    for blk, sym in sources.DAILY_YIELD.items():
        try:
            day, value = daily.yahoo_last(sym)
            put(data[blk], blk, "y10", day, value, 2)
            log(f"  10년물 {blk} {day} {value:.2f}")
        except daily.DailyError as exc:
            log(f"    └ {blk} 10년물({sym}) — {exc}")

    # 한국 10년물 — ECOS 시장금리(일별)의 국고채 10년. 야후에 티커가 없어
    # 출처가 여기만 다르다. OECD 월간과 같은 계열이다(sources.py 참고).
    if ecos.have_key():
        for blk, (table, item) in sources.ECOS_DAILY_YIELD.items():
            try:
                day, value = daily.ecos_last(table, item, since)
                if put(data[blk], blk, "y10", day, value, 2):
                    log(f"  10년물 {blk} {day} {value:.2f}")
            except (daily.DailyError, ecos.EcosError,
                    ValueError, KeyError) as exc:
                log(f"    └ {blk} 10년물(ECOS) — {exc}")
    else:
        log("    └ KR 10년물 — ECOS_API_KEY 가 없어 건너뛴다")

    # 대유로 환율 — 같은 ECB 기준환율.
    for blk, cur_code in sources.ECB_FX_PER_EUR.items():
        try:
            day, value = daily.ecb_last(cur_code, since)
            put(data[blk], blk, "fxE", day, value, 2)
        except (daily.DailyError, ecb.EcbError) as exc:
            log(f"    └ {blk} 대유로 환율 — {exc}")

    # 대미달러 환율 — ECB 기준환율 교차. OECD 월평균과 거의 같다.
    for blk, cur_code in sources.ECB_FX_PER_EUR.items():
        try:
            day, value = daily.ecb_cross_last(cur_code, since)
            put(data[blk], blk, "fxU", day, value, 2)
        except (daily.DailyError, ecb.EcbError) as exc:
            log(f"    └ {blk} 대미달러 환율 — {exc}")
    log(f"  환율   {sources.ECB_FX_PER_EUR} 대유로·대미달러")

    # 유로 탭이 쓰는 EUR/USD·EUR/KRW 는 meta 에 있다.
    for key, (cur_code, digits) in sources.FX_MONTHLY.items():
        try:
            day, value = daily.ecb_last(cur_code, since)
        except (daily.DailyError, ecb.EcbError) as exc:
            log(f"    └ meta.{key} — {exc}")
            continue
        if day[:7] != cur:
            continue
        mode = sources.ROUND_MODE.get(key, "binary")
        meta[key][-1] = half_up(value, digits, mode)
        meta.setdefault("dl", {})[key] = day
        log(f"  meta.{key:6} {day} {meta[key][-1]}")


def load_env() -> None:
    """.env 를 환경변수로 읽는다 (python-dotenv 없이).

    클라우드에서는 Actions Secret 이 환경변수로 들어오므로 이 파일이 없다.
    손으로 돌릴 때만 쓰인다. 저장소가 공개라 .env 는 커밋되지 않는다.
    """
    path = BASE / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    ap = argparse.ArgumentParser(description="주요국 경제 차트팩 빌드")
    ap.add_argument("--check", action="store_true",
                    help="쓰지 않고 지금 index.html 과 대조만 한다")
    args = ap.parse_args()

    load_env()
    prev = previous()
    data = build(prev)

    log("\n지금 index.html 과 대조:")
    if data["meta"]["months"] != prev["meta"]["months"]:
        log("기간 축이 밀렸다 — 이전 판과 값을 자리별로 견줄 수 없다.")
        log(f"  이전 {prev['meta']['months'][-1]} -> 지금 "
            f"{data['meta']['months'][-1]}")
        diffs = 0
    else:
        diffs = compare(data, prev)
    log(f"→ 달라진 계열 {diffs}개" if diffs else "→ 모든 계열이 같다")

    if args.check:
        log("--check: 파일을 쓰지 않았다.")
        return 0

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob)
    html = html.replace("__OPS__", ops_blob(data))
    OUTPUT.write_text(html, encoding="utf-8")
    log(f"\nindex.html 갱신 — {len(html):,}자 (데이터 {len(blob):,}자)")
    return 0


# ------------------------------------------------------------------ 자체 기록
# 페이지에 사람 눈에 안 보이는 한 덩어리를 심는다. 독자에게는 쓸모가 없고
# 주간 점검에만 쓰인다. 별도 파일로 두지 않는 까닭은 GitHub Pages 에 이미
# 올라가는 파일 안에 있으면 받는 쪽이 주소 하나로 끝나기 때문이다.
def fillable() -> dict[str, set[str]]:
    """블록마다 '진행 중인 달을 채울 수 있는' 계열.

    빈 칸을 셀 때 이 명단 안에서만 센다. 유로지역·중국·일본의 10년물은
    애초에 일별을 내는 무료 출처가 없어 늘 비어 있는데(sources.DAILY_YIELD
    의 설명), 그것을 매주 지적하면 보고가 울리는 것에 익숙해져 정작 고쳐야
    할 날에도 넘기게 된다. 셀 것은 '채울 수 있었는데 안 채워진 것'뿐이다.
    """
    plan: dict[str, set[str]] = {}
    for blk in list(stocks.SYMBOLS) + list(sources.OECD_STOCKS):
        plan.setdefault(blk, set()).add("stk")
    for blk in list(sources.DAILY_YIELD) + list(sources.ECOS_DAILY_YIELD):
        plan.setdefault(blk, set()).add("y10")
    for blk in sources.ECB_FX_PER_EUR:
        plan.setdefault(blk, set()).update(("fxE", "fxU"))
    for blk in sources.DOLLAR_INDEX:
        plan.setdefault(blk, set()).add("fxU")
    return plan


def ops_blob(data: dict) -> str:
    """빌드 상태를 JSON 한 줄로."""
    months = data["meta"]["months"]
    plan = fillable()
    holes = {}
    for blk, block in data.items():
        if blk == "meta":
            continue
        gap = sorted(k for k in plan.get(blk, ())
                     if k in block and block[k] and block[k][-1] is None)
        if gap:
            holes[blk] = gap
    ops = {
        "built": datetime.datetime.now(datetime.UTC)
                         .strftime("%Y-%m-%dT%H:%MZ"),
        "month": months[-1],
        "asOf": data["meta"].get("asOf"),
        "krItemMonth": data["meta"].get("krItemMonth"),
        "filled": {blk: sorted(block.get("dl", {}))
                   for blk, block in data.items()
                   if blk != "meta" and block.get("dl")},
        "holes": holes,
        "trouble": TROUBLE,
    }
    # </script> 가 값 안에 들어가면 스크립트 태그가 끊긴다. '<' 를 막아 둔다.
    return json.dumps(ops, ensure_ascii=False).replace("<", "\\u003c")


if __name__ == "__main__":
    raise SystemExit(main())
