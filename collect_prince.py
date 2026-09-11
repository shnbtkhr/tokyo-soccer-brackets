"""プリンスリーグ関東1部（2026）の順位表と全試合を読む。東京の高校で T リーグより上にいるのは帝京だけ（2026年度）。

出典は高校サッカードットコム（koko-soccer.com/score/4347）。個人で見るためだけに使う（公開するときは外す）。
取得したページは raw/web/prince/ に保存し、--refresh のときだけ取り直す。
出力: data/leagues/prince_kanto1_2026_standings.csv・prince_kanto1_2026_matches.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize

ROOT = Path(__file__).parent
URL = "https://koko-soccer.com/score/4347"
RAW = ROOT / "raw/web/prince/koko_4347.html"
OUT = ROOT / "data/leagues"
LEAGUE = "プリンス関東1部"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if args.refresh or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    soup = BeautifulSoup(RAW.read_text(encoding="utf-8"), "html.parser")
    standings, matches = [], []
    for t in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in t.find_all("tr")]
        if rows and rows[0][:2] == ["順位", "チーム名"]:
            for r in rows[1:]:
                standings.append({"年度": 2026, "リーグ": LEAGUE, "順位": int(r[0]), "チーム": r[1], "学校": normalize(r[1]), "勝点": int(r[2]), "試合": int(r[3]),
                                  "勝": int(r[4]), "敗": int(r[5]), "分": int(r[6]), "得点": int(r[7]), "失点": int(r[8]), "得失点": int(r[9]), "出典": URL})
        elif rows and rows[0][:2] == ["日程", "対戦カード"]:
            for r in rows[1:]:
                if len(r) < 4:
                    continue
                m = re.match(r"(\d+)\s*-\s*(\d+)", r[2])
                home, away = re.sub(r"\s*（.*?）$", "", r[1]), re.sub(r"\s*（.*?）$", "", r[3])
                d = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", r[0])
                matches.append({"年度": 2026, "リーグ": LEAGUE, "日付": f"{d[1]}-{d[2]}-{d[3]}" if d else "", "ホーム": home, "アウェイ": away,
                                "ホーム得点": int(m[1]) if m else "", "アウェイ得点": int(m[2]) if m else "", "実施": "済" if m else "未",
                                "ホーム学校": normalize(home), "アウェイ学校": normalize(away), "出典": URL})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("standings", standings), ("matches", matches)):
        with (OUT / f"prince_kanto1_2026_{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"順位表 {len(standings)} チーム・試合 {len(matches)}（実施済み {sum(m['実施'] == '済' for m in matches)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
