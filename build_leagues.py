"""サイトの「今季のリーグ戦」のデータを、Tリーグ・プリンス関東・地区リーグのまとめデータから作る。

入力: data/leagues/tleague_*.csv・prince_kanto1_2026_*.csv・district_*.csv、scout/sen2026_block10.json（山の8校）
出力: out/scout/leagues_2026.json … {学校: [リーグ, …]}。サイトの leagueSection が読む形
- 1つの学校につき、Aチーム → 控え（B・C…）の順。同じチームの中はプリンス → Tリーグ → 地区リーグの順
- 順位表の無いリーグ（第8地区など）は、試合だけを載せる
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SEASON = 2026
LEVEL = {"プリンス": 0, "T": 1, "地区": 2}


def rows(path: str) -> list[dict]:
    p = ROOT / path
    return list(csv.DictReader(p.open(encoding="utf-8-sig"))) if p.exists() else []


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def when_of(date: str, time: str = "") -> str:
    m = re.match(r"\d{4}-(\d{2})-(\d{2})", date or "")
    return f"{m[1]}/{m[2]}" + (f" {time}" if time else "") if m else "日付未登録"


def table_of(st: list[dict]) -> list[dict]:
    out = []
    for r in sorted(st, key=lambda r: num(r["順位"]) or 99):
        out.append({"team": r["チーム"], "pts": num(r["勝点"]), "gp": num(r["試合"]), "w": num(r["勝"]), "l": num(r["敗"]), "d": num(r["分"]),
                    "gf": num(r["得点"]), "ga": num(r["失点"]), "gd": num(r["得失点"]), "rank": num(r["順位"])})
    return out


def games_of(ms: list[dict], school: str, squad: str) -> tuple[list[dict], str]:
    games, name = [], ""
    for r in ms:
        home = r["ホーム学校"] == school and r["ホーム区分"] == squad
        away = r["アウェイ学校"] == school and r["アウェイ区分"] == squad
        if not (home or away):
            continue
        name = name or (r["ホーム"] if home else r["アウェイ"])
        gf, ga = (num(r["ホーム得点"]), num(r["アウェイ得点"])) if home else (num(r["アウェイ得点"]), num(r["ホーム得点"]))
        done = r["実施"] == "済" and gf is not None and ga is not None
        games.append({"when": when_of(r.get("日付", ""), r.get("時刻", "")), "opp": r["アウェイ"] if home else r["ホーム"], "home": home, "venue": r.get("会場", ""),
                      "gf": gf if done else None, "ga": ga if done else None, "res": ("勝" if gf > ga else "負" if gf < ga else "分") if done else ""})
    games.sort(key=lambda g: g["when"])
    return games, name


def main() -> int:
    cfg = json.loads((ROOT / "scout/sen2026_block10.json").read_text(encoding="utf-8"))
    block = list(cfg["slots"].keys())
    tl_s = [r for r in rows("data/leagues/tleague_standings.csv") if num(r["年度"]) == SEASON]
    tl_m = [r for r in rows("data/leagues/tleague_matches.csv") if num(r["年度"]) == SEASON]
    ds_s = [r for r in rows("data/leagues/district_standings.csv") if num(r["年度"]) == SEASON]
    ds_m = [r for r in rows("data/leagues/district_matches.csv") if num(r["年度"]) == SEASON]
    pr_s = rows("data/leagues/prince_kanto1_2026_standings.csv")
    pr_m = rows("data/leagues/prince_kanto1_2026_matches.csv")
    from collect_tleague import squad_of  # プリンスの CSV には区分の列が無い
    from build_outputs import normalize
    for r in pr_m:
        for side in ("ホーム", "アウェイ"):
            b, sq = squad_of(r[side])
            r[f"{side}学校"], r[f"{side}区分"] = normalize(b), sq
    for r in pr_s:
        b, sq = squad_of(r["チーム"])
        r["学校"], r["区分"] = normalize(b), sq
    out = {}
    for school in block:
        entries = []
        # Tリーグ
        for r in [r for r in tl_s if r["学校"] == school]:
            grp = [x for x in tl_s if (x["リーグ"], x["ブロック"]) == (r["リーグ"], r["ブロック"])]
            ms = [m for m in tl_m if (m["リーグ"], m["ブロック"]) == (r["リーグ"], r["ブロック"])]
            games, _ = games_of(ms, school, r["区分"])
            entries.append(("T", r["区分"], {"league": f"Tリーグ {r['リーグ']}{' ' + r['ブロック'] if r['ブロック'] else ''}", "source": r["出典"].replace("rank.php", "schedule.php"),
                                             "table": table_of(grp), "teamName": r["チーム"], "games": games, "squad": r["区分"]}))
        # プリンス関東
        for r in [r for r in pr_s if r["学校"] == school]:
            games, _ = games_of(pr_m, school, r["区分"])
            entries.append(("プリンス", r["区分"], {"league": "プリンスリーグ関東1部", "source": r["出典"], "table": table_of(pr_s), "teamName": r["チーム"], "games": games, "squad": r["区分"]}))
        # 地区リーグ（順位表のある部）
        seen = set()
        for r in [r for r in ds_s if r["学校"] == school]:
            key = (r["地区"], r["リーグ"], r["部"], r["区分"])
            seen.add(key)
            grp = [x for x in ds_s if (x["地区"], x["リーグ"], x["部"]) == key[:3]]
            ms = [m for m in ds_m if (m["地区"], m["リーグ"], m["部"]) == key[:3]]
            games, _ = games_of(ms, school, r["区分"])
            src = re.sub(r"（試合から計算）$", "", r["出典"])
            entries.append(("地区", r["区分"], {"league": f"{r['リーグ']} {r['部']}（{r['地区']}）", "source": src, "table": table_of(grp), "teamName": r["チーム"],
                                              "games": games, "squad": r["区分"], "computed": r["出典"].endswith("（試合から計算）")}))
        # 地区リーグ（順位表の無い部。第8地区など）
        for m in ds_m:
            for side in ("ホーム", "アウェイ"):
                if m[f"{side}学校"] != school:
                    continue
                key = (m["地区"], m["リーグ"], m["部"], m[f"{side}区分"])
                if key in seen:
                    continue
                seen.add(key)
                ms = [x for x in ds_m if (x["地区"], x["リーグ"], x["部"]) == key[:3]]
                games, name = games_of(ms, school, key[3])
                entries.append(("地区", key[3], {"league": f"{key[1]} {key[2]}（{key[0]}）", "source": m["出典"], "table": [], "teamName": name,
                                                 "games": games, "squad": key[3], "noTable": True}))
        entries.sort(key=lambda e: (e[1], LEVEL[e[0]]))
        if entries:
            out[school] = [e[2] for e in entries]
    path = ROOT / "out/scout/leagues_2026.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for s, lgs in out.items():
        for lg in lgs:
            played = [g for g in lg["games"] if g["res"]]
            row = next((r for r in lg["table"] if r["team"] == lg["teamName"]), None)
            print(f"{s:8s} [{lg['squad']}] {lg['league']:34s} {('%s位/%d' % (row['rank'], len(lg['table']))) if row else '順位表なし':10s} 試合{len(played)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
