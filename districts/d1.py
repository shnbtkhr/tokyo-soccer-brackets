"""第1地区（リバーサイドユースリーグ）の順位表・試合を集める。

- 2024年度: junior-soccer.jp（非公式集計サイト）。order/{tid} が順位表（<table>2本、順位+チーム名／勝点等が別テーブルで
  行がそろっている）、match/{tid} が試合結果（<table>を使わず div.match_box の並び）。tid は
  data/leagues/sources.csv で確認済みのもの（1部=49170, 2部A=49171, 2部B=49172）。
- 2026年度: リバーサイド公式サイト（現行ページ・年度の明記なし。2026-09時点で「2026年度リーグ情報」と
  トップページに明記されているため2026年度として扱う）。1部・2部A・2部Bとも「順位表」ページが無い
  （1部の standing_division1.html は対戦成績のクロス表のみで順位・勝点が無い、2部A/Bはそもそも順位表URL
  自体が見つかっていない）ため、試合結果ページ（schedule_division*.html）から順位表を計算する
  （出典欄に「（試合から計算）」と付記）。エンコードは cp932（fetch_leagues.py の riverside() と同じ）。
- 2025年度: 公式サイトに過去ページのアーカイブが無く、junior-soccer.jp にも tid が見つからなかった
  （sources.csv に未発見と明記）。取得しない。

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
RAW = ROOT / "raw/web/district/d1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
地区 = "第1地区"
リーグ = "リバーサイドユースリーグ"

SCORE_RE = re.compile(r"^(\d+)-(\d+)$")

# 2024年度（junior-soccer.jp）。tid・部・保存済みファイル名は data/leagues/sources.csv と現物確認済み。
# 順位表ページ(junior_soccer_*.html)は前担当が保存した際の命名が部ごとに揺れているため、tidごとに明示する。
JS_2024 = {
    "1部": {"tid": 49170, "order_file": "junior_soccer_49170.html", "match_file": "junior_soccer_match_49170.html"},
    "2部A": {"tid": 49171, "order_file": "junior_soccer_49171.html", "match_file": "junior_soccer_match_49171.html"},
    "2部B": {"tid": 49172, "order_file": "junior_soccer_order_49172.html", "match_file": "junior_soccer_match_49172.html"},
}

# 2026年度（公式サイト・現行ページ。年度の明記なし）
RIVERSIDE_2026 = {
    "1部": {"url": "https://riverside-league.com/schedule_division1.html", "file": "riverside_schedule_division1.html"},
    "2部A": {"url": "https://riverside-league.com/schedule_division2_group_a.html", "file": "riverside_schedule_division2_group_a.html"},
    "2部B": {"url": "https://www.riverside-league.com/schedule_division2_group_b.html", "file": "riverside_schedule_division2_group_b.html"},
}


def fetch(url: str, path: Path, refresh: bool) -> bytes:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes()


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


# ---- 2024年度 junior-soccer.jp ----

def parse_js_order(html: bytes) -> list[dict]:
    s = BeautifulSoup(html.decode("utf-8", "replace"), "html.parser")
    tables = s.find_all("table")
    left = rows_of(tables[0])[1:]   # 順位, チーム名
    right = rows_of(tables[1])[1:]  # 勝点,試合数,勝数,引分数,敗数,得点,失点,得失点差
    out = []
    for (rank, team), (pts, gp, w, d, l, gf, ga, gd) in zip(left, right):
        out.append({"rank": int(rank), "team": team, "pts": int(pts), "gp": int(gp),
                     "w": int(w), "d": int(d), "l": int(l), "gf": int(gf), "ga": int(ga), "gd": int(gd)})
    return out


def parse_js_matches(html: bytes, year: int) -> list[dict]:
    s = BeautifulSoup(html.decode("utf-8", "replace"), "html.parser")
    games = []
    for box in s.find_all("div", class_="match_box"):
        home = box.find("div", class_="lbox").get_text(strip=True)
        away = box.find("div", class_="rbox").get_text(strip=True)
        score = box.find("div", class_="cbox").get_text(strip=True).replace(" ", "")
        m = SCORE_RE.match(score)
        tbl = box.find_next_sibling("table")
        ko = tbl.find_all("tr")[0].find_all(["th", "td"])[1].get_text(" ", strip=True) if tbl else "-"
        dm = re.search(r"(\d{1,2})/(\d{1,2})", ko)
        date = f"{year if int(dm[1]) >= 4 else year + 1}-{int(dm[1]):02d}-{int(dm[2]):02d}" if dm else ""
        games.append({"home": home, "away": away, "date": date,
                      "hg": int(m[1]) if m else None, "ag": int(m[2]) if m else None})
    return games


def collect_js_2024(refresh: bool) -> tuple[list[dict], list[dict]]:
    standings, matches = [], []
    for part, cfg in JS_2024.items():
        tid = cfg["tid"]
        order_url = f"https://junior-soccer.jp/sp/kanto/tokyo/league/order/{tid}"
        match_url = f"https://junior-soccer.jp/sp/kanto/tokyo/league/match/{tid}"
        order_html = fetch(order_url, RAW / cfg["order_file"], refresh)
        match_html = fetch(match_url, RAW / cfg["match_file"], refresh)

        for row in parse_js_order(order_html):
            base, sq = squad_of(row["team"])
            standings.append({
                "地区": 地区, "リーグ": リーグ, "年度": 2024, "部": part,
                "順位": row["rank"], "チーム": row["team"], "学校": normalize(base), "区分": sq,
                "勝点": row["pts"], "試合": row["gp"], "勝": row["w"], "分": row["d"], "敗": row["l"],
                "得点": row["gf"], "失点": row["ga"], "得失点": row["gd"],
                "出典": order_url,
            })

        for g in parse_js_matches(match_html, 2024):
            hb, hsq = squad_of(g["home"])
            ab, asq = squad_of(g["away"])
            matches.append({
                "地区": 地区, "リーグ": リーグ, "年度": 2024, "部": part,
                "節": "", "日付": g["date"],
                "ホーム": g["home"], "アウェイ": g["away"],
                "ホーム得点": g["hg"], "アウェイ得点": g["ag"], "実施": "済" if g["hg"] is not None else "未",
                "ホーム学校": normalize(hb), "ホーム区分": hsq,
                "アウェイ学校": normalize(ab), "アウェイ区分": asq,
                "出典": match_url,
            })
    return standings, matches


# ---- 2026年度 リバーサイド公式サイト（現行ページ） ----

def parse_riverside_games(html: bytes) -> list[dict]:
    s = BeautifulSoup(html.decode("cp932", "replace"), "html.parser")
    table = s.find_all("table")[2]
    games = []
    round_label = ""
    for r in rows_of(table):
        if r and r[0].startswith("第"):
            round_label = r[0]
            r = r[1:]
        if len(r) >= 5 and re.search(r"\d+月\d+日", r[0]):
            when, home, score, away, _venue = r[:5]
            m = SCORE_RE.match(score.replace(" ", "").replace("　", ""))
            games.append({"round": round_label, "when": when, "home": home, "away": away,
                          "hg": int(m[1]) if m else None, "ag": int(m[2]) if m else None})
    return games


def to_date(year: int, when: str) -> str:
    m = re.search(r"(\d{1,2})月(\d{1,2})日", when)
    if not m:
        return ""
    mo, da = int(m[1]), int(m[2])
    return f"{year if mo >= 4 else year + 1}-{mo:02d}-{da:02d}"


def standings_from_games(games: list[dict]) -> list[dict]:
    stats: dict[str, dict] = {}
    for g in games:
        if g["hg"] is None:
            continue
        for team, gf, ga in ((g["home"], g["hg"], g["ag"]), (g["away"], g["ag"], g["hg"])):
            st = stats.setdefault(team, {"gp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0})
            st["gp"] += 1
            st["gf"] += gf
            st["ga"] += ga
            st["w" if gf > ga else "l" if gf < ga else "d"] += 1
    rows = []
    for team, st in stats.items():
        pts = 3 * st["w"] + st["d"]
        gd = st["gf"] - st["ga"]
        rows.append({"team": team, "pts": pts, "gd": gd, **st})
    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def collect_riverside_2026(refresh: bool) -> tuple[list[dict], list[dict]]:
    standings, matches = [], []
    for part, cfg in RIVERSIDE_2026.items():
        html = fetch(cfg["url"], RAW / cfg["file"], refresh)
        games = parse_riverside_games(html)
        played = [g for g in games if g["hg"] is not None]
        source = f"{cfg['url']}（試合から計算）"

        for row in standings_from_games(played):
            base, sq = squad_of(row["team"])
            standings.append({
                "地区": 地区, "リーグ": リーグ, "年度": 2026, "部": part,
                "順位": row["rank"], "チーム": row["team"], "学校": normalize(base), "区分": sq,
                "勝点": row["pts"], "試合": row["gp"], "勝": row["w"], "分": row["d"], "敗": row["l"],
                "得点": row["gf"], "失点": row["ga"], "得失点": row["gd"],
                "出典": source,
            })

        for g in games:
            hb, hsq = squad_of(g["home"])
            ab, asq = squad_of(g["away"])
            played_flag = g["hg"] is not None
            matches.append({
                "地区": 地区, "リーグ": リーグ, "年度": 2026, "部": part,
                "節": g["round"], "日付": to_date(2026, g["when"]) if played_flag else "",
                "ホーム": g["home"], "アウェイ": g["away"],
                "ホーム得点": g["hg"] if played_flag else "", "アウェイ得点": g["ag"] if played_flag else "",
                "実施": "済" if played_flag else "未",
                "ホーム学校": normalize(hb), "ホーム区分": hsq,
                "アウェイ学校": normalize(ab), "アウェイ区分": asq,
                "出典": cfg["url"],
            })
    return standings, matches


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    s1, m1 = collect_js_2024(refresh)
    s2, m2 = collect_riverside_2026(refresh)
    return s1 + s2, m1 + m2


if __name__ == "__main__":
    s, m = collect()
    print(f"順位表 {len(s)} 行・試合 {len(m)} 件")
