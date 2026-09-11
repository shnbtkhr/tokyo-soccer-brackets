"""地区リーグの結果ページの一覧を1つにまとめる。

data/leagues/sources_parts/d1〜d8.csv（地区ごとに URL を開いて確かめた結果）を、
data/leagues/sources.csv（全件）と data/leagues/sources.md（AI・Notebook 用の要約）にまとめる。
元の候補は ChatGPT の調査（docs/district_sources_chatgpt_20260911.md）。Gemini の結果が届いたら同じ形で足す。
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
PARTS = ROOT / "data/leagues/sources_parts"
COLS = ["地区", "リーグ名", "年度", "部・ブロック", "結果ページのURL", "順位表ページのURL", "形式", "goalnote_tid", "チームの区別", "状態", "根拠のURL", "メモ",
        "Claude確認", "確認メモ", "チーム数", "チーム例", "取得方法"]


def canon(row: dict) -> str:
    """地区ごとの担当で書き方が少し違うので、「Claude確認」をそろえる（はみ出た説明は確認メモへ回す）。"""
    v = row["Claude確認"].replace("(", "（").replace(")", "）")
    for head in ("確認済み（ChatGPTの記載どおり）", "確認済み（Geminiの記載どおり）", "ChatGPTの記載と違う", "Geminiの記載と違う", "開けない", "新たに発見", "未発見"):
        if v.startswith(head):
            extra = v[len(head):].strip("（）")
            if extra:
                row["確認メモ"] = f"{extra}。{row['確認メモ']}".strip("。") if row["確認メモ"] else extra
            return head
    return v


def main() -> int:
    rows = []
    for p in sorted(PARTS.glob("d*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                row = {c: (r.get(c) or "").strip() for c in COLS}
                row["Claude確認"] = canon(row)
                rows.append(row)
    rows.sort(key=lambda r: (r["地区"], r["年度"], r["部・ブロック"]))
    with (ROOT / "data/leagues/sources.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    c = Counter(r["Claude確認"] for r in rows)
    md = ["# 東京都 高校サッカー 地区リーグの結果ページ一覧（2024〜2026年度）", "",
          "ChatGPT の調査結果（docs/district_sources_chatgpt_20260911.md）を、Claude Code のサブエージェントが1件ずつ開いて確かめたもの（2026-09-11）。",
          "全件は data/leagues/sources.csv。「Claude確認」の列が確かめた結果。", "",
          "確かめた結果: " + "、".join(f"{k or '（空）'} {v}" for k, v in c.most_common()), ""]
    for d in sorted({r["地区"] for r in rows}):
        md += [f"## {d}", "", "| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |", "|---|---|---|---|---|---|---|---|"]
        for r in [r for r in rows if r["地区"] == d]:
            md.append(f"| {r['年度']} | {r['リーグ名']} {r['部・ブロック']} | {r['状態']} | {r['Claude確認']} | {r['結果ページのURL']} | {r['順位表ページのURL']} | {r['形式']} | {(r['確認メモ'] or r['メモ'])[:120]} |")
        md.append("")
    (ROOT / "data/leagues/sources.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{len(rows)} 行 → data/leagues/sources.csv・sources.md", dict(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
