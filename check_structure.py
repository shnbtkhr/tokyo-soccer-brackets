"""parse_bracket.py の出力（out/json/*.json）を構造的に点検する。

木ごとに次を確かめる。
- 試合数 = 葉の数 - 1（トーナメントの木なら必ず成り立つ）
- 勝者が決まっていない試合（未実施または赤線の読み落とし）
- スコアと勝者の矛盾（3-0 で負けている等）
- スコアを拾えなかった試合
- 学校名が空、または学校名らしくない葉
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

NAME_OK = re.compile(r"[぀-ヿ一-鿿]")


def check_file(path: Path) -> list[str]:
    r = json.loads(path.read_text(encoding="utf-8"))
    issues = []
    for p in r["pages"]:
        ms = p["matches"]
        trees = Counter(m["tree"] for m in ms)
        for t, n in sorted(trees.items()):
            if t < 0:
                continue
            tm = [m for m in ms if m["tree"] == t]
            nleaf = sum(("leaf" in m["slot1"]) + ("leaf" in m["slot2"]) for m in tm)
            root = [m for m in tm if m["parent"] is None][0]
            tag = f"{r['file']} p{p['page']} t{t}"
            if n != nleaf - 1:
                issues.append(f"{tag}: 試合数{n} != 葉{nleaf}-1")
            for m in tm:
                where = f"{tag} c{m['col']} {m['team1']} vs {m['team2']}"
                for k in (1, 2):
                    s = m[f"slot{k}"]
                    if "leaf" in s and not NAME_OK.search(s["leaf"] or ""):
                        issues.append(f"{where}: 葉{k}の名前が不正 {s['leaf']!r}")
                if m["winner_slot"] is None:
                    # 赤もスコアも無ければ未実施（開催中の大会）。どちらかがあれば読み落とし
                    if max(m["red"]) > 0.05 or m["score1"] is not None or m["score2"] is not None:
                        issues.append(f"{where}: 勝者未確定 red={m['red']} score={m['score1']}-{m['score2']}")
                    continue
                s1, s2 = m["score1"], m["score2"]
                walkover = any("不戦" in x or "棄権" in x for x in m["notes"])
                if s1 is None or s2 is None:
                    if not walkover:
                        issues.append(f"{where}: スコア欠落 {s1}-{s2} notes={m['notes']}")
                    continue
                k1 = (s1, m["pk1"] if m["pk1"] is not None else -1)
                k2 = (s2, m["pk2"] if m["pk2"] is not None else -1)
                if k1 == k2:
                    issues.append(f"{where}: 同点で決着不明 {s1}-{s2} pk={m['pk1']}-{m['pk2']}")
                elif (k1 > k2) != (m["winner_slot"] == 1):
                    issues.append(f"{where}: スコアと勝者が矛盾 {s1}-{s2} pk={m['pk1']}-{m['pk2']} 勝者slot{m['winner_slot']}")
                # 前後半が書かれていれば、合計が本スコアと合うか検算する（延長があれば4段、前後半だけなら2段）
                halves = [h.split("-") for h in m["halves"] if re.fullmatch(r"\d+-\d+", h)]
                if len(halves) in (2, 4) and len(halves) == len(m["halves"]):
                    t1 = sum(int(a) for a, _ in halves)
                    t2 = sum(int(b) for _, b in halves)
                    if (t1, t2) != (s1, s2):
                        issues.append(f"{where}: 前後半の合計{t1}-{t2}が本スコア{s1}-{s2}と合わない {m['halves']}")
                extra = [x for x in m["notes"] if x.startswith(("extra:", "text:"))]
                if extra:
                    issues.append(f"{where}: 余分な文字 {extra}")
            _ = root
    return issues


def main() -> int:
    files = sorted(Path(sys.argv[1] if len(sys.argv) > 1 else "out/json").glob("*.json"))
    total = 0
    for f in files:
        iss = check_file(f)
        r = json.loads(f.read_text(encoding="utf-8"))
        nm = sum(len(p["matches"]) for p in r["pages"])
        nt = sum(len({m["tree"] for m in p["matches"]}) for p in r["pages"])
        print(f"{f.stem:24s} matches={nm:4d} trees={nt:3d} issues={len(iss)}")
        for i in iss:
            print("    " + i)
        total += len(iss)
    print(f"TOTAL issues: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
