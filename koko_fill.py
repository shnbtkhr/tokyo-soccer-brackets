"""トーナメント表から読めなかったスコアを、高校サッカードットコムの結果で埋める。

古いトーナメント表は「結果が入る前の版」しか残っていない年がある（2014〜2016年度は
半分以上のスコアが空）。同じ大会の結果が高校サッカードットコムに日付つきで残っている
ので、突き合わせて空欄だけを埋める。

照合の鍵は（年度・大会・対戦カード）の3つ。同じ組み合わせが年度内に複数あって、しかも
スコアが食い違う場合は、どちらの試合か決められないので埋めない。トーナメント表に
赤線（勝者）が引いてあってスコアだけ無い試合では、埋めたスコアの勝敗が赤線と一致するか
を確かめ、食い違えば別の試合とみなして埋めない。

  uv run python koko_fill.py          # 何件埋まるかを見るだけ（書き込まない）

build_outputs.py から apply_fills() が呼ばれ、out/matches.csv の生成時に反映される。
埋めた試合には備考に「結果は高校サッカードットコム」が付く。
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).parent
SRC = ROOT / "data/koko_tokyo_matches.csv"
NOTE = "結果は高校サッカードットコム"

_cache: dict | None = None


def load_fills() -> dict:
    """(年度, 大会, 両校の正規化名の組) → 候補の一覧。"""
    global _cache
    if _cache is not None:
        return _cache
    out: dict = defaultdict(list)
    if SRC.exists():
        with SRC.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                a, b = r["学校A"], r["学校B"]
                if not a or not b or a == b:
                    continue
                out[(r["年度"], r["大会"], frozenset((a, b)))].append({
                    "a": a, "b": b,
                    "sa": int(r["得点A"]), "sb": int(r["得点B"]),
                    "pa": int(r["PK_A"]) if r["PK_A"] else None,
                    "pb": int(r["PK_B"]) if r["PK_B"] else None,
                    "date": r["日付"],
                })
    _cache = out
    return out


def _pick(cands: list[dict]) -> dict | None:
    """候補が1つ、または全部が同じスコアなら、それを採る。割れていたら諦める。"""
    if not cands:
        return None
    key = {(c["sa"], c["sb"], c["a"]) for c in cands}
    return cands[0] if len(key) == 1 else None


def apply_fills(meta: dict, matches: list[dict], norm: Callable[[str], str]) -> dict:
    """スコアの空いている試合を埋める。埋めた件数などを返す。"""
    fills = load_fills()
    stat = {"filled": 0, "ambiguous": 0, "conflict": 0, "missing": 0}
    for m in matches:
        if m["score1"] is not None or not (m["team1"] and m["team2"]):
            continue
        a, b = norm(m["team1"]), norm(m["team2"])
        if not a or not b or a == b:
            continue
        cands = fills.get((str(meta["year"]), meta["series"], frozenset((a, b))), [])
        if not cands:
            stat["missing"] += 1
            continue
        c = _pick(cands)
        if c is None:
            stat["ambiguous"] += 1
            continue
        # 出典側の並び（a 対 b）を、トーナメント表の並び（team1 対 team2）に合わせ直す
        s1, s2 = (c["sa"], c["sb"]) if c["a"] == a else (c["sb"], c["sa"])
        p1, p2 = (c["pa"], c["pb"]) if c["a"] == a else (c["pb"], c["pa"])
        won = 1 if s1 > s2 else 2 if s2 > s1 else (1 if (p1 or 0) > (p2 or 0) else 2 if (p2 or 0) > (p1 or 0) else None)
        if m["winner_slot"] and won and m["winner_slot"] != won:
            stat["conflict"] += 1  # 赤線と食い違う＝同じ顔合わせの別の試合を拾っている
            continue
        m["score1"], m["score2"] = s1, s2
        if p1 is not None:
            m["pk1"], m["pk2"] = p1, p2
        if not m["winner_slot"] and won:
            m["winner_slot"] = won
        m["notes"] = m["notes"] + [NOTE]
        stat["filled"] += 1
    return stat


def main() -> int:
    """埋まる見込みを年度・大会ごとに数える（書き込みはしない）。"""
    import json

    from build_outputs import file_meta, normalize

    fills = load_fills()
    print(f"出典側の試合 {sum(len(v) for v in fills.values())} 件 / 対戦カード {len(fills)} 通り\n")
    tot: dict = defaultdict(lambda: defaultdict(int))
    for path in sorted((ROOT / "out/json").glob("*.json")):
        meta = file_meta(path.stem)
        if meta is None:
            continue
        r = json.loads(path.read_text(encoding="utf-8"))
        for p in r["pages"]:
            for k, v in apply_fills(meta, p["matches"], normalize).items():
                tot[(meta["year"], meta["series"])][k] += v
    head = f'{"年度":6}{"大会":8}{"埋まる":>7}{"候補割れ":>9}{"赤線と矛盾":>11}{"出典に無し":>11}'
    print(head)
    print("-" * 54)
    g = defaultdict(int)
    for (y, s), v in sorted(tot.items()):
        if not any(v.values()):
            continue
        print(f'{y:6}{s:8}{v["filled"]:7}{v["ambiguous"]:9}{v["conflict"]:11}{v["missing"]:11}')
        for k, n in v.items():
            g[k] += n
    print("-" * 54)
    print(f'{"合計":14}{g["filled"]:7}{g["ambiguous"]:9}{g["conflict"]:11}{g["missing"]:11}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
