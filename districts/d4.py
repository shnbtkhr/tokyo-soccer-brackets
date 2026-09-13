"""第4地区（4地区ユースリーグ・kawakitanet.com）の順位表・試合を集める。

- 順位表: main.php（順位・チーム・試合・勝点・勝・分・敗・得失点差のみ。得点/失点は載っていない）
- 試合結果: select.php（表ではなく文章。日付・ホーム・スコア・アウェイが並ぶ）
  得点・失点はここから集計して埋める（得点-失点が main.php の得失点差と一致することを確かめ済み）。

年度・部→gameid の対応は data/leagues/sources.csv で確認済みのもの（推測で番号を変えない）。
仕様は notes/district_collector_spec.md。
"""

from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw/web/district/d4"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
BASE = "https://www.kawakitanet.com/league_soccer"
地区 = "第4地区"
リーグ = "4地区ユースリーグ"

# 年度 → 部 → gameid（data/leagues/sources.csv の第4地区の行と一致）
GAMEIDS: dict[int, dict[str, int]] = {
    2024: {"1部": 9154, "2部": 9155, "3部A": 9156, "3部B": 9157},
    2025: {"1部": 9466, "2部": 9467, "3部A": 9468, "3部B": 9469},
    2026: {"1部": 9761, "2部": 9762, "3部A": 9763, "3部B": 9764},
}

DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
SCORE_RE = re.compile(r"^(\d+)-(\d+)$")


def fetch(url: str, path: Path, refresh: bool) -> str:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes().decode("utf-8", "replace")


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def parse_games(select_html: str) -> list[dict]:
    """select.php は<table>を使わない文章形式。日付,ホーム,スコア,アウェイ,更,削 の6個ひと組が繰り返される。"""
    strs = list(BeautifulSoup(select_html, "html.parser").stripped_strings)
    games = []
    i = 0
    while i < len(strs):
        m = DATE_RE.match(strs[i])
        if m and i + 3 < len(strs) and SCORE_RE.match(strs[i + 2]):
            sm = SCORE_RE.match(strs[i + 2])
            games.append({
                "date": f"{m[1]}-{m[2]}-{m[3]}",
                "home": strs[i + 1], "away": strs[i + 3],
                "hg": int(sm[1]), "ag": int(sm[2]),
            })
            i += 6  # 日付, ホーム, スコア, アウェイ, 更, 削
        else:
            i += 1
    return games


def goal_tally(games: list[dict]) -> tuple[dict, dict]:
    gf, ga = {}, {}
    for g in games:
        gf[g["home"]] = gf.get(g["home"], 0) + g["hg"]
        ga[g["home"]] = ga.get(g["home"], 0) + g["ag"]
        gf[g["away"]] = gf.get(g["away"], 0) + g["ag"]
        ga[g["away"]] = ga.get(g["away"], 0) + g["hg"]
    return gf, ga


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    standings: list[dict] = []
    matches: list[dict] = []
    for year, parts in GAMEIDS.items():
        for part, gid in parts.items():
            main_url = f"{BASE}/main.php?pref_cd=8&gameid={gid}"
            select_url = f"{BASE}/select.php?pref_cd=8&gameid={gid}"
            main_html = fetch(main_url, RAW / f"kawakita_{gid}_main.html", refresh)
            select_html = fetch(select_url, RAW / f"kawakita_{gid}_select.html", refresh)

            games = parse_games(select_html)
            gf, ga = goal_tally(games)

            table = BeautifulSoup(main_html, "html.parser").find("table")
            for r in rows_of(table)[1:]:
                if len(r) != 8:
                    continue
                rank, team, gp, pts, w, d, l, gd = r
                base, sq = squad_of(team)
                standings.append({
                    "地区": 地区, "リーグ": リーグ, "年度": year, "部": part,
                    "順位": int(rank), "チーム": team, "学校": normalize(base), "区分": sq,
                    "勝点": int(pts), "試合": int(gp), "勝": int(w), "分": int(d), "敗": int(l),
                    "得点": gf.get(team, ""), "失点": ga.get(team, ""), "得失点": int(gd),
                    "出典": main_url,
                })

            for g in games:
                hb, hsq = squad_of(g["home"])
                ab, asq = squad_of(g["away"])
                matches.append({
                    "地区": 地区, "リーグ": リーグ, "年度": year, "部": part,
                    "節": "", "日付": g["date"],
                    "ホーム": g["home"], "アウェイ": g["away"],
                    "ホーム得点": g["hg"], "アウェイ得点": g["ag"], "実施": "済",
                    "ホーム学校": normalize(hb), "ホーム区分": hsq,
                    "アウェイ学校": normalize(ab), "アウェイ区分": asq,
                    "出典": select_url,
                })
    return standings, matches


if __name__ == "__main__":
    s, m = collect()
    print(f"順位表 {len(s)} 行・試合 {len(m)} 件")
