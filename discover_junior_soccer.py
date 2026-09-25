"""junior-soccer.jp にある東京のリーグ戦の一覧を作り、どの地区のどの部かを調べる。

地区リーグは年度ごとに番号（tid）が振られている。番号を総当たりする必要は無く、
/sp/kanto/tokyo/league?page=N に全リーグの索引があるので、そこを歩いて名前と番号を集める
（128ページ・1ページ約34件）。番号の近くを順に開く --range も残してあるが、索引のほうが速くて確実。

収集の実行はこのスクリプトが行い、見つかった番号は data/leagues/junior_soccer_tids.csv に
書き出す。地区の部品（districts/dN.py）へ取り込むかどうかは、それを見てから決める。

礼儀として1件ごとに間を空け、範囲を区切って動かす。保存済みのページは取りに行かない。

  uv run python discover_junior_soccer.py --index            # 索引を全ページ歩く
  uv run python discover_junior_soccer.py --index --pages 20  # 先頭20ページだけ
  uv run python discover_junior_soccer.py --range 47940-47990 # 番号の近くを見る
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
RAW = ROOT / "raw/web/junior-soccer"
OUT = ROOT / "data/leagues/junior_soccer_tids.csv"
UA = {"User-Agent": "Mozilla/5.0 (compatible; tokyo-soccer-brackets/1.0)"}
WAIT = 1.5
# 「【3部A】2024年度 第3地区リーグユースリーグ」のような見出しを拾う
HEAD = re.compile(r"【([^】]+)】\s*(\d{4})年度\s*(.+)")


def fetch(url: str, dest: Path, refresh: bool) -> str | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not dest.exists():
        try:
            dest.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                dest.write_bytes(b"")  # 無い番号も記録して、二度と取りに行かない
                time.sleep(WAIT)
                return None
            raise
        time.sleep(WAIT)
    b = dest.read_bytes()
    return b.decode("utf-8", "replace") if b else None


def league_of(html: str) -> tuple[str, str, str] | None:
    """ページの見出しから（部, 年度, リーグ名）を取り出す。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        m = HEAD.match(tag.get_text(" ", strip=True))
        if m:
            return m[1].strip(), m[2], re.sub(r"\s+", " ", m[3]).strip()
    return None


INDEX = "https://junior-soccer.jp/sp/kanto/tokyo/league?page={}"


def walk_index(pages: int, refresh: bool) -> list[dict]:
    """索引を歩いて（番号, 表示名）を集める。名前は「【部】年度 リーグ名」の形。"""
    found: dict[str, str] = {}
    for n in range(1, pages + 1):
        html = fetch(INDEX.format(n), RAW / f"index_{n:03d}.html", refresh)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            m = re.search(r"/league/(?:match|table|order)/(\d+)", a["href"])
            if not m:
                continue
            text = a.get_text(" ", strip=True)
            if not text:
                par = a.find_parent(["li", "div", "td"])
                text = par.get_text(" ", strip=True) if par else ""
            if text:
                found.setdefault(m[1], re.sub(r"\s+", " ", text))
        print(f"  {n:3}ページ目まで … 累計 {len(found)} 件")
    out = []
    for tid, text in found.items():
        m = HEAD.match(text)
        bu, year, name = (m[1].strip(), m[2], m[3].strip()) if m else ("", "", text)
        out.append({"tid": tid, "種類": "index", "年度": year, "リーグ名": name, "部": bu,
                    "URL": f"https://junior-soccer.jp/kanto/tokyo/league/table/{tid}"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--range", default="", help="47940-47990 の形")
    ap.add_argument("--index", action="store_true", help="索引を歩く（番号の総当たりより速い）")
    ap.add_argument("--pages", type=int, default=128, help="索引の何ページ目まで見るか")
    ap.add_argument("--kind", choices=["match", "table", "order"], default="match")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if not args.range and not args.index:
        ap.error("--index か --range のどちらかを指定してください")
    lo, hi = (int(x) for x in args.range.split("-")) if args.range else (0, 0)

    rows = []
    if OUT.exists():
        with OUT.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    seen = {(r["tid"], r["種類"]) for r in rows}

    hit = miss = 0
    if args.index:
        got = walk_index(args.pages, args.refresh)
        known = {r["tid"] for r in rows}
        new = [g for g in got if g["tid"] not in known]
        rows += new
        hit = len(new)
        by = {}
        for g in got:
            key = (g["年度"], g["リーグ名"])
            by[key] = by.get(key, 0) + 1
        print(f"索引から {len(got)} 件（新規 {hit}）")
        for (y, n), c in sorted(by.items()):
            if any(k in n for k in ("地区", "U-18", "Ｕ-18", "リバーサイド", "ユースリーグ")):
                print(f"  {y}年度  {n[:44]:46} {c}ブロック")
        lo = hi = 0
    for tid in ([] if args.index else range(lo, hi + 1)):
        if (str(tid), args.kind) in seen:
            continue
        url = f"https://junior-soccer.jp/sp/kanto/tokyo/league/{args.kind}/{tid}"
        html = fetch(url, RAW / f"{args.kind}_{tid}.html", args.refresh)
        info = league_of(html) if html else None
        if not info:
            miss += 1
            continue
        bu, year, name = info
        hit += 1
        rows.append({"tid": str(tid), "種類": args.kind, "年度": year, "リーグ名": name, "部": bu, "URL": url})
        print(f"  {tid}  {year}年度  {name}  【{bu}】")

    rows.sort(key=lambda r: (r["リーグ名"], r["年度"], r["部"], r["tid"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tid", "種類", "年度", "リーグ名", "部", "URL"])
        w.writeheader()
        w.writerows(rows)
    where = "索引" if args.index else f"{lo}〜{hi}（{args.kind}）"
    print(f"{where}: 見つかった {hit} / 無し {miss} → 累計 {len(rows)} 件  {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
