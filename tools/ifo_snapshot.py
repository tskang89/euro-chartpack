# -*- coding: utf-8 -*-
"""ifo 업황지수를 사무소 PC 에서 받아 저장소에 올린다.

**왜 사무소에서 받는가.** 런너에서 ifo 가 들쭉날쭉하다. 2026-11-23 에
세 번 돌려 두 번 실패했다 — 06:05Z 와 13:10Z 는 넉 달치(202611~202608)를
하나도 받지 못했고, 13:41Z 는 그대로 받혔다. 11-20 까지는 탈이 없었다.
같은 날 사무소 IP 로는 202610·202609 가 늘 내려왔다(각 102KB, 내용이
PK 로 시작).

실패해도 빌드는 성공으로 끝난다 — build.py 가 이전 판 값을 물려 쓰기
때문이다. 차트가 멀쩡해 보이므로 눈에 띄지 않는데, 하필 발표 당일 판이
실패하면 그달 값이 통째로 비껴간다. 그래서 늘 받히는 자리에서 받아
`data/ifo.json` 으로 올려 두고, 런너는 막히는 판에서 그것을 읽는다
(build/ifo.py 의 series).

**푸시가 곧 빌드를 부른다.** build.yml 에 `data/ifo.json` 만 보는 push
방아쇠를 달아 두었다. 그래서 새 달치가 올라가면 그 자리에서 차트팩이 다시
그려진다 — 이튿날 아침까지 기다리지 않는다. 바뀐 것이 없으면 커밋을 아예
하지 않으므로 헛빌드도 없다.

평일 06:40 과 11:00 에 돈다. 06:40 은 07:05 차트팩 빌드 앞자리이고,
11:00 은 ifo 가 발표하는 시각(매달 말 10:00 CET) 뒤를 받는 자리다.

손으로 돌려 보려면:
    python tools/ifo_snapshot.py          # 받아서 바뀌었으면 올린다
    python tools/ifo_snapshot.py --dry-run  # 받아만 보고 아무것도 하지 않는다
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import ifo                                                   # noqa: E402


def log(*parts) -> None:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(stamp, *parts, flush=True)


def git(*args: str, check: bool = True) -> str:
    done = subprocess.run(("git", "-C", str(ROOT)) + args,
                          capture_output=True, text=True, encoding="utf-8")
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} — {done.stderr.strip()}")
    return (done.stdout or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="받아만 보고 쓰지도 올리지도 않는다")
    args = ap.parse_args()

    try:
        got, ym = ifo.fresh(log=lambda m: log(m.strip()))
    except Exception as exc:                       # noqa: BLE001
        log(f"[실패] ifo 를 받지 못했다 — {exc}")
        log("       저장분을 그대로 둔다. 런너는 지난 저장분을 계속 읽는다.")
        return 1

    newest = max(got["all"]) if got["all"] else "?"
    log(f"받았다 — gsk-e-{ym}.xlsx, 전체 지수 마지막 달 {newest} "
        f"({got['all'].get(newest)})")

    if args.dry_run:
        log("--dry-run 이라 여기서 멈춘다")
        return 0

    # 저장소가 날마다 index.html 을 되커밋하므로 먼저 당겨 놓는다.
    git("pull", "--rebase", "--quiet")

    if not ifo.write_snapshot(got, ym):
        log("바뀐 것이 없다 — 커밋하지 않는다")
        return 0

    rel = ifo.SNAPSHOT.relative_to(ROOT).as_posix()
    git("add", rel)
    if not git("diff", "--cached", "--name-only"):
        log("바뀐 것이 없다 — 커밋하지 않는다")
        return 0
    git("commit", "--quiet", "-m",
        f"ifo 저장분 갱신 — gsk-e-{ym}, 마지막 달 {newest}\n\n"
        "사무소 PC 예약 작업이 올린 것이다. 런너에서는 ifo 가 열리지\n"
        "않는다(tools/ifo_snapshot.py 머리말). 이 커밋이 차트팩 빌드를\n"
        "부른다 — build.yml 의 push 방아쇠가 이 파일만 본다.")
    git("push", "--quiet")
    log(f"올렸다 — {rel} ({ym}). 차트팩 빌드가 곧 돈다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
