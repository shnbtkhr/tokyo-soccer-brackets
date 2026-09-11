"""1チームの視点で、同じ山の相手を分析する（対戦相手カルテ・力の比較・勝ち上がりの見通し）。

入力: out/matches.csv（build_outputs.py の出力）
出力: out/scout/<チーム>_<大会>.json（ページに埋め込むデータ）

強さの点数は Elo レーティング。全試合を時系列に並べて更新する。
- 1年度の中の順序: 関東予選(4月) → 総体 支部予選 → 一次 → 二次 → 選手権 一次 → 二次 → 新人戦
- 得点差が大きいほど大きく動く（サッカー向け Elo でよく使う補正）
- PK 決着は引き分け（0.5）として扱う
- 年度が変わるたびに平均（1500）へ 1/4 戻す。部員は毎年入れ替わり、前年の強さはそのままは続かないため
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from build_outputs import normalize

ROOT = Path(__file__).parent
BASE, K, CARRY = 1500.0, 32.0, 0.75
STAGE_ORDER = [("関東", ""), ("総体", "支部予選"), ("総体", "一次"), ("総体", "二次"), ("選手権", "一次"), ("選手権", "二次"), ("新人戦", "")]
ROUND_ORDER = {"3位決定戦": 90, "決勝": 80, "ブロック決勝": 70, "準決勝": 60, "準々決勝": 50}


def stage_rank(r: dict) -> int:
    for i, (series, key) in enumerate(STAGE_ORDER):
        if r["大会"] == series and key in r["段階"]:
            return i
    return 99


def round_rank(r: dict) -> int:
    if r["ラウンド"] in ROUND_ORDER:
        return ROUND_ORDER[r["ラウンド"]]
    m = re.match(r"(\d+)回戦", r["ラウンド"])
    return int(m[1]) if m else 0


def load_matches() -> list[dict]:
    rows = list(csv.DictReader((ROOT / "out/matches.csv").open(encoding="utf-8-sig")))
    for r in rows:
        r["年度"] = int(r["年度"])
        r["kA"], r["kB"] = normalize(r["チームA"]), normalize(r["チームB"])
        r["_t"] = (r["年度"], stage_rank(r), round_rank(r))
    rows.sort(key=lambda r: r["_t"])
    return rows


def played(r: dict) -> bool:
    return r["状態"] in ("終了", "スコアのみ記載（赤線未反映）", "赤線が両側（スコアで判定）") and r["得点A"] != "" and r["得点B"] != ""


def result_for(r: dict, key: str) -> dict:
    """key のチームから見た1試合。"""
    a = r["kA"] == key
    gf, ga = (int(r["得点A"]), int(r["得点B"])) if a else (int(r["得点B"]), int(r["得点A"]))
    pkf = r["PK_A" if a else "PK_B"]
    pka = r["PK_B" if a else "PK_A"]
    won = r["勝者"] == (r["チームA"] if a else r["チームB"])
    pk = pkf != "" and pka != ""
    return {
        "year": r["年度"],
        "series": r["大会"],
        "stage": r["段階"] + (" " + r["地区・支部"] if r["地区・支部"] else ""),
        "round": r["ラウンド"],
        "date": r["日付"],
        "opp": r["チームB"] if a else r["チームA"],
        "oppKey": r["kB"] if a else r["kA"],
        "gf": gf,
        "ga": ga,
        "pk": f"{pkf}-{pka}" if pk else "",
        "et": "(延長)" in r["スコア"],
        "res": ("PK勝" if pk else "勝") if won else ("PK負" if pk else "負"),
        "src": r["出典PDF"],
        "myElo": r.get("_eloA" if a else "_eloB"),
        "oppElo": r.get("_eloB" if a else "_eloA"),
    }


def compute_elo(rows: list[dict]) -> tuple[dict, dict]:
    """全試合で Elo を更新する。現在値と、チームごとの推移（年度末の値）を返す。"""
    elo: dict[str, float] = defaultdict(lambda: BASE)
    hist: dict[str, dict] = defaultdict(dict)
    n_games: dict[str, int] = defaultdict(int)
    year = None
    for r in rows:
        if r["年度"] != year:
            if year is not None:
                for k in list(elo):
                    hist[k][year] = round(elo[k])
                    elo[k] = BASE + (elo[k] - BASE) * CARRY
            year = r["年度"]
        if not played(r) or not r["kA"] or not r["kB"]:
            continue
        a, b = r["kA"], r["kB"]
        # 試合の時点の点数を残す（格上・格下に対する成績を見るため）
        r["_eloA"], r["_eloB"] = round(elo[a]), round(elo[b])
        ga, gb = int(r["得点A"]), int(r["得点B"])
        if r["PK_A"] != "" and r["PK_B"] != "":
            sa = 0.5
        else:
            sa = 1.0 if ga > gb else 0.0 if ga < gb else 0.5
        exp = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
        margin = abs(ga - gb)
        mult = 1.0 if margin <= 1 else 1.5 if margin == 2 else (11 + margin) / 8
        d = K * mult * (sa - exp)
        elo[a] += d
        elo[b] -= d
        n_games[a] += 1
        n_games[b] += 1
    for k in list(elo):
        hist[k][year] = round(elo[k])
    return dict(elo), {k: dict(v) for k, v in hist.items()}, dict(n_games)


def win_prob(ea: float, eb: float) -> float:
    return 1 / (1 + 10 ** ((eb - ea) / 400))


def block_probabilities(bracket: list, elo: dict) -> dict:
    """山の勝ち上がり確率を、勝敗が確定した試合は確定として厳密に計算する。

    bracket は入れ子のリスト。葉はチームのキー、["勝者確定", key] は結果が出た試合。
    """

    def dist(node) -> dict:
        if isinstance(node, str):
            return {node: 1.0}
        if isinstance(node, dict):  # 結果が出た試合
            return {node["winner"]: 1.0}
        left, right = dist(node[0]), dist(node[1])
        out: dict = defaultdict(float)
        for a, pa in left.items():
            for b, pb in right.items():
                p = win_prob(elo.get(a, BASE), elo.get(b, BASE))
                out[a] += pa * pb * p
                out[b] += pa * pb * (1 - p)
        return dict(out)

    return dist(bracket)


def common_opponents(games: dict, me: str, opp: str) -> list:
    """共通の対戦相手ごとに、両チームの結果を並べる（直接対戦は含めない）。"""
    by_me = defaultdict(list)
    by_opp = defaultdict(list)
    for g in games[me]:
        if g["oppKey"] != opp:
            by_me[g["oppKey"]].append(g)
    for g in games[opp]:
        if g["oppKey"] != me:
            by_opp[g["oppKey"]].append(g)
    out = []
    for k in sorted(set(by_me) & set(by_opp)):
        out.append({"common": by_me[k][0]["opp"], "me": by_me[k], "them": by_opp[k]})
    return out


def summarize(gs: list) -> dict:
    n = len(gs)
    if not n:
        return {"n": 0}
    w = sum(g["res"] == "勝" for g in gs)
    pw = sum(g["res"] == "PK勝" for g in gs)
    pl = sum(g["res"] == "PK負" for g in gs)
    l = sum(g["res"] == "負" for g in gs)
    gf = sum(g["gf"] for g in gs)
    ga = sum(g["ga"] for g in gs)
    return {
        "n": n,
        "w": w,
        "pkw": pw,
        "pkl": pl,
        "l": l,
        "gf": gf,
        "ga": ga,
        "gfPer": round(gf / n, 2),
        "gaPer": round(ga / n, 2),
        "cleanSheets": sum(g["ga"] == 0 for g in gs),
        "scoreless": sum(g["gf"] == 0 for g in gs),
        "oneGoal": sum(abs(g["gf"] - g["ga"]) <= 1 and g["res"] in ("勝", "負") for g in gs),
        "et": sum(g["et"] for g in gs),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="武蔵丘")
    ap.add_argument("--block", nargs="+", default=["学習院", "板橋有徳", "昭和第一", "武蔵丘", "府中", "城東", "多摩科学技術", "東村山"], help="山の8校（トーナメント表の並び順）")
    ap.add_argument("--out", type=Path, default=ROOT / "out/scout/musashigaoka_sen2026.json")
    args = ap.parse_args()

    rows = load_matches()
    elo, hist, n_games = compute_elo(rows)
    games: dict[str, list] = defaultdict(list)
    for r in rows:
        if not played(r):
            continue
        for key in (r["kA"], r["kB"]):
            if key:
                games[key].append(result_for(r, key))

    teams = {}
    ranked = sorted(elo.items(), key=lambda kv: -kv[1])
    rank_of = {k: i + 1 for i, (k, _) in enumerate((k, v) for k, v in ranked if n_games.get(k, 0) >= 5)}
    for key in args.block:
        gs = games[key]
        by_year = defaultdict(list)
        for g in gs:
            by_year[g["year"]].append(g)
        teams[key] = {
            "key": key,
            "names": sorted({r["チームA"] for r in rows if r["kA"] == key} | {r["チームB"] for r in rows if r["kB"] == key}),
            "elo": round(elo.get(key, BASE)),
            "eloRank": rank_of.get(key),
            "eloHistory": hist.get(key, {}),
            "summary": summarize(gs),
            "byYear": {y: summarize(v) for y, v in sorted(by_year.items())},
            "bySeries": {s: summarize([g for g in gs if g["series"] == s]) for s in ("総体", "選手権", "新人戦", "関東")},
            "games": gs,
            "recent": summarize([g for g in gs if g["year"] >= 2025]),
        }

    me = args.me
    comparisons = {}
    for key in args.block:
        if key == me:
            continue
        h2h = [g for g in games[me] if g["oppKey"] == key]
        comparisons[key] = {
            "headToHead": h2h,
            "common": common_opponents(games, me, key),
            "winProb": round(win_prob(elo.get(me, BASE), elo.get(key, BASE)), 3),
        }

    # 山の形（sen26_1j.pdf の【10】）。結果が出た試合は勝者を確定させる
    b = args.block
    decided = {}
    for r in rows:
        if r["大会"] == "選手権" and r["年度"] == 2026 and r["勝者"]:
            decided[frozenset((r["kA"], r["kB"]))] = normalize(r["勝者"])

    def match(x, y):
        w = decided.get(frozenset((x, y)))
        return {"winner": w} if w else [x, y]

    bracket = [[match(b[0], b[1]), match(b[2], b[3])], [match(b[4], b[5]), match(b[6], b[7])]]
    probs = block_probabilities(bracket, elo)

    ratings_top = [{"key": k, "elo": round(v), "games": n_games.get(k, 0)} for k, v in ranked if n_games.get(k, 0) >= 5][:60]
    out = {
        "me": me,
        "block": args.block,
        "teams": teams,
        "comparisons": comparisons,
        "blockWinProb": {k: round(v, 3) for k, v in sorted(probs.items(), key=lambda kv: -kv[1])},
        "decided": [{"teams": sorted(k), "winner": v} for k, v in decided.items() if k <= set(b)],
        "ratingsTop": ratings_top,
        "nTeamsRated": len(rank_of),
        "eloParams": {"base": BASE, "k": K, "carry": CARRY},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size // 1024} KB)")
    for k in args.block:
        t = teams[k]
        s = t["summary"]
        print(f"{k:8s} elo={t['elo']} rank={t['eloRank']} 試合{s['n']} {s['w']}勝{s['pkw']}PK勝{s['pkl']}PK負{s['l']}敗 得{s.get('gfPer')} 失{s.get('gaPer')}  山勝率={out['blockWinProb'].get(k)}  武蔵丘の勝率={comparisons.get(k, {}).get('winProb')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
