"""武蔵丘の年度ごとの記録を並べ、歴代のランキングを作る。

年度単位でまとめる。世代（3年）で括ると、隣り合う代が同じ試合を共有して
ピークが同じ値で並び、順位がつかなかった（2026-09-27 に単位を変更）。

出力: out/scout/generations.json
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
ME = "武蔵丘"
BIG = ("ブロック決勝", "準々決勝", "準決勝", "決勝", "3位決定戦")
SERIES = ("選手権", "総体", "新人戦", "関東")


def reach(games: list, series: str) -> str:
    """その年度・その大会で、どこまで行ったか。"""
    gs = [g for g in games if g["series"] == series]
    if not gs:
        return ""
    last = gs[-1]
    ok = last["res"] in ("勝", "PK勝")
    # 勝った試合が最後なら、その先の記録が残っていないという意味になる
    return f'{last["round"]}{" 勝（記録はここまで）" if ok else " 敗退"}'


def main() -> int:
    m = json.loads((ROOT / "out/scout/musashigaoka_sen2026.json").read_text(encoding="utf-8"))["teams"][ME]
    games, hist, by = m["games"], m["eloHistory"], m["byYear"]
    years = sorted({g["year"] for g in games})

    out = []
    for y in years:
        gs = [g for g in games if g["year"] == y]
        s = by.get(str(y), {})
        big = [g for g in gs if any(k in g["round"] for k in BIG)]
        ups = sorted([g for g in gs if g["oppElo"] - g["myElo"] > 50 and g["res"] == "勝"],
                     key=lambda g: -(g["oppElo"] - g["myElo"]))
        peak_g = max(gs, key=lambda g: g["myElo"])
        prev = hist.get(str(y - 1))
        end = hist.get(str(y))
        out.append({
            "year": y, "n": len(gs),
            "w": s.get("w", 0), "pkw": s.get("pkw", 0), "pkl": s.get("pkl", 0), "l": s.get("l", 0),
            "gf": s.get("gf", 0), "ga": s.get("ga", 0),
            "gfPer": s.get("gfPer"), "gaPer": s.get("gaPer"),
            "cleanSheets": s.get("cleanSheets", 0), "scoreless": s.get("scoreless", 0),
            "winRate": round((s.get("w", 0) + s.get("pkw", 0)) / len(gs), 3) if gs else 0,
            "endElo": end, "prevElo": prev,
            "delta": (end - prev) if (end is not None and prev is not None) else None,
            "peak": peak_g["myElo"], "peakOpp": peak_g["opp"],
            "bigGames": len(big), "bigWins": sum(1 for g in big if g["res"] in ("勝", "PK勝")),
            "reach": {k: reach(gs, k) for k in SERIES if reach(gs, k)},
            "upsets": [{"series": g["series"], "round": g["round"], "opp": g["opp"],
                        "gf": g["gf"], "ga": g["ga"], "gap": g["oppElo"] - g["myElo"]} for g in ups[:2]],
        })

    rated = [x for x in out if x["endElo"] is not None]
    for i, x in enumerate(sorted(rated, key=lambda v: -v["endElo"]), 1):
        x["eloRank"] = i
    for i, x in enumerate(sorted(out, key=lambda v: -v["winRate"]), 1):
        x["winRank"] = i

    doc = {"me": ME, "years": [x["year"] for x in out], "nYears": len(out),
           "seasons": sorted(out, key=lambda x: -x["year"]),
           "note": "年度ごとの記録。順位は、その年度末の強さの点数で並べたもの。"
                   "高校の部活は3年で入れ替わるので、点数は前年度から持ち越して計算している。"}
    p = ROOT / "out/scout/generations.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {p.name}  {len(out)}年度")
    for x in sorted(rated, key=lambda v: v["eloRank"])[:5]:
        r = "／".join(f"{k} {v}" for k, v in x["reach"].items())
        print(f'  {x["eloRank"]:2d}位 {x["year"]}年度 {x["endElo"]} ({x["delta"]:+d}) '
              f'{x["n"]}試合 {x["w"]}勝{x["l"]}敗  {r}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
