"""今季（2026年）のリーグ戦の結果を集める。高体連のトーナメント表には無い「今の調子」を見るため。

- T リーグ（高円宮杯 JFA U-18 サッカーリーグ 東京）: https://www.tleague-u18.com/
  schedule.php（節・日時・ホーム・スコア・アウェイ・会場）と rank.php（順位表）
- リバーサイドユースリーグ 1部（東京東部の地域リーグ）: https://riverside-league.com/

取得したページは raw/web/ に保存し、--refresh を付けたときだけ取り直す（アクセスは1.5秒以上あける）。
出力: out/scout/leagues_2026.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize

ROOT = Path(__file__).parent
RAW = ROOT / "raw/web"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# 見たい学校と、その学校が入っているリーグ（ページの番号）
TLEAGUE = {
    ("T5", "Cブロック", 24): ["学習院"],
    ("T5", "Dブロック", 25): ["城東"],
}
RIVERSIDE_TEAMS = {"城東Ｂ": "城東"}


def fetch(url: str, path: Path, refresh: bool) -> bytes:
    if refresh or not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes()


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def tleague(refresh: bool) -> dict:
    out = {}
    for (div, block, no), teams in TLEAGUE.items():
        sched = BeautifulSoup(fetch(f"https://www.tleague-u18.com/schedule.php?dy=2026&dt=5&ltno={no}", RAW / f"tleague_schedule_2026_t5_{no}.html", refresh), "html.parser")
        rank = BeautifulSoup(fetch(f"https://www.tleague-u18.com/rank.php?dy=2026&dt=5&ltno={no}", RAW / f"tleague_rank_2026_t5_{no}.html", refresh), "html.parser")
        games = []
        for r in rows_of(sched.find("table")):
            if len(r) == 6 and r[0].isdigit():
                sec, when, home, score, away, venue = r
                m = re.fullmatch(r"(\d+)-(\d+)", score.replace(" ", ""))
                games.append({"sec": int(sec), "when": when, "home": home, "away": away, "venue": venue, "hg": int(m[1]) if m else None, "ag": int(m[2]) if m else None})
        table = []
        for r in rows_of(rank.find("table")):
            if len(r) == 10 and r[1].isdigit():
                table.append(dict(zip(["team", "pts", "gp", "w", "l", "d", "gf", "ga", "gd", "rank"], [r[0]] + [int(x) for x in r[1:]])))
        for t in teams:
            mine = [g for g in games if normalize(g["home"]) == t or normalize(g["away"]) == t]
            out.setdefault(t, []).append({
                "league": f"{div} {block}",
                "source": f"https://www.tleague-u18.com/schedule.php?dy=2026&dt=5&ltno={no}",
                "table": table,
                "teamName": next((row["team"] for row in table if normalize(row["team"]) == t), t),
                "games": [view(g, t) for g in mine],
            })
    return out


def view(g: dict, t: str) -> dict:
    home = normalize(g["home"]) == t
    gf, ga = (g["hg"], g["ag"]) if home else (g["ag"], g["hg"])
    res = None if gf is None else ("勝" if gf > ga else "負" if gf < ga else "分")
    return {"when": g["when"], "opp": g["away"] if home else g["home"], "home": home, "venue": g["venue"], "gf": gf, "ga": ga, "res": res}


def riverside(refresh: bool) -> dict:
    raw = fetch("https://riverside-league.com/schedule_division1.html", RAW / "riverside_div1.html", refresh).decode("cp932", errors="replace")
    s = BeautifulSoup(raw, "html.parser")
    games = []
    for r in rows_of(s.find_all("table")[2]):
        if r and r[0].startswith("第"):
            r = r[1:]
        if len(r) >= 5 and re.search(r"\d+月\d+日", r[0]):
            when, home, score, away, venue = r[:5]
            m = re.fullmatch(r"(\d+)-(\d+)", score.replace(" ", ""))
            games.append({"when": when, "home": home, "away": away, "venue": venue, "hg": int(m[1]) if m else None, "ag": int(m[2]) if m else None})
    out = {}
    for label, t in RIVERSIDE_TEAMS.items():
        mine = [g for g in games if label in (g["home"], g["away"])]
        vs = []
        for g in mine:
            home = g["home"] == label
            gf, ga = (g["hg"], g["ag"]) if home else (g["ag"], g["hg"])
            vs.append({"when": g["when"], "opp": g["away"] if home else g["home"], "home": home, "venue": g["venue"], "gf": gf, "ga": ga, "res": None if gf is None else ("勝" if gf > ga else "負" if gf < ga else "分")})
        out.setdefault(t, []).append({"league": "リバーサイドユースリーグ 1部（Bチーム）", "source": "https://riverside-league.com/schedule_division1.html", "table": [], "teamName": label, "games": vs})
    return out


GOALNOTE = {  # goalnote（地区リーグ）: tid → {学校キー: そのリーグでのチーム名}
    18597: {"name": "NSリーグ2026", "teams": {"武蔵丘": ["都立武蔵丘高等学校A", "都立武蔵丘高等学校B"]}},
    18409: {"name": "DUOリーグ2026", "teams": {"昭和第一": ["昭和第一A", "昭和第一B"]}},
}


def member_areas(refresh: bool) -> dict:
    """高体連の加盟校一覧（地区・区市・学校）。学校キー → {地区, 区市, 設置, 表記}。"""
    raw = fetch("https://tokyosoccer-u18.com/member/", RAW / "tokyosoccer_member.html", refresh).decode("utf-8", "replace")
    s = BeautifulSoup(raw, "html.parser")
    out = {}
    for n in range(1, 9):
        div = s.find(id=f"area{n}")
        if not div:
            continue
        city = ""
        for line in div.get_text("\n", strip=True).split("\n"):
            m = re.fullmatch(r"[（(](都|私|国|区)[）)](.+)", line)
            if m:
                kind = {"都": "都立", "私": "私立", "国": "国立", "区": "区立"}[m[1]]
                out[normalize(m[2])] = {"area": n, "city": city, "kind": kind, "name": m[2]}
            elif re.search(r"(区|市|町|村|島)$", line) and len(line) <= 8:
                city = line
    return out


def goalnote(refresh: bool) -> dict:
    out = {}
    for tid, cfg in GOALNOTE.items():
        base = "https://www.goalnote.net"
        sched = BeautifulSoup(fetch(f"{base}/detail-schedule.php?tid={tid}", RAW / f"goalnote_{tid}_detail-schedule.html", refresh).decode("utf-8", "replace"), "html.parser")
        stand = BeautifulSoup(fetch(f"{base}/detail-standings.php?tid={tid}", RAW / f"goalnote_{tid}_detail-standings.html", refresh).decode("utf-8", "replace"), "html.parser")
        division = {}
        games = []
        cur_div = ""
        for tb in sched.find_all("table"):
            for r in rows_of(tb):
                if len(r) == 1 and re.search(r"\d部", r[0]):
                    cur_div = re.match(r"(\S+部)", r[0])[1]
                    continue
                if len(r) >= 7 and re.fullmatch(r"\d{4}/\d{2}/\d{2}", r[1]):
                    grp, date, tm, home, score, away, venue = r[:7]
                    division.setdefault(grp, cur_div)
                    m = re.match(r"(\d+)-(\d+)", score)
                    # 日付を登録していない試合は「2026/04/01 10:00・会場空欄」になっている
                    when = "日付未登録" if (date.endswith("/04/01") and tm == "10:00" and not venue) else f"{date[5:]} {tm}"
                    games.append({"grp": grp, "when": when, "home": home, "away": away, "venue": venue, "hg": int(m[1]) if m else None, "ag": int(m[2]) if m else None})
        tables = {}
        for tb in stand.find_all("table"):
            rows = rows_of(tb)
            if not rows or not rows[0][0].startswith("グループ"):
                continue
            grp = rows[0][0].replace("グループ", "")
            tables[grp] = [dict(zip(["rank", "team", "pts", "gp", "w", "d", "l", "gf", "ga", "gd"], r)) for r in rows[1:] if len(r) >= 10]
        for key, names in cfg["teams"].items():
            for nm in names:
                mine = [g for g in games if nm in (g["home"], g["away"])]
                if not mine:
                    continue
                grp = mine[0]["grp"]
                vs = []
                for g in sorted(mine, key=lambda g: g["when"]):
                    home = g["home"] == nm
                    gf, ga = (g["hg"], g["ag"]) if home else (g["ag"], g["hg"])
                    vs.append({"when": g["when"], "opp": g["away"] if home else g["home"], "home": home, "venue": g["venue"], "gf": gf, "ga": ga, "res": None if gf is None else ("勝" if gf > ga else "負" if gf < ga else "分")})
                num = lambda v: int(v.replace("+", "")) if re.fullmatch(r"[+-]?\d+", v or "") else 0  # noqa: E731  試合がまだ無いチームは空欄
                table = [{"team": t["team"], **{f: num(t[f]) for f in ("pts", "gp", "w", "l", "d", "gf", "ga", "gd", "rank")}} for t in tables.get(grp, [])]
                out.setdefault(key, []).append({"league": f"{cfg['name']} {division.get(grp, '')} グループ{grp}".replace("  ", " "), "source": f"{base}/detail-schedule.php?tid={tid}", "table": table, "teamName": nm, "games": vs})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="サイトから取り直す")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    data = tleague(args.refresh)
    for k, v in riverside(args.refresh).items():
        data.setdefault(k, []).extend(v)
    for k, v in goalnote(args.refresh).items():
        data.setdefault(k, []).extend(v)
    out = ROOT / "out/scout/leagues_2026.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    areas = member_areas(args.refresh)
    (ROOT / "out/scout/member_areas.json").write_text(json.dumps(areas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"加盟校 {len(areas)}校", {n: sum(1 for v in areas.values() if v["area"] == n) for n in range(1, 9)})
    for t, lgs in data.items():
        for lg in lgs:
            played = [g for g in lg["games"] if g["res"]]
            rec = f"{sum(g['res'] == '勝' for g in played)}勝{sum(g['res'] == '分' for g in played)}分{sum(g['res'] == '負' for g in played)}敗 得{sum(g['gf'] for g in played)} 失{sum(g['ga'] for g in played)}"
            print(t, lg["league"], f"{len(played)}試合", rec, "残り", len(lg["games"]) - len(played))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
