"""第2地区（DUOリーグ・goalnote）の順位表と試合を集める。

部品の決まりは notes/district_collector_spec.md。ページの読み方は fetch_leagues.py の goalnote() を写して使う
（fetch_leagues.py 自体は変更しない）。DUOリーグは「N部」の見出しが無く、グループA〜Eの総当りのみ
（校名末尾のA/B/C等は同一校の複数チームを示す。data/leagues/sources.csv 確認済み）。

取得したページは raw/web/district/d2/ に保存する。refresh=False なら保存済みのページだけで動く。
"""

from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw/web/district/d2"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
BASE = "https://www.goalnote.net"

地区 = "第2地区"
リーグ = "DUOリーグ"
# 年度 → tid（data/leagues/sources.csv で確認済み）
YEAR_TID = {2024: 15652, 2025: 16985, 2026: 18409}

STAT_KEYS = {"勝点": "pts", "試合数": "gp", "勝利": "w", "引分": "d", "敗戦": "l", "得点": "gf", "失点": "ga", "得失差": "gd", "得失点": "gd"}


def fetch(url: str, path: Path, refresh: bool) -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    if refresh or not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes().decode("utf-8", "replace")


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def parse_year(year: int, tid: int, refresh: bool) -> tuple[list[dict], list[dict]]:
    sched_url = f"{BASE}/detail-schedule.php?tid={tid}"
    stand_url = f"{BASE}/detail-standings.php?tid={tid}"
    sched = BeautifulSoup(fetch(sched_url, RAW / f"goalnote_{tid}_detail-schedule.html", refresh), "html.parser")
    stand = BeautifulSoup(fetch(stand_url, RAW / f"goalnote_{tid}_detail-standings.html", refresh), "html.parser")

    division: dict[str, str] = {}  # グループ文字 → 部ラベル（DUOでは常に空。将来の混在に備えて残す）
    matches: list[dict] = []
    cur_div = ""
    cur_round = ""
    for tb in sched.find_all("table"):
        for r in rows_of(tb):
            if len(r) == 1:
                header = r[0]
                m_round = re.search(r"第\d+節", header)
                if m_round:
                    cur_round = m_round.group(0)
                first = header.split()[0] if header.split() else ""
                if re.search(r"\d部", first):
                    cur_div = first
                continue
            if len(r) >= 7 and re.fullmatch(r"\d{4}/\d{2}/\d{2}", r[1]):
                grp, date, tm, home, score, away, venue = r[:7]
                division.setdefault(grp, cur_div)
                bu = cur_div or f"グループ{grp}"
                m = re.match(r"(\d+)-(\d+)", score)
                hg, ag = (int(m[1]), int(m[2])) if m else (None, None)
                placeholder = date.endswith("/04/01") and tm == "10:00" and not venue
                hb, hs = squad_of(home)
                ab, as_ = squad_of(away)
                matches.append({
                    "地区": 地区, "リーグ": リーグ, "年度": year, "部": bu,
                    "節": cur_round, "日付": "" if placeholder else date.replace("/", "-"),
                    "ホーム": home, "アウェイ": away,
                    "ホーム得点": hg if hg is not None else "", "アウェイ得点": ag if ag is not None else "",
                    "実施": "済" if hg is not None else "未",
                    "ホーム学校": normalize(hb), "ホーム区分": hs, "アウェイ学校": normalize(ab), "アウェイ区分": as_,
                    "出典": sched_url,
                })

    standings: list[dict] = []
    for tb in stand.find_all("table"):
        rs = rows_of(tb)
        if not rs or not rs[0][0].startswith("グループ"):
            continue
        grp = rs[0][0].replace("グループ", "")
        header = rs[0][1:]
        bu = division.get(grp) or f"グループ{grp}"
        for row in rs[1:]:
            if len(row) < 2:
                continue
            順位, チーム = row[0], row[1]
            stats = dict(zip(header, row[2:]))
            vals = {}
            for jp, key in STAT_KEYS.items():
                if jp in stats and key not in vals:
                    raw_v = stats[jp].replace("+", "")
                    vals[key] = int(raw_v) if re.fullmatch(r"-?\d+", raw_v or "") else ""
            base, sq = squad_of(チーム)
            standings.append({
                "地区": 地区, "リーグ": リーグ, "年度": year, "部": bu,
                "順位": int(順位) if 順位.isdigit() else "", "チーム": チーム, "学校": normalize(base), "区分": sq,
                "勝点": vals.get("pts", ""), "試合": vals.get("gp", ""), "勝": vals.get("w", ""), "分": vals.get("d", ""),
                "敗": vals.get("l", ""), "得点": vals.get("gf", ""), "失点": vals.get("ga", ""), "得失点": vals.get("gd", ""),
                "出典": stand_url,
            })
    return standings, matches


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    standings: list[dict] = []
    matches: list[dict] = []
    for year, tid in YEAR_TID.items():
        s, m = parse_year(year, tid, refresh)
        standings += s
        matches += m
    return standings, matches


if __name__ == "__main__":
    import json
    s, m = collect()
    print(f"順位表 {len(s)} 行・試合 {len(m)} 件")
    print(json.dumps(s[:3], ensure_ascii=False, indent=1))
