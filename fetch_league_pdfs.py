"""T リーグの過去シーズンの日程・星取表 PDF を、インターネットアーカイブから集める。

公式（tleague-u18.com）は今季と前季しか残さないが、アーカイブには 2020〜2024 年度の
PDF が残っている。ファイル名は T1-1.pdf（日程と結果）・T1-★.pdf（星取表）の形。

年度の決め方: URL の ?data=YYYYMMDD（公開日）を 4月始まりの年度に直す。
無い場合はアーカイブされた日時から同じように決める。同じ年度・同じ部なら、
いちばん新しい公開日のものを採る（シーズン終盤の版がいちばん埋まっている）。

  uv run python fetch_league_pdfs.py --list
  uv run python fetch_league_pdfs.py

出力: pdfs/leagues/<年度>_<ファイル名>.pdf、raw/archive/league_manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw/archive"
OUT = ROOT / "pdfs/leagues"
CDX = ("http://web.archive.org/cdx/search/cdx?url=tleague-u18.com&matchType=domain"
       "&filter=statuscode:200&filter=original:.*\\.pdf&fl=timestamp,original&limit=3000")
UA = {"User-Agent": "Mozilla/5.0 (compatible; tokyo-soccer-brackets/1.0)"}
WAIT = 2.0


def season_of(yyyymmdd: str) -> int:
    """4月始まりの年度。2024-03-31 は 2023年度、2024-04-01 は 2024年度。"""
    y, m = int(yyyymmdd[:4]), int(yyyymmdd[4:6])
    return y if m >= 4 else y - 1


def rows(refresh: bool) -> list[tuple[str, str]]:
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / "cdx_tleague_pdf_all.txt"
    if refresh or not p.exists():
        req = urllib.request.Request(CDX, headers=UA)
        p.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out.append((parts[0], urllib.parse.unquote(parts[1])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    best: dict[tuple[int, str], tuple[str, str, str]] = {}
    for ts, url in rows(args.refresh):
        name = url.split("?")[0].rsplit("/", 1)[-1]
        # 個々の試合結果（p_1743503708.pdf）ではなく、部ごとの日程・星取表だけを採る
        if not re.match(r"T\d", name):
            continue
        d = re.search(r"data=(\d{8})", url)
        pub = d[1] if d else ts[:8]
        season = season_of(pub)
        key = (season, name)
        if key not in best or pub > best[key][0]:
            best[key] = (pub, ts, url)

    items = [{"season": s, "name": n, "pub": v[0], "ts": v[1], "url": v[2]} for (s, n), v in best.items()]
    items.sort(key=lambda x: (x["season"], x["name"]))
    print(f"対象 {len(items)} 本")
    by: dict[int, list[str]] = {}
    for it in items:
        by.setdefault(it["season"], []).append(it["name"])
    for s, names in sorted(by.items()):
        print(f"  {s}年度 {len(names):2}本  " + " ".join(sorted(set(names))))
    if args.list:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    man = RAW / "league_manifest.csv"
    exists = man.exists()
    got = skip = fail = 0
    with man.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "season", "pub", "ts", "url", "bytes", "at"])
        if not exists:
            w.writeheader()
        for it in items:
            safe = re.sub(r"[^A-Za-z0-9._-]", "", it["name"].replace("★", "-star"))
            dest = OUT / f"{it['season']}_{safe}"
            if dest.exists() and dest.stat().st_size > 0:
                skip += 1
                continue
            wb = "https://web.archive.org/web/" + it["ts"] + "id_/" + urllib.parse.quote(it["url"], safe=":/?=&")
            try:
                req = urllib.request.Request(wb, headers=UA)
                data = urllib.request.urlopen(req, timeout=90).read()
                if not data.startswith(b"%PDF"):
                    raise ValueError("PDFではない中身")
                dest.write_bytes(data)
                w.writerow({"file": dest.name, "season": it["season"], "pub": it["pub"], "ts": it["ts"],
                            "url": it["url"], "bytes": len(data), "at": time.strftime("%Y-%m-%d %H:%M:%S")})
                f.flush()
                got += 1
                print(f"  取得 {dest.name}  {len(data) // 1024}KB")
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"  失敗 {dest.name}: {e}")
            time.sleep(WAIT)
    print(f"完了: 取得 {got} / 既にある {skip} / 取れず {fail} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
