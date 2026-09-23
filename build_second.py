"""第105回選手権 東京 2次予選（都大会）のトーナメント表と勝ち上がり予想を作る。

- 組み合わせは pdfs/sen26_2j.pdf を parse_bracket.py で読んだ out/json/sen26_2j.json から取る
- 勝ち上がりの見込みは、いまの強さの点数から1試合ずつ掛け合わせる（analyze_team と同じ考え方）
- 準決勝・決勝は4つの山の勝者どうしなので、山の優勝確率から組み立てる

出力: out/scout/second_2026.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from analyze_team import compute_elo, load_matches, normalize, win_prob

ROOT = Path(__file__).parent
BASE = 1500.0


def read_bracket() -> list[list]:
    """4つの山それぞれについて、トーナメント表の並び順で校名を返す。"""
    d = json.loads((ROOT / "out/json/sen26_2j.json").read_text(encoding="utf-8"))
    ms = {m["id"]: m for m in d["pages"][0]["matches"]}
    roots = sorted([m for m in ms.values() if m.get("parent") is None], key=lambda m: m["id"])

    def leaves(m: dict) -> list:
        out = []
        for s in ("slot1", "slot2"):
            v = m.get(s) or {}
            if v.get("leaf"):
                out.append(normalize(v["leaf"]))
            elif v.get("from") in ms:
                out.extend(leaves(ms[v["from"]]))
        return out

    return [leaves(r) for r in roots]


def dist(seq: list, elo: dict) -> dict:
    """その山を勝ち上がる確率の分布。1校だけなら不戦でそのまま上がる。"""
    if len(seq) == 1:
        return {seq[0]: 1.0}
    half = len(seq) // 2
    left, right = dist(seq[:half], elo), dist(seq[half:], elo)
    out: dict = defaultdict(float)
    for a, pa in left.items():
        for b, pb in right.items():
            p = win_prob(elo.get(a, BASE), elo.get(b, BASE))
            out[a] += pa * pb * p
            out[b] += pa * pb * (1 - p)
    return dict(out)


def main() -> int:
    rows = load_matches()
    elo, _, n_games = compute_elo(rows)
    blocks = read_bracket()

    # 山ごとの優勝確率 → 準決勝・決勝へ。山0と山1、山2と山3が準決勝で当たる並び
    block_win = [dist(b, elo) for b in blocks]
    semi = [(0, 1), (2, 3)]
    final_dist: dict = defaultdict(float)
    semi_dist = []
    for i, j in semi:
        out: dict = defaultdict(float)
        for a, pa in block_win[i].items():
            for b, pb in block_win[j].items():
                p = win_prob(elo.get(a, BASE), elo.get(b, BASE))
                out[a] += pa * pb * p
                out[b] += pa * pb * (1 - p)
        semi_dist.append(dict(out))
    for a, pa in semi_dist[0].items():
        for b, pb in semi_dist[1].items():
            p = win_prob(elo.get(a, BASE), elo.get(b, BASE))
            final_dist[a] += pa * pb * p
            final_dist[b] += pa * pb * (1 - p)

    names = ["Aブロック 上", "Aブロック 下", "Bブロック 上", "Bブロック 下"]
    rank = sorted({t for b in blocks for t in b}, key=lambda t: -elo.get(t, BASE))
    teams = []
    for i, t in enumerate(rank, 1):
        bi = next(k for k, b in enumerate(blocks) if t in b)
        teams.append({
            "rank": i, "key": t, "elo": round(elo.get(t, BASE)), "games": n_games.get(t, 0),
            "block": bi + 1, "blockName": names[bi],
            "blockWin": round(block_win[bi].get(t, 0.0), 4),
            "semiWin": round(semi_dist[bi // 2].get(t, 0.0), 4),
            "title": round(final_dist.get(t, 0.0), 4),
        })
    pairs = []
    for bi, b in enumerate(blocks):
        for i in range(0, len(b) - 1, 2):
            a, c = b[i], b[i + 1]
            pairs.append({"block": bi + 1, "blockName": names[bi], "a": a, "b": c,
                          "aElo": round(elo.get(a, BASE)), "bElo": round(elo.get(c, BASE)),
                          "p": round(win_prob(elo.get(a, BASE), elo.get(c, BASE)), 3)})
        if len(b) % 2:
            pairs.append({"block": bi + 1, "blockName": names[bi], "a": b[-1], "b": None, "aElo": round(elo.get(b[-1], BASE)), "bElo": None, "p": 1.0})

    out = {"blocks": [[{"key": t, "elo": round(elo.get(t, BASE))} for t in b] for b in blocks],
           "teams": teams, "firstRound": pairs, "nTeams": len(rank), "blockNames": names,
           "predWinners": [max(bw, key=bw.get) for bw in block_win]}
    path = ROOT / "out/scout/second_2026.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path}  {len(rank)}校")
    for t in teams[:12]:
        print(f'  {t["rank"]:2d}. {t["key"]:12s} {t["elo"]}  山{t["block"]}  山制覇{t["blockWin"]*100:5.1f}%  優勝{t["title"]*100:5.1f}%')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
