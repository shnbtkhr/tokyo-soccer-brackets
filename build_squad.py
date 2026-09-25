"""この代（2024〜2026年度に在学した3年間）が戦った大会の全試合を書き出す。

各試合に「試合時点の点数」と「いまの点数」の両方を持たせる。試合の時点では下だった
相手が、その後に上へ行くことがあるため（例: 佼成学園は2025年11月に武蔵丘へ勝った
時点で1476、いまは1713で武蔵丘を上回る）。片方だけだと相手の評価を誤る。

出力: out/scout/squad_2026.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from analyze_team import compute_elo, load_matches, normalize, played, win_prob

ROOT = Path(__file__).parent
ME = "武蔵丘"
YEARS = (2024, 2025, 2026)  # 2026年度の3年生が在学した3年間
SERIES_ORDER = {"総体": 0, "選手権": 1, "新人戦": 2}


def main() -> int:
    rows = load_matches()
    elo, hist, n_games = compute_elo(rows)
    # 地区ごとにリーグ戦の取れ高が違う。理由まで誌面に書けるよう、相手の地区を持たせる
    ap = ROOT / "out/scout/member_areas.json"
    raw = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}
    areas = {k: (v.get("area") if isinstance(v, dict) else None) for k, v in raw.items()} if isinstance(raw, dict) else {}

    # 大会だけの試合数とリーグ戦の試合数を分ける（点数の動きやすさの目安として誌面に出す）
    tour = defaultdict(int)
    for r in rows:
        if played(r):
            for s in ("A", "B"):
                tour[normalize(r[f"チーム{s}"])] += 1

    def side(r: dict) -> tuple:
        a, b = normalize(r["チームA"]), normalize(r["チームB"])
        me_a = a == ME
        opp = b if me_a else a
        gf, ga = (r["得点A"], r["得点B"]) if me_a else (r["得点B"], r["得点A"])
        pk = (r["PK_A"], r["PK_B"]) if me_a else (r["PK_B"], r["PK_A"])
        ea, eb = (r.get("_eloA"), r.get("_eloB")) if me_a else (r.get("_eloB"), r.get("_eloA"))
        return opp, gf, ga, pk, ea, eb

    games = []
    for r in rows:
        if not (played(r) and r["年度"] in YEARS and ME in (normalize(r["チームA"]), normalize(r["チームB"]))):
            continue
        opp, gf, ga, pk, my_e, op_e = side(r)
        try:
            gf, ga = int(gf), int(ga)
        except (TypeError, ValueError):
            continue
        won = normalize(r["勝者"] or "") == ME
        drew = not r["勝者"]
        pk_played = bool(pk[0] or pk[1])
        res = "PK勝" if pk_played and won else "PK負" if pk_played and not won else "勝" if won else "分" if drew else "負"
        games.append({
            "year": r["年度"], "series": r["大会"], "stage": r["段階"], "round": r["ラウンド"],
            "date": (r["日付"] or "").strip(), "opp": opp,
            "gf": gf, "ga": ga, "pk": f"{pk[0]}-{pk[1]}" if pk_played else "",
            "halves": r.get("前後半") or "", "res": res,
            # 試合の時点の点数（rating が各行に書き戻したもの）
            "thenMe": round(my_e) if my_e is not None else None,
            "thenOpp": round(op_e) if op_e is not None else None,
            # いまの点数
            "nowMe": round(elo.get(ME, 1500)), "nowOpp": round(elo.get(opp, 1500)),
            "oppTournamentGames": tour.get(opp, 0),
            "oppLeagueGames": max(0, n_games.get(opp, 0) - tour.get(opp, 0)),
            "oppDistrict": areas.get(opp),
            "src": r.get("出典PDF") or "",
        })
        if my_e is not None and op_e is not None:
            games[-1]["thenProb"] = round(win_prob(my_e, op_e), 3)
            games[-1]["nowProb"] = round(win_prob(elo.get(ME, 1500), elo.get(opp, 1500)), 3)

    games.sort(key=lambda g: (g["year"], SERIES_ORDER.get(g["series"], 9)))

    # 大会ごとにまとめる
    tours: list = []
    for g in games:
        key = (g["year"], g["series"])
        if not tours or (tours[-1]["year"], tours[-1]["series"]) != key:
            tours.append({"year": g["year"], "series": g["series"], "stage": g["stage"], "games": []})
        tours[-1]["games"].append(g)
    for t in tours:
        gs = t["games"]
        t["record"] = {r: sum(1 for g in gs if g["res"] == r) for r in ("勝", "PK勝", "分", "PK負", "負")}
        t["gf"] = sum(g["gf"] for g in gs)
        t["ga"] = sum(g["ga"] for g in gs)
        t["reach"] = gs[-1]["round"] + ("" if gs[-1]["res"] in ("勝", "PK勝") else " 敗退")

    # 地区ごとの取れ高の事情。data/leagues/coverage.md の要約を誌面向けに1行で
    coverage = {
        1: "2025年度の記録が公式サイトに残っていない",
        2: "2024〜2026年度は取れている",
        3: "2025年度は最終順位だけで、試合ごとの結果が公開されていない",
        4: "地区をまとめたページが無く、年度によって取れ方が違う",
        5: "早大学院が公開している星取表が2008年度から残っており、8地区で最も厚い",
        6: "2024・2025年度の地区をまとめた結果ページが見つかっていない",
        7: "2024・2025年度は最終順位だけで、試合ごとの結果が載っていない",
        8: "結果ページの多くが JavaScript で描かれており、本文を取れていない",
    }
    out = {
        "me": ME, "years": list(YEARS), "nGames": len(games),
        "coverageByDistrict": coverage,
        "tournaments": tours,
        "eloHistory": hist.get(ME, {}),
        "myTournamentGames": tour.get(ME, 0),
        "myLeagueGames": max(0, n_games.get(ME, 0) - tour.get(ME, 0)),
    }
    path = ROOT / "out/scout/squad_2026.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path.name}  {len(games)}試合 / {len(tours)}大会")
    for t in tours:
        r = t["record"]
        print(f'  {t["year"]} {t["series"]:4s} {len(t["games"])}試合 {r["勝"]}勝{r["PK勝"]}PK勝{r["PK負"]}PK負{r["負"]}敗  → {t["reach"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
