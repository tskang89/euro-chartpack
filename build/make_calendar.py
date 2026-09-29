# -*- coding: utf-8 -*-
"""calendar.html 을 만든다 — 오늘부터 이레 치 일정 한 장.

조간 브리핑 맨 아래 '참고자료'에서 차트팩 다음으로 걸리는 쪽이다. 하루 한
번 새로 만든다. 자료가 어디서 왔고 무엇이 빠졌는지는 페이지 아래 각주에
그대로 적는다 — 빠진 것을 말하지 않으면 없는 일정으로 읽힌다.
"""

from __future__ import annotations

import argparse
import datetime
import html
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import policy_dates                                          # noqa: E402
import schedule                                              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "calendar_template.html"
OUTPUT = ROOT / "calendar.html"

WEEKDAY = "월화수목금토일"
DAYS = 7

TAG = {"policy": "통화정책", "meeting": "회의", "release": "지표"}


def log(msg: str = "") -> None:
    print(msg, flush=True)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_days(events: list[dict], today: datetime.date) -> str:
    by_day: dict[str, list[dict]] = {}
    for e in events:
        by_day.setdefault(e["date"], []).append(e)

    out = []
    for i in range(DAYS):
        day = today + datetime.timedelta(days=i)
        key = day.isoformat()
        rows = by_day.get(key, [])
        # 일정이 없는 주말은 아예 접는다. 빈 칸이 이레 내내 이어지면
        # 정작 있는 날이 묻힌다.
        if not rows and day.weekday() >= 5:
            continue
        cls = "day today" if i == 0 else "day"
        head = (f'<h2><span class="d">{day.month}.{day.day}</span>'
                f'<span class="w">{WEEKDAY[day.weekday()]}요일</span></h2>')
        if not rows:
            body = '<div class="empty">예정된 발표·회의가 없습니다</div>'
        else:
            items = []
            for e in rows:
                items.append(
                    f'<li class="{esc(e["kind"])}">'
                    f'<span class="tag">{TAG.get(e["kind"], e["kind"])}</span>'
                    f'<span class="body">'
                    f'<a class="src" href="{esc(e["url"])}" target="_blank" '
                    f'rel="noopener"><span class="who">{esc(e["who"])}</span></a> '
                    f'<span class="what">{esc(e["what"])}</span>'
                    f'</span></li>')
            body = "<ul>" + "".join(items) + "</ul>"
        out.append(f'<section class="{cls}">{head}{body}</section>')
    return "\n".join(out)


NOTE = """<b>자료</b> ECB 이사회·통화정책회의 일정, 독일 통계청(Destatis)
발표일정은 두 기관의 공식 일정표에서 날마다 새로 받아 옵니다. 폴란드·체코·
스위스·튀르키예 중앙은행의 통화정책 결정일은 네 곳 모두 자동 수집이 막혀
있어(봇 차단·자바스크립트 렌더링) 공식 발표에서 확인한 날짜를 저장소에 적어
두고 씁니다. 기관 이름을 누르면 공식 일정표로 갑니다.
<br><br>
<b>빠진 것</b>
<ul>
<li>유로지역 지표(HICP 속보치·GDP 등) 발표일 — Eurostat 일정표가 자바스크립트로
그려지고 공개 API 에 캘린더 경로가 없습니다. 독일 소비자물가가 유로지역
속보치보다 대개 하루 앞서므로 그쪽으로 가늠하실 수 있습니다.</li>
<li>독일 통계청은 지역·행정 통계까지 함께 내는데, 여기에는 물가·고용·생산·
교역·국민계정 같은 거시지표만 싣습니다.</li>
<li>연준·영란은행·일본은행 등은 아직 넣지 않았습니다.</li>
</ul>"""


def build(today: datetime.date) -> str:
    log(f"일정 수집 — {today} 부터 {DAYS}일")
    events, warn = schedule.week(today, DAYS, log=log)
    warn += policy_dates.health(today)
    for w in policy_dates.health(today):
        log(w)

    stamp = (f'{today.year}년 {today.month}월 {today.day}일 '
             f'({WEEKDAY[today.weekday()]}) 기준 · '
             f'<a href="./">주요국 경제 차트팩</a>')

    # 수집이 실패한 것은 화면에도 적는다. 조용히 빈 일정표를 내놓으면
    # '이번 주는 일정이 없다'로 읽힌다.
    fetch_fail = [w for w in warn if "받지 못했다" in w]
    warn_html = ""
    if fetch_fail:
        warn_html = ('<div class="warn"><b>일부 자료를 받지 못했습니다.</b> '
                     + " / ".join(esc(w) for w in fetch_fail)
                     + " 아래 일정이 전부가 아닐 수 있습니다.</div>")

    html_out = TEMPLATE.read_text(encoding="utf-8")
    html_out = html_out.replace("__STAMP__", stamp)
    html_out = html_out.replace("__DAYS__", render_days(events, today))
    html_out = html_out.replace("__WARN__", warn_html)
    html_out = html_out.replace("__NOTE__", NOTE)
    log(f"\n일정 {len(events)}건")
    return html_out


def main() -> int:
    ap = argparse.ArgumentParser(description="향후 1주일 주요 일정 페이지")
    ap.add_argument("--check", action="store_true",
                    help="쓰지 않고 만들어만 본다")
    ap.add_argument("--date", help="기준일을 바꿔 본다 (YYYY-MM-DD)")
    args = ap.parse_args()

    today = (datetime.date.fromisoformat(args.date) if args.date
             else datetime.date.today())
    page = build(today)
    if args.check:
        log("--check: 파일을 쓰지 않았다.")
        return 0
    OUTPUT.write_text(page, encoding="utf-8")
    log(f"calendar.html 갱신 — {len(page):,}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
