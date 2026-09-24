"""東京 T リーグの過去（2014〜2020年度）を高校サッカードットコムから読む。

公式（tleague-u18.com）は今季と前季しか残っていない。高校サッカードットコムには
2014〜2020年度の「東京 T リーグ」が、順位表と全試合（スコア入り）で残っている。

  uv run python collect_koko_tleague.py            # 取得して CSV を書く
  uv run python collect_koko_tleague.py --refresh  # ページを取り直す

出典: https://koko-soccer.com/score/<id> （個人で見るためだけに使う）
出力: data/leagues/tleague_history_standings.csv・tleague_history_matches.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize

ROOT = Path(__file__).parent
RAW = ROOT / "raw/web/koko"
OUT = ROOT / "data/leagues"
UA = {"User-Agent": "Mozilla/5.0 (compatible; tokyo-soccer-brackets/1.0)"}
WAIT = 2.0
# 年度 → 高校サッカードットコムの大会ID（東京 T リーグ）
SEASONS = {2014: 94, 2015: 92, 2016: 321, 2017: 657, 2018: 1032, 2019: 1454, 2020: 1919}


def fetch(url: str, dest: Path, refresh: bool) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not dest.exists():
        req = urllib.request.Request(url, headers=UA)
        dest.write_bytes(urllib.request.urlopen(req, timeout=40).read())
        time.sleep(WAIT)
    return dest.read_text(encoding="utf-8", errors="replace")


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def parse_division(html: str, year: int, url: str) -> tuple[list[dict], list[dict]]:
    """1つの部（T1・T3A など）のページから、順位表と試合を読む。"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    m = re.search(r"(T\d[ＡＢABab]?)\s*リーグ", title.replace("　", " "))
    div = (m[1].upper().translate(str.maketrans("ＡＢ", "AB")) if m else title.split("｜")[0].strip())

    standings, matches = [], []
    for t in soup.find_all("table"):
        rs = rows_of(t)
        if not rs:
            continue
        head = rs[0]
        if head[:2] == ["順位", "チーム名"]:
            for r in rs[1:]:
                if len(r) < 9 or not r[0].isdigit():
                    continue
                standings.append({
                    "年度": year, "リーグ": div, "順位": int(r[0]), "チーム": r[1], "学校": normalize(r[1]),
                    "勝点": r[2], "試合": r[3], "勝": r[4], "敗": r[5], "分": r[6], "得点": r[7], "失点": r[8],
                    "出典": url,
                })
        elif head[:2] == ["日程", "対戦カード"]:
            for r in rs[1:]:
                if len(r) < 4:
                    continue
                date, home, score, away = r[0], r[1], r[2], r[3]
                sm = re.search(r"(\d+)\s*-\s*(\d+)", score)
                matches.append({
                    "年度": year, "リーグ": div, "日時": date,
                    "ホーム": home, "学校H": normalize(home), "アウェイ": away, "学校A": normalize(away),
                    "得点H": sm[1] if sm else "", "得点A": sm[2] if sm else "",
                    "状態": "終了" if sm else score, "出典": url,
                })
    return standings, matches


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    standings, matches = [], []
    for year, sid in sorted(SEASONS.items()):
        top = fetch(f"https://koko-soccer.com/score/{sid}", RAW / f"tleague_{year}.html", args.refresh)
        soup = BeautifulSoup(top, "html.parser")
        subs = []
        for a in soup.find_all("a", href=True):
            if re.fullmatch(r"/score/\d+", a["href"]) and a["href"] != f"/score/{sid}":
                subs.append(a["href"].rsplit("/", 1)[-1])
        subs = list(dict.fromkeys(subs))
        got_s = got_m = 0
        for sub in subs:
            url = f"https://koko-soccer.com/score/{sub}"
            html = fetch(url, RAW / f"tleague_{year}_{sub}.html", args.refresh)
            s, m = parse_division(html, year, url)
            standings += s
            matches += m
            got_s += len(s)
            got_m += len(m)
        print(f"{year}年度  部 {len(subs)}  順位表 {got_s} 行  試合 {got_m} 件")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("tleague_history_standings.csv", standings), ("tleague_history_matches.csv", matches)):
        if not rows:
            continue
        p = OUT / name
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"→ {p}  {len(rows)} 行")
    done = sum(1 for m in matches if m["得点H"])
    print(f"合計: 順位表 {len(standings)} 行 / 試合 {len(matches)} 件（うちスコアあり {done}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
