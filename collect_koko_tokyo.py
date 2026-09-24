"""東京都予選（選手権・総体・新人戦・関東）の試合結果を高校サッカードットコムから読む。

PDF のトーナメント表は、結果が入る前の版しか残っていない年がある（2008〜2016年度は
スコアが半分以上欠けている）。高校サッカードットコムには同じ大会の日付つきの結果が
残っているので、突き合わせて埋めるための材料にする。

  uv run python collect_koko_tokyo.py --list     # どの大会が取れるか見る
  uv run python collect_koko_tokyo.py            # 取得して CSV を書く

出典: https://koko-soccer.com/score/<id>（個人で見るためだけに使う）
出力: data/koko_tokyo_matches.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize

ROOT = Path(__file__).parent
RAW = ROOT / "raw/web/koko"
OUT = ROOT / "data/koko_tokyo_matches.csv"
UA = {"User-Agent": "Mozilla/5.0 (compatible; tokyo-soccer-brackets/1.0)"}
WAIT = 2.0
SERIES = [("選手権", r"全国高校サッカー選手権"), ("総体", r"インターハイ|総体"),
          ("新人戦", r"新人戦"), ("関東", r"関東高校サッカー")]


def fetch(url: str, dest: Path, refresh: bool = False) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not dest.exists():
        req = urllib.request.Request(url, headers=UA)
        dest.write_bytes(urllib.request.urlopen(req, timeout=40).read())
        time.sleep(WAIT)
    return dest.read_text(encoding="utf-8", errors="replace")


def sub_links(html: str) -> list[tuple[str, str]]:
    """そのページから辿れる下位ページ（ID, 見出し）。"""
    s = BeautifulSoup(html, "html.parser")
    out = []
    for a in s.find_all("a", href=True):
        if not re.fullmatch(r"/score/\d+", a["href"]):
            continue
        par = a.find_parent(["li", "div", "td", "tr"])
        label = re.sub(r"\s+", " ", par.get_text(" ", strip=True)) if par else ""
        out.append((a["href"].rsplit("/", 1)[-1], label))
    return out


def matches_of(html: str, year: int, series: str, stage: str, url: str) -> list[dict]:
    s = BeautifulSoup(html, "html.parser")
    out = []
    for t in s.find_all("table"):
        for tr in t.find_all("tr"):
            cs = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cs) < 4 or "試合終了" not in cs[2]:
                continue
            m = re.search(r"(\d+)\s*-\s*(\d+)(?:\s*PK\s*(\d+)\s*-\s*(\d+))?", cs[2])
            if not m:
                continue
            d = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", cs[0])
            out.append({
                "年度": year, "大会": series, "段階": stage,
                "日付": f"{d[1]}-{int(d[2]):02d}-{int(d[3]):02d}" if d else "",
                "チームA": cs[1], "学校A": normalize(cs[1]),
                "チームB": cs[3], "学校B": normalize(cs[3]),
                "得点A": m[1], "得点B": m[2], "PK_A": m[3] or "", "PK_B": m[4] or "",
                "出典": url,
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--max-year", type=int, default=2021, help="この年度まで（既存PDFで足りている年は既定で除く）")
    args = ap.parse_args()

    index = json.loads((RAW / "tournaments.json").read_text(encoding="utf-8"))
    targets = []
    for it in index:
        if it["year"] > args.max_year:
            continue
        for name, pat in SERIES:
            if re.search(pat, it["name"]):
                targets.append({**it, "series": name})
                break
    targets.sort(key=lambda x: (x["year"], x["series"]))
    print(f"全国大会のページ {len(targets)} 件（〜{args.max_year}年度）")
    if args.list:
        for t in targets:
            print(f"  {t['year']} {t['series']:4} id={t['id']} {t['name'][:44]}")
        return 0

    rows = []
    for t in targets:
        top = fetch(f"https://koko-soccer.com/score/{t['id']}", RAW / f"nat_{t['id']}.html", args.refresh)
        tokyo = [(i, lb) for i, lb in sub_links(top) if "東京" in lb and i != t["id"]]
        if not tokyo:
            continue
        for tid, label in tokyo:
            page = fetch(f"https://koko-soccer.com/score/{tid}", RAW / f"tokyo_{tid}.html", args.refresh)
            # 東京予選のページは、さらに一次・二次などに分かれていることがある
            kids = [(i, lb) for i, lb in sub_links(page) if i != tid and "東京" in lb]
            targets_page = [(tid, label, page)] + [
                (i, lb, fetch(f"https://koko-soccer.com/score/{i}", RAW / f"tokyo_{i}.html", args.refresh))
                for i, lb in kids
            ]
            for pid, plabel, phtml in targets_page:
                stage = re.sub(r".*東京", "", plabel).replace("一覧はこちら", "").strip() or "東京予選"
                got = matches_of(phtml, t["year"], t["series"], stage, f"https://koko-soccer.com/score/{pid}")
                rows += got
                if got:
                    print(f"  {t['year']} {t['series']:4} {stage[:12]:14} {len(got):3} 試合")

    if not rows:
        print("結果が見つかりませんでした")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"合計 {len(rows)} 試合 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
