# -*- coding: utf-8 -*-
"""향후 일주일 일정을 공식 페이지에서 모은다.

두 곳만 자동으로 받아 온다. 나머지는 자동 수집이 막혀 있어 손으로 적은
표를 쓴다(policy_dates.py 에 까닭을 적었다).

  ECB      이사회·통화정책회의 일정. <dt>날짜</dt><dd>설명</dd> 짜임이라
           그대로 읽힌다.
  Destatis 독일 지표 발표일정. 결과 한 덩어리가 c-result 블록이고 그 안에
           제목·기준기간·발표일이 들어 있다.

유로지역 지표(HICP·GDP) 발표일은 넣지 못했다. Eurostat 의 release calendar
페이지가 자바스크립트로 그려지고, 공개 API 에 캘린더 경로가 없다. 독일
소비자물가가 유로지역 속보치보다 대개 하루 앞서므로 Destatis 쪽으로 어느
정도는 가늠할 수 있다.
"""

from __future__ import annotations

import datetime
import html
import re
import time

import requests

ECB_URL = "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"
DESTATIS_URL = ("https://www.destatis.de/SiteGlobals/Forms/Suche/Termine/"
                "DE/Terminsuche_Formular.html?nn=250582")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 40
RETRIES = 3


class ScheduleError(RuntimeError):
    pass


def _get(url: str) -> str:
    last = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT,
                                headers={"User-Agent": UA})
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or resp.encoding
                return resp.text
            last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise ScheduleError(f"{url.split('/')[2]}: {last}")


# ------------------------------------------------------------------ ECB
# 통화정책과 관계없는 회의도 한 목록에 섞여 있다. 무엇이 금리 결정인지
# 구분해 표시해야 하므로 설명 문구로 가른다.
# 'non-monetary policy meeting' 이 'monetary policy meeting' 을 품고 있다.
# 앞에 non- 이 붙지 않은 것만 골라야 한다 — 그러지 않으면 통화정책과
# 무관한 이사회가 '금리 결정일'로 올라간다.
_ECB_POLICY = re.compile(r"(?<!non-)monetary policy meeting", re.I)
_ECB_PRESSER = re.compile(r"press conference", re.I)


def ecb_events() -> list[dict]:
    doc = _get(ECB_URL)
    pairs = re.findall(r"<dt>\s*(\d{2}/\d{2}/\d{4})\s*</dt>\s*"
                       r"<dd>\s*(.*?)\s*</dd>", doc, re.S)
    if not pairs:
        raise ScheduleError("ECB: <dt>/<dd> 짜임이 바뀌었다 — 하나도 못 읽었다")
    out = []
    for raw, desc in pairs:
        d, m, y = raw.split("/")
        text = html.unescape(re.sub(r"<[^>]+>", " ", desc))
        text = re.sub(r"\s+", " ", text).strip()
        out.append({
            "date": f"{y}-{m}-{d}",
            "kind": "policy" if _ECB_POLICY.search(text) else "meeting",
            "area": "EZ",
            "who": "ECB",
            "what": _ecb_ko(text),
            "url": ECB_URL,
        })
    return out


def _ecb_ko(text: str) -> str:
    """ECB 일정 문구를 우리말로. 못 알아본 것은 원문 그대로 둔다."""
    if _ECB_POLICY.search(text):
        base = "통화정책회의"
        if _ECB_PRESSER.search(text):
            return base + " 결정·기자회견 (둘째 날)"
        if re.search(r"day 1", text, re.I):
            return base + " (첫째 날)"
        return base
    if re.search(r"non-monetary policy meeting", text, re.I):
        return "이사회 (통화정책 외)"
    if re.search(r"General Council", text, re.I):
        return "일반이사회"
    return text


# ------------------------------------------------------------------ Destatis
_BLOCK = re.compile(r'<div\s+class="c-result c-result--event-preview.*?'
                    r'(?=<div\s+class="c-result c-result--event-preview|</body)',
                    re.S)
_HEAD = re.compile(r'class="c-result__heading">(.*?)</h3>', re.S)
_PERIOD = re.compile(r"<strong>Berichtzeitraum</strong>\s*:\s*([^<]+)")
_DAY = re.compile(r"<strong>Ver\w*ffentlichungstermin</strong>\s*:\s*"
                  r"(\d{2})\.(\d{2})\.(\d{4})")

# 브리핑을 받는 사람이 관심 둘 만한 것만 고른다. 독일 통계청은 하루에도
# 여러 건을 내는데, 지역 통계나 행정 자료까지 실으면 일정표가 길어져
# 정작 중요한 것이 묻힌다.
_KEEP = re.compile(
    r"Verbraucherpreis|Erzeugerpreis|Gro\w*handelspreis|Au\w*enhandel|"
    r"Inlandsprodukt|Bruttoinlandsprodukt|Arbeitsmarkt|Erwerbst|"
    r"Industrieproduktion|Produktion im Produzierenden|Auftragseingang|"
    r"Einzelhandel|Umsatz im|Baugenehmigung|Import|Export|"
    r"Verarbeitendes Gewerbe|Dienstleistungen", re.I)


# 독일 통계청 제목을 우리말로. 자주 나오는 것만 옮기고, 없으면 원문을
# 그대로 둔다 — 빠뜨리는 것보다 독일어로라도 보이는 편이 낫다.
_DE_KO = [
    (r"Verbraucherpreisindex", "소비자물가지수"),
    (r"Erzeugerpreise?", "생산자물가"),
    (r"Gro\w*handelspreise?", "도매물가"),
    (r"Index der Au\w*enhandelspreise", "수출입물가지수"),
    (r"Au\w*enhandel", "대외교역"),
    (r"Bruttoinlandsprodukt|Inlandsprodukt", "국내총생산"),
    (r"Monatliche Arbeitsmarktstatistik", "월간 고용통계"),
    (r"Arbeitsmarkt", "고용"),
    (r"Produktion im Produzierenden Gewerbe|Industrieproduktion", "산업생산"),
    (r"Verarbeitendes Gewerbe\s*—\s*Auftragseingangs- und Umsatzindex",
     "제조업 수주·매출"),
    (r"Auftragseingang", "제조업 수주"),
    (r"Einzelhandel\s*—\s*Umsatz", "소매판매"),
    (r"Dienstleistungen\s*—\s*Umsatz, Besch\w*ftigte", "서비스업 매출·고용"),
    (r"Baugenehmigungen?", "건축허가"),
]
_MONTH_KO = {"Januar": 1, "Februar": 2, "März": 3, "Maerz": 3, "April": 4,
             "Mai": 5, "Juni": 6, "Juli": 7, "August": 8, "September": 9,
             "Oktober": 10, "November": 11, "Dezember": 12}


def _de_title(title: str) -> str:
    for pat, ko in _DE_KO:
        if re.search(pat, title, re.I):
            extra = re.search(r"Vorl\w*ufige|Endg\w*ltige", title, re.I)
            tag = ""
            if extra:
                tag = " 속보치" if extra.group(0).lower().startswith("vorl") \
                    else " 확정치"
            return ko + tag
    return title


def _de_period(text: str) -> str:
    """'August 2026' -> '2026년 8월'. 분기·반기는 그대로 옮긴다."""
    text = text.strip()
    m = re.match(r"(\w+)\s+(\d{4})$", text)
    if m and m.group(1) in _MONTH_KO:
        return f"{m.group(2)}년 {_MONTH_KO[m.group(1)]}월"
    m = re.match(r"(\d)\.\s*Quartal\s+(\d{4})", text)
    if m:
        return f"{m.group(2)}년 {m.group(1)}분기"
    m = re.match(r"(\d)\.\s*Halbjahr\s+(\d{4})", text)
    if m:
        return f"{m.group(2)}년 상반기" if m.group(1) == "1" \
            else f"{m.group(2)}년 하반기"
    return text


def destatis_events(keep_all: bool = False) -> list[dict]:
    doc = _get(DESTATIS_URL)
    blocks = _BLOCK.findall(doc)
    if not blocks:
        raise ScheduleError("Destatis: c-result 블록을 하나도 못 읽었다")
    out = []
    for block in blocks:
        head, day = _HEAD.search(block), _DAY.search(block)
        if not head or not day:
            continue
        title = html.unescape(re.sub(r"<[^>]+>", " ", head.group(1)))
        title = re.sub(r"\s+", " ", title).replace(" — ", " — ").strip()
        if not keep_all and not _KEEP.search(title):
            continue
        period = _PERIOD.search(block)
        d, m, y = day.groups()
        what = _de_title(title)
        if period:
            what += f" · {_de_period(html.unescape(period.group(1)))}"
        out.append({
            "date": f"{y}-{m}-{d}",
            "kind": "release",
            "area": "DE",
            "who": "독일 통계청",
            "what": what,
            "url": DESTATIS_URL,
        })
    return out


# ------------------------------------------------------------------ 모으기
def week(today: datetime.date, days: int = 7, log=print) -> tuple[list, list]:
    """(일정, 경고). 오늘부터 days 일까지."""
    end = today + datetime.timedelta(days=days - 1)
    events, warn = [], []

    for name, fn in (("ECB", ecb_events), ("Destatis", destatis_events)):
        try:
            got = fn()
        except ScheduleError as exc:
            warn.append(f"{name} 일정을 받지 못했다 — {exc}")
            log(f"  [실패] {name} — {exc}")
            continue
        hit = [e for e in got
               if today <= datetime.date.fromisoformat(e["date"]) <= end]
        events += hit
        log(f"  {name:9} 전체 {len(got):3}건 중 이 주 {len(hit)}건")

    import policy_dates
    hit = policy_dates.upcoming(today, end)
    events += hit
    log(f"  중앙은행     표에서 이 주 {len(hit)}건")

    events.sort(key=lambda e: (e["date"], e["kind"] != "policy", e["who"]))
    return events, warn
