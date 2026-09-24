"""リーグ戦のデータを1つの形にそろえて読む。

出どころが5つあり、列の名前も粒度もばらばらなので、ここで揃える。
どれも「1行1試合・結果の入ったものだけ」にして返す。

| ファイル | 中身 | 日付 |
|---|---|---|
| `district_stars_matches.csv` | 地区トップリーグ・NSリーグ・Tリーグ・ユニティリーグ 2008〜2026年度（星取表） | 無し |
| `district_matches.csv` | 第5地区 NSリーグ 2024〜2026年度（goalnote） | 有り |
| `tleague_matches.csv` | T リーグ 今季（公式） | 有り |
| `tleague_archive_matches.csv` | T リーグ 2018〜2024年度（アーカイブの日程 PDF） | 有り |
| `tleague_history_matches.csv` | T リーグ 2014〜2020年度（高校サッカードットコム） | 有り |

同じ試合が複数の出どころに出る。年度・対戦・スコアが同じものを同じ試合とみなし、
**足し合わせずに、いちばん多く持っている出どころの数に合わせる**（2回戦制で同じ
スコアの試合が2つある場合を潰さないため）。日付のある行を先に採る。

  uv run python leagues.py --team 武蔵丘
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
DIR = ROOT / "data/leagues"


def _rows(name: str) -> list[dict]:
    p = DIR / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _num(v) -> int | None:
    v = str(v or "").strip()
    return int(v) if v.lstrip("-").isdigit() else None


def _mk(year, league, div, date, h, hd, a, ad, gh, ga, src, kind) -> dict | None:
    gh, ga = _num(gh), _num(ga)
    if gh is None or ga is None or not h or not a or h == a:
        return None
    # 「2部Aブロック」と「2部A」は出どころ違いの同じ区分。表記をそろえる
    div = re.sub(r"ブロック$", "", str(div or "").strip())
    return {"年度": str(year), "リーグ": league, "区分": div, "日付": (date or "").strip()[:10],
            "ホーム学校": h, "ホーム区分": (hd or "").strip(), "アウェイ学校": a, "アウェイ区分": (ad or "").strip(),
            "得点H": gh, "得点A": ga, "出典": src, "出どころ": kind}


def load_all() -> list[dict]:
    """5つの出どころをそろえ、重なりを整理して返す。"""
    groups: dict[str, list[dict]] = defaultdict(list)

    def add(kind: str, rows: list[dict]) -> None:
        for r in rows:
            if r:
                groups[kind].append(r)

    add("星取表", [_mk(r["年度"], r["リーグ"], r["区分"], "", r["ホーム学校"], r["ホーム区分"],
                     r["アウェイ学校"], r["アウェイ区分"], r["得点H"], r["得点A"], r["出典"], "星取表")
                 for r in _rows("district_stars_matches.csv")])
    add("goalnote", [_mk(r["年度"], r["リーグ"], r["部"], r["日付"], r["ホーム学校"], r["ホーム区分"],
                         r["アウェイ学校"], r["アウェイ区分"], r["ホーム得点"], r["アウェイ得点"], r["出典"], "goalnote")
                     for r in _rows("district_matches.csv") if r.get("実施") == "済"])
    add("Tリーグ公式", [_mk(r["年度"], r["リーグ"], r.get("ブロック", ""), r["日付"], r["ホーム学校"], r.get("ホーム区分", ""),
                        r["アウェイ学校"], r.get("アウェイ区分", ""), r["ホーム得点"], r["アウェイ得点"], r["出典"], "Tリーグ公式")
                    for r in _rows("tleague_matches.csv") if r.get("実施") == "済"])
    add("Tリーグ過去", [_mk(r["年度"], "Tリーグ", r["リーグ"], r["日付"], r["学校H"], "", r["学校A"], "",
                        r["得点H"], r["得点A"], r["出典"], "Tリーグ過去")
                    for r in _rows("tleague_archive_matches.csv")])
    add("Tリーグ過去", [_mk(r["年度"], "Tリーグ", r["リーグ"], r["日時"], r["学校H"], "", r["学校A"], "",
                        r["得点H"], r["得点A"], r["出典"], "Tリーグ過去")
                    for r in _rows("tleague_history_matches.csv")])
    add("プリンス", [_mk(r["年度"], r["リーグ"], "", r["日付"], r["ホーム学校"], "", r["アウェイ学校"], "",
                     r["ホーム得点"], r["アウェイ得点"], r["出典"], "プリンス")
                 for r in _rows("prince_kanto1_2026_matches.csv") if r.get("実施") == "済"])

    def key(r: dict) -> tuple:
        # A・B の別は出どころによって書き方が違う（goalnote は A、星取表は無印）ので鍵に入れない。
        # 同じ学校の別チームが同じスコアで当たった場合は、下の「多いほうに合わせる」が守る
        pair = sorted([(r["ホーム学校"], r["得点H"]), (r["アウェイ学校"], r["得点A"])])
        return (r["年度"], *[x for p in pair for x in p])

    # 出どころごとに（年度・対戦・スコア）の数を数え、いちばん多い出どころの数だけ採る。
    # 日付のある行を先に採るので、同じ試合なら日付つきのほうが残る
    counts: dict[tuple, Counter] = defaultdict(Counter)
    for kind, rows in groups.items():
        for r in rows:
            counts[key(r)][kind] += 1
    order = sorted((r for rows in groups.values() for r in rows),
                   key=lambda r: (not r["日付"], r["出どころ"]))
    used: Counter = Counter()
    out = []
    for r in order:
        k = key(r)
        if used[k] < max(counts[k].values()):
            used[k] += 1
            out.append(r)
    out.sort(key=lambda r: (r["年度"], r["リーグ"], r["日付"]))
    return out


def for_school(rows: list[dict], school: str, squads: tuple[str, ...] = ("", "A")) -> list[dict]:
    """1校ぶんを、自チームから見た形にして返す。

    既定ではトップチーム（無印と A）だけ。B チーム以下は下部のリーグに別枠で出るため、
    混ぜると学校の戦績が実態とずれる。squads=() を渡すと全部返す。
    """
    out = []
    for r in rows:
        home = r["ホーム学校"] == school
        if not home and r["アウェイ学校"] != school:
            continue
        if squads and (r["ホーム区分"] if home else r["アウェイ区分"]) not in squads:
            continue
        gf, ga = (r["得点H"], r["得点A"]) if home else (r["得点A"], r["得点H"])
        out.append({
            "年度": r["年度"], "大会": r["リーグ"], "段階": r["区分"], "ラウンド": "",
            "相手": (r["アウェイ学校"] + r["アウェイ区分"]) if home else (r["ホーム学校"] + r["ホーム区分"]),
            "自": (r["ホーム区分"] if home else r["アウェイ区分"]),
            "結果": "○" if gf > ga else "●" if gf < ga else "△",
            "得点": gf, "失点": ga, "日付": r["日付"], "出どころ": r["出どころ"], "リーグ戦": True,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", default="")
    args = ap.parse_args()

    rows = load_all()
    print(f"リーグ戦 {len(rows)} 試合")
    src = Counter(r["出どころ"] for r in rows)
    print("  出どころ: " + " / ".join(f"{k} {v}" for k, v in src.most_common()))
    by = Counter((r["年度"], r["リーグ"]) for r in rows)
    for k in sorted(by):
        print(f"  {k[0]} {k[1]:20} {by[k]:4}")
    if args.team:
        mine = for_school(rows, args.team)
        w = sum(1 for m in mine if m["結果"] == "○")
        d = sum(1 for m in mine if m["結果"] == "△")
        print(f'\n{args.team}: {len(mine)} 試合  {w}勝 {d}分 {len(mine) - w - d}敗')
        for y in sorted({m["年度"] for m in mine}):
            ms = [m for m in mine if m["年度"] == y]
            ww = sum(1 for m in ms if m["結果"] == "○")
            dd = sum(1 for m in ms if m["結果"] == "△")
            names = " / ".join(sorted({f'{m["大会"]} {m["段階"]}'.strip() for m in ms}))
            print(f'  {y}  {len(ms):2}試合 {ww}勝{dd}分{len(ms) - ww - dd}敗  {names[:46]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
