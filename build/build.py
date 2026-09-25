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
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "build"))

import ecb                                                       # noqa: E402
import eurostat                                                  # noqa: E402
import sources                                                   # noqa: E402
import stocks                                                    # noqa: E402

TEMPLATE = BASE / "template.html"
OUTPUT = BASE / "index.html"

DATA_RE = re.compile(r"const DATA = (\{.*?\});\n", re.S)


def log(msg: str) -> None:
    print(msg, flush=True)


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


def build(prev: dict) -> dict:
    # 기간 축(months·qs·years)은 이전 판의 것을 그대로 쓴다. 아직 옮기지 못한
    # 계열(sources.CARRY_OVER)이 이 길이에 맞춰 물려 오기 때문이다. 축을 늘리면
    # 그 계열들만 짧아져 차트가 어긋난다.
    #
    # 그래서 지금 이 빌드는 "있는 기간의 수치를 최신으로 고치는" 일까지만 한다.
    # 새 달을 붙이려면 남은 계열을 먼저 API 로 옮겨야 한다. 그 전에 축만 늘리면
    # 안 된다.
    meta = prev["meta"]
    months, qs, years = meta["months"], meta["qs"], meta["years"]

    data: dict = {"meta": json.loads(json.dumps(meta))}
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
            live = {b: g for b, g in sources.GEO.items()
                    if b not in sources.IMM_CARRY_BLOCKS}
            imm = eurostat.series("migr_imm1ctz", sorted(live.values()),
                                  since=ym[0], **sources.IMM_FILTERS)
            pop = eurostat.series("demo_gind", sorted(live.values()),
                                  since=ym[0], indic_de="AVG")
            for blk, geo in live.items():
                rows = imm.get(geo, {})
                data[blk]["imm"] = [None if rows.get(y) is None
                                    else half_up(rows[y] / 1000, 1) for y in ym]
                data[blk]["immR"] = [
                    None if (rows.get(y) is None or not pop.get(geo, {}).get(y))
                    else half_up(rows[y] / pop[geo][y] * 100, 2) for y in ym]
            log(f"  연  imm/immR migr_imm1ctz     {len(live)}개국 "
                f"(유로지역은 그리스 결측으로 물려 씀)")
        except eurostat.EurostatError as exc:
            log(f"  [실패] 이민 — {exc}")

    # --- 주가지수 (월말 종가) ---
    # 기간 축이 또 다르다. monthsS 는 진행 중인 달까지 포함해 한 달 더 길다.
    msx = meta.get("monthsS") or months
    closes = stocks.all_closes(msx[0], msx[-1], log)
    for blk in sources.GEO:
        rows = closes.get(blk)
        if not rows:
            # 받지 못한 지수는 이전 판을 물려 쓴다. 길이가 달라지면 그때는
            # 비워 둔다 — 옛 숫자를 새 달의 값인 척 밀어 넣으면 안 된다.
            old_lvl = prev.get(blk, {}).get("stk") or []
            data[blk]["stk"] = (old_lvl if len(old_lvl) == len(msx)
                                else [None] * len(msx))
            data[blk]["stkR"] = (prev.get(blk, {}).get("stkR") or [])[:len(msx)]                 or [None] * len(msx)
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

    # 아직 못 옮긴 계열은 이전 판에서 그대로
    carried = []
    for blk in sources.IMM_CARRY_BLOCKS:
        for key in ("imm", "immR"):
            if key in prev.get(blk, {}):
                data[blk][key] = prev[blk][key]
                carried.append(f"{blk}.{key}")
    for blk in sources.GEO:
        for key in sources.CARRY_OVER:
            if key in prev.get(blk, {}):
                data[blk][key] = prev[blk][key]
                carried.append(key)
    if carried:
        log(f"  이전 판에서 물려 온 계열: {sorted(set(carried))}")

    # 화면 코드가 기대하는 계열이 빠지면 차트가 빈 칸으로 뜬다. 미리 잡는다.
    expected = set(prev["EZ"])
    for blk in sources.GEO:
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


def main() -> int:
    ap = argparse.ArgumentParser(description="유로지역 경제 차트팩 빌드")
    ap.add_argument("--check", action="store_true",
                    help="쓰지 않고 지금 index.html 과 대조만 한다")
    args = ap.parse_args()

    prev = previous()
    data = build(prev)

    log("\n지금 index.html 과 대조:")
    diffs = compare(data, prev)
    log(f"→ 달라진 계열 {diffs}개" if diffs else "→ 모든 계열이 같다")

    if args.check:
        log("--check: 파일을 쓰지 않았다.")
        return 0

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob)
    OUTPUT.write_text(html, encoding="utf-8")
    log(f"\nindex.html 갱신 — {len(html):,}자 (데이터 {len(blob):,}자)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
