"""第105回選手権 東京 1次予選で起きたジャイアントキリングを並べる。

「番狂わせ度」＝ 勝った側の、試合前の勝つ見込みの低さ。
強さの点数は試合の時点の値（analyze_team.compute_elo が各行に書き戻す _eloA・_eloB）を使う。

出力: out/scout/upsets_2026.json
"""

from __future__ import annotations

import json
from pathlib import Path

from analyze_team import compute_elo, load_matches, normalize, played, win_prob

ROOT = Path(__file__).parent
MIN_GAMES = 5  # 試合数が少ない学校は点数のぶれが大きいので、ランキングからは外す


def main() -> int:
    rows = load_matches()
    _, _, n_games = compute_elo(rows)
    out = []
    for r in rows:
        if not (played(r) and r["年度"] == 2026 and r["大会"] == "選手権"):
            continue
        a, b = normalize(r["チームA"]), normalize(r["チームB"])
        ea, eb = r.get("_eloA"), r.get("_eloB")
        if not r["勝者"] or ea is None or eb is None:
            continue
        win_a = normalize(r["勝者"]) == a
        w, l = (a, b) if win_a else (b, a)
        we, le = (ea, eb) if win_a else (eb, ea)
        if le <= we:
            continue  # 格上が勝った＝番狂わせではない
        gf, ga = (int(r["得点A"]), int(r["得点B"])) if win_a else (int(r["得点B"]), int(r["得点A"]))
        pk = (r["PK_A"] or r["PK_B"]) and True or False
        out.append({
            "round": r["ラウンド"], "date": r["日付"], "block": r["ブロック"],
            "winner": w, "loser": l, "winnerElo": round(we), "loserElo": round(le),
            "gap": round(le - we), "score": f"{gf}-{ga}", "pk": pk,
            "p": round(win_prob(we, le), 3),
            "winnerGames": n_games.get(w, 0), "loserGames": n_games.get(l, 0),
            "thin": n_games.get(w, 0) < MIN_GAMES or n_games.get(l, 0) < MIN_GAMES,
        })
    out.sort(key=lambda x: x["p"])
    path = ROOT / "out/scout/upsets_2026.json"
    path.write_text(json.dumps({"minGames": MIN_GAMES, "upsets": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    solid = [x for x in out if not x["thin"]]
    print(f"wrote {path} 番狂わせ {len(out)}件（うち両校5試合以上 {len(solid)}件）")
    for x in solid[:12]:
        print(f'  {x["p"]*100:4.1f}%  {x["round"]:8s} {x["winner"]}({x["winnerElo"]}) {x["score"]} {x["loser"]}({x["loserElo"]})  差{-x["gap"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
