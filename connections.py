"""対戦のつながり（直接対戦・共通の相手・相手の相手）を全部数え上げる。

2校が直接戦っていなくても、「武蔵丘 → A → B → 相手」のように試合でつながっていることがある。
人が目で追うと見逃すので、ここで機械的にすべて列挙し、読みやすいものを上に並べる。

つながり1本の読み方:
- 各試合の得点差（左の学校から見た値。PK戦は 0、1試合 ±5 で頭打ち）を足したものを
  「武蔵丘が相手よりどれくらい上か」の目安とする（例: +2 −1 +2 → +3）
- 重み = 新しさ（1年さかのぼるごとに ×0.7）× 段数（直接 1.0、2段 0.5、3段 0.25）
  3段のつながりはどちらの向きの試合でもよい

サッカーでは「A>B かつ B>C なら A>C」は成り立たないことが多い。弱い手がかりとして扱う。

入力: out/matches.csv
出力: data/connections/<チーム>_<年度>.csv（全件）・.md（要約と上位）・.json（サイト用）
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from build_outputs import normalize

ROOT = Path(__file__).parent
DECAY, CAP = 0.7, 5
HOP_W = {1: 1.0, 2: 0.5, 3: 0.25}


def load(season: int) -> tuple[dict, dict]:
    adj: dict[str, list] = defaultdict(list)
    disp: dict[str, str] = {}
    for r in csv.DictReader((ROOT / "out/matches.csv").open(encoding="utf-8-sig")):
        if r["得点A"] == "" or r["得点B"] == "" or r["状態"] == "不戦勝・棄権":
            continue
        a, b = normalize(r["チームA"]), normalize(r["チームB"])
        if not a or not b or a == b:
            continue
        disp.setdefault(a, r["チームA"])
        disp.setdefault(b, r["チームB"])
        ga, gb = int(r["得点A"]), int(r["得点B"])
        pk = r["PK_A"] != "" and r["PK_B"] != ""
        m = {
            "year": int(r["年度"]), "series": r["大会"], "stage": r["段階"] + (" " + r["地区・支部"] if r["地区・支部"] else ""),
            "round": r["ラウンド"], "a": a, "b": b, "ga": ga, "gb": gb, "pk": f"{r['PK_A']}-{r['PK_B']}" if pk else "",
            "winner": normalize(r["勝者"]) if r["勝者"] else "", "src": r["出典PDF"],
        }
        adj[a].append((b, m))
        adj[b].append((a, m))
    return adj, disp


def view(m: dict, left: str) -> dict:
    """left の学校から見た1試合。"""
    lf = m["a"] == left
    gf, ga = (m["ga"], m["gb"]) if lf else (m["gb"], m["ga"])
    pk = m["pk"]
    if pk and not lf:
        x, y = pk.split("-")
        pk = f"{y}-{x}"
    if m["winner"] == left:
        res = "PK勝" if pk else "勝"
    elif m["winner"]:
        res = "PK負" if pk else "負"
    else:
        res = "分"
    d = 0 if pk else max(-CAP, min(CAP, gf - ga))
    return {"year": m["year"], "series": m["series"], "stage": m["stage"], "round": m["round"], "gf": gf, "ga": ga, "pk": pk, "res": res, "d": d, "src": m["src"]}


def chains(adj: dict, me: str, opp: str, season: int) -> list[dict]:
    out = []
    def add(path: list[str], ms: list[dict]) -> None:
        legs = [view(m, path[i]) for i, m in enumerate(ms)]
        w = HOP_W[len(ms)] * min(1.0, 1.0)
        for lg in legs:
            w *= DECAY ** max(0, season - lg["year"])
        out.append({"path": path, "legs": legs, "implied": sum(lg["d"] for lg in legs), "w": round(w, 4), "hops": len(ms), "latest": max(lg["year"] for lg in legs)})

    for x, m in adj[me]:
        if x == opp:
            add([me, opp], [m])
    by_me = defaultdict(list)
    for x, m in adj[me]:
        if x != opp:
            by_me[x].append(m)
    by_opp = defaultdict(list)
    for y, m in adj[opp]:
        if y != me:
            by_opp[y].append(m)
    for x in set(by_me) & set(by_opp):
        for m1 in by_me[x]:
            for m2 in by_opp[x]:
                add([me, x, opp], [m1, m2])
    for x, m1s in by_me.items():
        if x in by_opp:
            pass  # 2段で数えたものも、3段の中継点としては使う
        for y, m2 in adj[x]:
            if y in (me, opp) or y not in by_opp:
                continue
            for m1 in m1s:
                for m3 in by_opp[y]:
                    add([me, x, y, opp], [m1, m2, m3])
    return out


def summarize(cs: list[dict]) -> dict:
    tw = sum(c["w"] for c in cs)
    return {
        "n": len(cs), "direct": sum(c["hops"] == 1 for c in cs), "two": sum(c["hops"] == 2 for c in cs), "three": sum(c["hops"] == 3 for c in cs),
        "up": sum(c["implied"] > 0 for c in cs), "down": sum(c["implied"] < 0 for c in cs), "even": sum(c["implied"] == 0 for c in cs),
        "weighted": round(sum(c["w"] * c["implied"] for c in cs) / tw, 2) if tw else None, "weight": round(tw, 3),
    }


def pick(cs: list[dict], n: int = 8) -> list[dict]:
    """読む価値の高い順: 重み（新しさ・短さ）を主に、同じ中継校の重複を避けて選ぶ。"""
    seen, out = set(), []
    for c in sorted(cs, key=lambda c: (-c["w"], -abs(c["implied"]))):
        key = tuple(c["path"][1:-1])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= n:
            break
    return out


def leg_text(disp: dict, a: str, b: str, lg: dict) -> str:
    mark = {"勝": "○", "PK勝": "○", "負": "×", "PK負": "×", "分": "△"}[lg["res"]]
    pk = f" PK{lg['res'][2:] if lg['res'].startswith('PK') else ''} {lg['pk']}" if lg["pk"] else ""
    return f"{disp.get(a, a)} {mark} {lg['gf']}-{lg['ga']}{pk} {disp.get(b, b)}（{lg['year']} {lg['series']} {lg['round']}）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="武蔵丘")
    ap.add_argument("--opps", nargs="+", default=["昭和第一", "学習院", "板橋有徳", "城東", "東村山"])
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()
    adj, disp = load(args.season)
    out_dir = ROOT / "data/connections"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.me}_{args.season}"
    site, md = {}, [
        f"# 対戦のつながり — {disp.get(args.me, args.me)} と山の相手（{args.season}年度 選手権1次予選）", "",
        "高体連のトーナメント表から読み取った公式戦（2022〜2026年度）で、武蔵丘と各相手が試合でどうつながっているかを全部数え上げた結果。",
        "", "- つながり1本の「目安」= 各試合の得点差（左の学校から見た値。PK戦は0、1試合±5で頭打ち）の合計。プラスなら武蔵丘が上とみる",
        f"- 重み = 新しさ（1年さかのぼるごとに×{DECAY}）× 段数（直接1.0・2段0.5・3段0.25）。「重みつき平均」はこの重みで目安を平均したもの",
        "- サッカーでは「AがBに勝ち、BがCに勝った」から「AはCより強い」とは言えない。弱い手がかりとして扱うこと",
        "- 作成: connections.py（Claude Code, 2026-09-11）。強さの点数（docs/strength_rating.md）とは別の見方", "",
    ]
    with (out_dir / f"{stem}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["相手", "段数", "目安の得点差", "重み", "経路", "試合1", "試合2", "試合3"])
        for opp in args.opps:
            cs = chains(adj, args.me, opp, args.season)
            sm = summarize(cs)
            top = pick(cs)
            for c in sorted(cs, key=lambda c: -c["w"]):
                legs = [leg_text(disp, c["path"][i], c["path"][i + 1], lg) for i, lg in enumerate(c["legs"])]
                w.writerow([disp.get(opp, opp), c["hops"], c["implied"], c["w"], " → ".join(disp.get(p, p) for p in c["path"]), *legs, *[""] * (3 - len(legs))])
            site[opp] = {"summary": sm, "top": [{"path": [disp.get(p, p) for p in c["path"]], "legs": c["legs"], "implied": c["implied"], "w": c["w"], "hops": c["hops"]} for c in top]}
            md += [f"## {disp.get(opp, opp)}", "",
                   f"- つながり {sm['n']} 本（直接 {sm['direct']}・2段 {sm['two']}・3段 {sm['three']}）",
                   f"- 武蔵丘が上とみるもの {sm['up']} 本、下とみるもの {sm['down']} 本、互角 {sm['even']} 本",
                   f"- 重みつき平均の目安: {sm['weighted']:+.2f} 点差" if sm["weighted"] is not None else "- 重みつき平均の目安: なし", "",
                   "重みの大きい順（中継校が重複しないもの）:", ""]
            for c in top:
                legs = [leg_text(disp, c["path"][i], c["path"][i + 1], lg) for i, lg in enumerate(c["legs"])]
                md.append(f"- 目安 {c['implied']:+d}（重み {c['w']}）: " + " ／ ".join(legs))
            md.append("")
            print(f"{opp}: {sm}")
    (out_dir / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / f"{stem}.json").write_text(json.dumps(site, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
