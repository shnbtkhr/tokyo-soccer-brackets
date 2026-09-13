"""地区リーグ（第1〜8地区）の順位表と試合を、地区ごとの部品（districts/dN.py）から集めてまとめる。

部品の決まりは notes/district_collector_spec.md。部品が無い地区・失敗した地区は飛ばして、何が取れなかったかを表示する。
出力:
- data/leagues/district_standings.csv … 1行 = 1チーム × 部 × 年度
- data/leagues/district_matches.csv   … 1行 = 1試合
- data/leagues/district.md             … AI・Notebook 用（年度・地区・部ごとの順位表）
--refresh を付けると各サイトから取り直す（付けなければ保存済みのページだけで動く）。
"""

from __future__ import annotations

import argparse
import csv
import importlib
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "data/leagues"
S_COLS = ["地区", "リーグ", "年度", "部", "順位", "チーム", "学校", "区分", "勝点", "試合", "勝", "分", "敗", "得点", "失点", "得失点", "出典"]
M_COLS = ["地区", "リーグ", "年度", "部", "節", "日付", "ホーム", "アウェイ", "ホーム得点", "アウェイ得点", "実施", "ホーム学校", "ホーム区分", "アウェイ学校", "アウェイ区分", "出典"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    standings, matches, report = [], [], []
    for n in range(1, 9):
        try:
            mod = importlib.import_module(f"districts.d{n}")
        except ModuleNotFoundError:
            report.append(f"第{n}地区: 部品なし")
            continue
        try:
            s, m = mod.collect(refresh=args.refresh)
        except Exception:  # 1つの地区が失敗しても、ほかは続ける
            report.append(f"第{n}地区: 失敗\n{traceback.format_exc(limit=2)}")
            continue
        standings += s
        matches += m
        report.append(f"第{n}地区: 順位表 {len(s)} 行・試合 {len(m)}（実施済み {sum(x.get('実施') == '済' for x in m)}）")
    key = lambda r: (int(r["年度"]), r["地区"], r["部"], r["順位"] if isinstance(r["順位"], int) else 99)  # noqa: E731
    standings.sort(key=lambda r: (-key(r)[0], *key(r)[1:]))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows, cols in (("district_standings", standings, S_COLS), ("district_matches", matches, M_COLS)):
        with (OUT / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    write_md(standings, matches)
    print("\n".join(report))
    print(f"計: 順位表 {len(standings)} 行・試合 {len(matches)}")
    return 0


def write_md(standings: list, matches: list) -> None:
    c = Counter((r["年度"], r["地区"]) for r in standings)
    md = ["# 東京都 高校サッカー 地区リーグの順位表（collect_districts.py）", "",
          "出典は各地区のリーグのサイト（data/leagues/sources.csv で確かめたもの）。部品の決まりは notes/district_collector_spec.md。",
          "チーム名の末尾の B・C などは控えチーム。出典の末尾に「（試合から計算）」とある部は、順位表が公開されていないため試合結果から計算した。",
          "第8地区は地区全体の結果ページが無く、1校の試合記録だけ（順位表なし）。", "",
          "収録: " + "、".join(f"{y}年度 {d} {n}行" for (y, d), n in sorted(c.items(), key=lambda kv: (-int(kv[0][0]), kv[0][1]))), ""]
    groups: dict = {}
    for r in standings:
        groups.setdefault((r["年度"], r["地区"], r["リーグ"], r["部"]), []).append(r)
    for (y, d, lg, div), rows in groups.items():
        md += [f"## {y}年度 {d} {lg} {div}", "", "| 順位 | チーム | 試合 | 勝点 | 勝 | 分 | 敗 | 得点 | 失点 | 得失点 |", "|---|---|---|---|---|---|---|---|---|---|"]
        md += [f"| {r['順位']} | {r['チーム']} | {r['試合']} | {r['勝点']} | {r['勝']} | {r['分']} | {r['敗']} | {r['得点']} | {r['失点']} | {r['得失点']} |" for r in rows]
        md += [f"出典: {rows[0]['出典']}", ""]
    (OUT / "district.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
