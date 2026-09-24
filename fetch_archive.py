"""公式サイトから消えた年のトーナメント表 PDF を、インターネットアーカイブから集める。

公式（tokyosoccer-u18.com）に残っているのは直近数年ぶんだけで、それ以前は消えている。
Wayback Machine には 2004 年度からの PDF が残っているので、そこから落として pdfs/archive/ に置く。

  uv run python fetch_archive.py --list          # 何が取れるかだけ見る
  uv run python fetch_archive.py --max-year 21   # 2021年度までを落とす（既存の 2022+ は触らない）

出力
  raw/archive/cdx_pdfs.txt   … アーカイブにある PDF の一覧（timestamp と URL）
  pdfs/archive/<COMP><YY>_<ファイル名>.pdf
  raw/archive/manifest.csv   … 落としたファイルの記録（年度・大会・元URL・取得時刻）
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw/archive"
OUT = ROOT / "pdfs/archive"
CDX = "http://web.archive.org/cdx/search/cdx?url=tokyosoccer-u18.com&matchType=domain&filter=mimetype:application/pdf&filter=statuscode:200&collapse=urlkey&fl=timestamp,original"
UA = {"User-Agent": "Mozilla/5.0 (compatible; tokyo-soccer-brackets/1.0)"}
WAIT = 2.0


def get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def cdx_rows(refresh: bool) -> list[tuple[str, str]]:
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / "cdx_pdfs.txt"
    if refresh or not p.exists():
        p.write_bytes(get(CDX, timeout=300))
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    return rows


def classify(url: str) -> tuple[str, int] | None:
    """URL から大会と年度を読む。読めないものは対象外とする。"""
    m = re.search(r"/(SOTAI|SEN|SINJ)(\d{2})/", url, re.I)
    if m:
        comp = m.group(1).upper()
        yy = int(m.group(2))
        return comp, 2000 + yy
    # 関東大会はディレクトリが年ごとにばらばら（2023KANTO/ など）
    m = re.search(r"/(\d{4})KANTO/", url, re.I)
    if m:
        return "KANTO", int(m.group(1))
    m = re.search(r"/kanto(\d{4})[._]", url, re.I) or re.search(r"/(\d{4})kanto", url, re.I)
    if m:
        return "KANTO", int(m.group(1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-year", type=int, default=2021, help="この年度まで落とす（既存ぶんを避けるため既定は2021）")
    ap.add_argument("--min-year", type=int, default=2003)
    ap.add_argument("--list", action="store_true", help="落とさずに一覧だけ出す")
    ap.add_argument("--refresh", action="store_true", help="アーカイブの一覧を取り直す")
    args = ap.parse_args()

    rows = cdx_rows(args.refresh)
    targets = []
    for ts, url in rows:
        c = classify(url)
        if not c:
            continue
        comp, year = c
        if not (args.min_year <= year <= args.max_year):
            continue
        name = f"{comp}{str(year)[2:]}_{url.rsplit('/', 1)[-1]}"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        targets.append({"year": year, "comp": comp, "ts": ts, "url": url, "name": name})
    targets.sort(key=lambda t: (t["year"], t["comp"], t["name"]))

    print(f"対象 {len(targets)} 本（{args.min_year}〜{args.max_year}年度）")
    by = {}
    for t in targets:
        by.setdefault((t["year"], t["comp"]), []).append(t)
    for (year, comp), items in sorted(by.items()):
        print(f"  {year} {comp:6} {len(items):2}本  " + " ".join(i["url"].rsplit("/", 1)[-1] for i in items[:6]))
    if args.list:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    man = RAW / "manifest.csv"
    done = set()
    if man.exists():
        with man.open(encoding="utf-8") as f:
            done = {r["name"] for r in csv.DictReader(f)}
    new = man.exists()
    with man.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "year", "comp", "ts", "url", "bytes", "at"])
        if not new:
            w.writeheader()
        got = skip = fail = 0
        for i, t in enumerate(targets, 1):
            dest = OUT / t["name"]
            if dest.exists() and dest.stat().st_size > 0 and t["name"] in done:
                skip += 1
                continue
            wb = f"https://web.archive.org/web/{t['ts']}id_/{t['url']}"
            try:
                data = get(wb)
                if not data.startswith(b"%PDF"):
                    raise ValueError("PDFではない中身が返った")
                dest.write_bytes(data)
                w.writerow({**{k: t[k] for k in ("name", "year", "comp", "ts", "url")},
                            "bytes": len(data), "at": time.strftime("%Y-%m-%d %H:%M:%S")})
                f.flush()
                got += 1
                print(f"[{i}/{len(targets)}] {t['name']}  {len(data) // 1024}KB")
            except Exception as e:  # noqa: BLE001 - 取れないものは飛ばして続ける
                fail += 1
                print(f"[{i}/{len(targets)}] 失敗 {t['name']}: {e}")
            time.sleep(WAIT)
    print(f"完了: 取得 {got} / 既にある {skip} / 取れず {fail} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
