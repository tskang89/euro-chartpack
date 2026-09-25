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

import eurostat                                                  # noqa: E402
import sources                                                   # noqa: E402

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


def half_up(value: float, digits: int):
    """사람이 쓰는 반올림 — 5는 올린다.

    파이썬 기본 round 는 5를 짝수 쪽으로 보낸다(601866.5 -> 601866). 통계표는
    올림 쪽이라 601867 이어야 한다.

    Decimal(str(v)) 가 아니라 Decimal(v) 로 감싸는 것이 중요하다. 앞의 것은
    2.405 를 글자 그대로 2.405 로 보아 2.41 로 올리지만, 부동소수점이 실제로
    담고 있는 값은 2.40499999… 라서 2.40 이 맞다. 원본 차트팩도 그 값으로
    반올림했다. str 를 거치면 없는 정밀도를 지어내는 셈이 된다."""
    q = Decimal(1).scaleb(-digits)
    d = Decimal(value).quantize(q, rounding=ROUND_HALF_UP)
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
    expected = set(prev["EZ"])
    for blk in sources.GEO:
        missing = expected - set(data[blk])
        if missing:
            log(f"  [경고] {blk} 에 없는 계열: {sorted(missing)} — 이전 판에서 채운다")
            for key in missing:
                data[blk][key] = prev[blk][key]
    return data


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
