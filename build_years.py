"""武蔵丘の年度ごとの記録を、ページに載せる形にまとめる。

3つの粒度で書き出す（遠い年ほど粗くする）。
- この代の3年間（2024〜2026年度）… 大会ごとのトーナメント表・全試合の当時と今の点数・
  その年度の番狂わせ・リーグ戦の順位表まで
- その前の3年間（2021〜2023年度）… 大会ごとの全試合と点数まで。トーナメント表は載せない
- 前史（2004〜2020年度）… 1年度を1行に。勝敗・到達・年度末の点数だけ

点数はいつも「その試合の時点の値」と「いまの値」を並べる。当時の点数だけで相手を
測ると、そのあと強くなった相手（佼成学園など）を「格下に負けた」と読み違えるため。

出力: out/scout/years.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_team import compute_elo, load_matches, normalize, played, result_for, win_prob
from dataset import source
from leagues import for_school, load_all

ROOT = Path(__file__).parent
ME = "武蔵丘"
SQUAD = (2024, 2025, 2026)
ERA = (2021, 2022, 2023)
SERIES = ("総体", "選手権", "新人戦", "関東")
ROUND_RANK = {"1回戦": 1, "2回戦": 2, "3回戦": 3, "4回戦": 4, "ブロック決勝": 5, "準々決勝": 5,
              "準決勝": 6, "3位決定戦": 7, "決勝": 7}
MIN_GAMES = 5  # 番狂わせの一覧に入れるのは、両校とも5試合以上の記録がある試合だけ（点数のぶれが大きいため）


def first_stage(stage: str) -> bool:
    """1次の段階（総体の支部予選・選手権の一次予選・新人戦の地区大会）か。"""
    return "支部予選" in stage or "一次予選" in stage or "地区大会" in stage


def stage_label(series: str, stage: str) -> str:
    s = stage.replace("一次", "1次").replace("二次", "2次")
    return f"{series} {s}"


def rnd(v):
    return round(v) if v is not None else None


def last_of_bracket(g: dict) -> bool:
    """勝って終わっても、そこが表のいちばん上（決勝）なら「記録はここまで」ではない。"""
    return g["round"] in ("決勝", "3位決定戦")


def rank_of(rnd: str) -> int:
    return ROUND_RANK.get(rnd, 0)


# ---------- トーナメント表 ----------

def block_rows(rows: list[dict], r: dict) -> list[dict]:
    """その試合と同じ表・同じブロックの試合。"""
    key = lambda x: (x["年度"], x["大会"], x["段階"], x["地区・支部"], x["ブロック"], x["出典PDF"], x["ページ"])
    k = key(r)
    return [x for x in rows if key(x) == k and x["kA"] and x["kB"]]


def build_tree(block: list[dict], last: dict) -> dict:
    """武蔵丘の最後の試合から、8校以内に収まるところまで親をさかのぼった部分木を返す。"""
    def winner(m: dict) -> str:
        return normalize(m["勝者"]) if m["勝者"] else ""

    def prev(m: dict, team: str) -> dict | None:
        c = [x for x in block if rank_of(x["ラウンド"]) < rank_of(m["ラウンド"]) and team in (x["kA"], x["kB"])]
        return max(c, key=lambda x: rank_of(x["ラウンド"])) if c else None

    def parent(m: dict) -> dict | None:
        w = winner(m)
        if not w:
            return None
        c = [x for x in block if rank_of(x["ラウンド"]) > rank_of(m["ラウンド"]) and w in (x["kA"], x["kB"])]
        return min(c, key=lambda x: rank_of(x["ラウンド"])) if c else None

    def node(m: dict) -> dict:
        kids = []
        for team, name in ((m["kA"], m["チームA"]), (m["kB"], m["チームB"])):
            p = prev(m, team)
            kids.append(node(p) if p else {"t": name, "k": team})
        return {"m": {"round": m["ラウンド"], "date": m["日付"], "a": m["チームA"], "b": m["チームB"],
                      "ka": m["kA"], "kb": m["kB"], "sa": m["得点A"], "sb": m["得点B"],
                      "pa": m["PK_A"], "pb": m["PK_B"], "w": winner(m)}, "c": kids}

    def leaves(n: dict) -> int:
        return 1 if "t" in n else sum(leaves(c) for c in n["c"])

    top = last
    while (p := parent(top)) is not None and leaves(node(p)) <= 8:
        top = p
    return node(top)


# ---------- 1年度ぶん ----------

def season(rows: list[dict], y: int, elo: dict, hist: dict, n_games: dict, detail: str) -> dict:
    mine = [r for r in rows if r["年度"] == y and ME in (r["kA"], r["kB"])]
    games = []
    tours: dict[tuple, dict] = {}
    for r in mine:
        # 「未実施」は、アーカイブに結果の入る前の版しか残っていない試合を含む。
        # 行われなかったとは言い切れないので、出場の記録として「結果不明」で残す
        known = played(r)
        g = result_for(r, ME) if known else {
            "year": y, "series": r["大会"], "stage": r["段階"], "round": r["ラウンド"], "date": r["日付"],
            "opp": r["チームB"] if r["kA"] == ME else r["チームA"], "oppKey": r["kB"] if r["kA"] == ME else r["kA"],
            "gf": None, "ga": None, "pk": "", "src": r["出典PDF"], "myElo": None, "oppElo": None,
            # 不戦勝・棄権は結果だけ残し、勝敗の数には入れない
            "res": ("不戦勝" if normalize(r["勝者"]) == ME else "不戦敗") if "不戦" in r["状態"] and r["勝者"] else ""}
        me_e, op_e = g.get("myElo"), g.get("oppElo")
        now_opp = elo.get(g["oppKey"])
        item = {
            "series": r["大会"], "stage": r["段階"], "round": r["ラウンド"], "date": r["日付"],
            "opp": g["opp"].replace("都・", "").replace("国・", "").replace("私・", ""), "oppKey": g["oppKey"],
            "gf": g["gf"], "ga": g["ga"], "pk": g["pk"], "res": g["res"],
            "me": round(me_e) if me_e is not None else None, "oppElo": round(op_e) if op_e is not None else None,
            "p": round(win_prob(me_e, op_e), 3) if me_e is not None and op_e is not None else None,
            "nowOpp": round(now_opp) if now_opp is not None else None,
            "src": r["出典PDF"],
        }
        games.append(item)
        tk = (r["大会"], r["段階"])
        t = tours.setdefault(tk, {"series": r["大会"], "stage": r["段階"], "label": stage_label(r["大会"], r["段階"]),
                                  "block": r["ブロック"].lstrip("→"), "area": r["地区・支部"], "games": [], "src": r["出典PDF"]})
        t["games"].append(item)
        if detail == "full" and first_stage(r["段階"]):
            t["_last"] = r  # 1次の段階の最後の試合（行は時系列順）
    for t in tours.values():
        last = t["games"][-1]
        won = last["res"] in ("勝", "PK勝", "不戦勝")
        t["reach"] = (f'{last["round"]}' + (" 勝（記録はここまで）" if won and not last_of_bracket(last) else "" if won else " 敗退")
                      if last["res"] else f'{last["round"]}（結果不明）')
        if "_last" in t:
            t["tree"] = build_tree(block_rows(rows, t["_last"]), t.pop("_last"))
    order = lambda t: (SERIES.index(t["series"]) if t["series"] in SERIES else 9, 0 if first_stage(t["stage"]) else 1)
    tl = sorted(tours.values(), key=order)

    known = [g for g in games if g["res"] in ("勝", "PK勝", "PK負", "負")]
    c = Counter(g["res"] for g in known)
    rated = [g for g in known if g["me"] is not None]
    # 年度末の順位（学校の点数を、その年度末の値で並べる）
    # その年度に大会の試合をした学校だけで並べる（点数は持ち越されるため、休部・統合した学校まで数えないように）
    active = {k for r in rows if r["年度"] == y and played(r) for k in (r["kA"], r["kB"])}
    ends = sorted(((k, v[y]) for k, v in hist.items() if y in v and k in active), key=lambda kv: -kv[1])
    rank = next((i + 1 for i, (k, _) in enumerate(ends) if k == ME), None)
    out = {
        "year": y, "n": len(games), "known": len(known),
        "w": c["勝"], "pkw": c["PK勝"], "pkl": c["PK負"], "l": c["負"],
        "gf": sum(g["gf"] for g in known), "ga": sum(g["ga"] for g in known),
        "cleanSheets": sum(1 for g in known if g["ga"] == 0),
        "start": rnd(hist.get(ME, {}).get(y - 1)), "end": rnd(hist.get(ME, {}).get(y)),
        "peak": max((g["me"] for g in rated), default=None),
        "rankEnd": rank, "nRatedEnd": len(ends),
        "upWins": [g for g in known if g["res"] == "勝" and g["me"] is not None and g["oppElo"] > g["me"]],
        "reach": {t["series"]: t["reach"] for t in tl if first_stage(t["stage"]) or t["series"] == "関東"},
        "tournaments": tl,
    }
    # 2次以上へ進んだ大会は、最後に出た段階の到達を上書きする
    for t in tl:
        if not first_stage(t["stage"]):
            out["reach"][t["series"]] = f'{t["label"].split(" ", 1)[1]} {t["reach"]}'
    if detail != "line":
        out["avgOpp"] = round(sum(g["oppElo"] for g in rated) / len(rated)) if rated else None
    if detail == "full":
        out["upsets"] = year_upsets(rows, y, n_games)
    return out


def year_upsets(rows: list[dict], y: int, n_games: dict) -> dict:
    """その年度の1次の段階（総体・選手権・新人戦）で、90分で格上が倒された試合。"""
    out = []
    for r in rows:
        if not (r["年度"] == y and played(r) and first_stage(r["段階"]) and r["勝者"]):
            continue
        ea, eb = r.get("_eloA"), r.get("_eloB")
        if ea is None or eb is None or (r["PK_A"] or r["PK_B"]):
            continue
        a, b = r["kA"], r["kB"]
        win_a = normalize(r["勝者"]) == a
        w, l, we, le = (a, b, ea, eb) if win_a else (b, a, eb, ea)
        if le <= we or min(n_games.get(w, 0), n_games.get(l, 0)) < MIN_GAMES:
            continue
        gf, ga = (r["得点A"], r["得点B"]) if win_a else (r["得点B"], r["得点A"])
        out.append({"series": r["大会"], "round": r["ラウンド"], "winner": w, "loser": l,
                    "winnerElo": round(we), "loserElo": round(le), "gap": round(le - we),
                    "score": f"{gf}-{ga}", "p": round(win_prob(we, le), 3)})
    out.sort(key=lambda x: x["p"])
    mine = [i + 1 for i, x in enumerate(out) if ME in (x["winner"], x["loser"])]
    return {"n": len(out), "top": out[:10], "mine": [dict(out[i - 1], rank=i) for i in mine]}


def league(y: int, games: list[dict], standings: list[dict]) -> dict | None:
    gs = [g for g in games if int(g["年度"]) == y]
    st = [s for s in standings if s["年度"] == str(y) and s["学校"] == ME]
    if not gs and not st:
        return None
    c = Counter(g["結果"] for g in gs)
    return {
        "games": [{"league": g["大会"], "div": g["段階"], "opp": g["相手"], "gf": g["得点"], "ga": g["失点"],
                   "res": g["結果"], "date": g["日付"]} for g in gs],
        "w": c["○"], "d": c["△"], "l": c["●"],
        "gf": sum(g["得点"] or 0 for g in gs), "ga": sum(g["失点"] or 0 for g in gs),
        "standings": [{"team": s["区分"], "league": s["リーグ"], "div": s["部"], "rank": s["順位"],
                       "n": s["試合"], "w": s["勝"], "d": s["分"], "l": s["敗"], "gf": s["得点"], "ga": s["失点"],
                       "pts": s["勝点"], "src": s["出典"]} for s in st],
    }


def main() -> int:
    rows = load_matches()
    elo, hist, n_games = compute_elo(rows)
    lg = for_school(load_all(), ME)
    standings = list(csv.DictReader(source.path("data/leagues/district_standings.csv").open(encoding="utf-8-sig")))
    first = min(r["年度"] for r in rows if ME in (r["kA"], r["kB"]))

    years = {}
    for y in range(first, 2027):
        detail = "full" if y in SQUAD else "games" if y in ERA else "line"
        s = season(rows, y, elo, hist, n_games, detail)
        if s["n"] == 0:
            continue
        s["detail"] = detail
        lgy = league(y, lg, standings)
        if lgy:
            s["league"] = lgy if detail != "line" else {k: lgy[k] for k in ("w", "d", "l", "gf", "ga")} | {"n": len(lgy["games"])}
        years[str(y)] = s

    ranked = sorted(elo.items(), key=lambda kv: -kv[1])
    doc = {
        "me": ME, "first": first, "now": round(elo[ME]),
        "rankNow": next(i + 1 for i, (k, _) in enumerate(ranked) if k == ME), "nRatedNow": len(ranked),
        "eloHistory": {k: round(v) for k, v in sorted(hist.get(ME, {}).items())},
        "years": years,
    }
    p = ROOT / "out/scout/years.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"wrote {p.name}  {len(years)}年度（{min(years)}〜{max(years)}）")
    for y in (*SQUAD, *ERA):
        s = years.get(str(y))
        if s:
            print(f'  {y}: {s["n"]}試合 {s["w"]}勝{s["pkw"]}PK勝{s["pkl"]}PK負{s["l"]}敗  {s["start"]}→{s["end"]}  '
                  f'{s["rankEnd"]}/{s["nRatedEnd"]}位  木{sum(1 for t in s["tournaments"] if "tree" in t)}  '
                  f'番狂わせ{s.get("upsets", {}).get("n", "-")}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
