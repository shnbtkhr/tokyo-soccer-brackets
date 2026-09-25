"""リーグ戦がどこまで取れていて、どこが取れていないかを一覧にする。

点数（Elo）はリーグ戦を混ぜて計算するので、取れている量が地区で偏っていると、
量の少ない地区の学校は点数が動きにくくなる。誌面に「この学校は記録が少ない」と
断るために、地区ごと・年度ごとの取れ高と、取れなかった理由をまとめる。

出どころは3つある。役割が違うので分けて数える。
  地区コレクタ  districts/dN.py が集めた地区リーグ（2024〜2026年度）
  星取表        早大学院が公開している PDF（2008〜2026年度・同校が入っている組だけ）
  Tリーグ       公式・アーカイブ・高校サッカードットコム

  uv run python league_coverage.py

出力: data/leagues/coverage.md（誌面と申し送り用）
"""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from build_outputs import normalize
from leagues import load_all

ROOT = Path(__file__).parent
OUT = ROOT / "data/leagues/coverage.md"


def rows(name: str) -> list[dict]:
    p = ROOT / "data/leagues" / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> int:
    areas = {normalize(k): v for k, v in
             json.loads((ROOT / "out/scout/member_areas.json").read_text(encoding="utf-8")).items()}
    lg = load_all()

    # 学校ごとのリーグ戦数（トップチームのみ）を、出どころ別に数える
    per_school: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in lg:
        for school, squad in ((r["ホーム学校"], r["ホーム区分"]), (r["アウェイ学校"], r["アウェイ区分"])):
            if school and squad in ("", "A"):
                per_school[school][r["出どころ"]] += 1

    by_district: dict[int, list[str]] = collections.defaultdict(list)
    for k, v in areas.items():
        by_district[v["area"]].append(k)

    lines = ["# リーグ戦の取れ高", "",
             "`league_coverage.py` が作る。点数は大会の結果にリーグ戦を足して計算するため、",
             "リーグ戦の取れている量が少ない学校は点数が動きにくい。", "",
             "## 地区ごと（加盟校のトップチームのみ）", "",
             "| 地区 | 校数 | 1校あたり | 0件の学校 | 地区コレクタ | 星取表 | Tリーグ |",
             "|---|---|---|---|---|---|---|"]
    kinds = ("goalnote", "Tリーグ公式", "星取表", "Tリーグ過去", "プリンス")
    for d in sorted(by_district):
        ks = by_district[d]
        tot = collections.Counter()
        zero = 0
        for k in ks:
            c = per_school.get(k, collections.Counter())
            tot += c
            zero += not sum(c.values())
        n = sum(tot.values())
        coll = tot["goalnote"]
        star = tot["星取表"]
        tl = tot["Tリーグ公式"] + tot["Tリーグ過去"] + tot["プリンス"]
        lines.append(f"| 第{d}地区 | {len(ks)} | {n / len(ks):.1f} | {zero}校 "
                     f"({zero / len(ks) * 100:.0f}%) | {coll} | {star} | {tl} |")

    # 出どころ別の年度の幅
    lines += ["", "## 出どころごとの年度の幅", "",
              "| 出どころ | 年度 | 試合 | 備考 |", "|---|---|---|---|"]
    for kind in kinds:
        ms = [r for r in lg if r["出どころ"] == kind]
        if not ms:
            continue
        ys = sorted({r["年度"] for r in ms})
        note = {"星取表": "早大学院が入っている組だけ。他の組は記録が残っていない",
                "goalnote": "地区コレクタ（districts/dN.py）が集めた分",
                "Tリーグ公式": "今季のみ", "Tリーグ過去": "アーカイブと高校サッカードットコム",
                "プリンス": "関東1部のみ"}.get(kind, "")
        lines.append(f"| {kind} | {ys[0]}〜{ys[-1]} | {len(ms)} | {note} |")

    # 地区コレクタが年度ごとにどれだけ取れているか
    dm = rows("district_matches.csv")
    got = collections.Counter((r["地区"], r["年度"]) for r in dm if r.get("実施") == "済")
    lines += ["", "## 地区コレクタの年度ごとの取れ高", "",
              "| 地区 | 2024 | 2025 | 2026 |", "|---|---|---|---|"]
    for d in range(1, 9):
        key = f"第{d}地区"
        cells = " | ".join(str(got.get((key, str(y)), 0) or "—") for y in (2024, 2025, 2026))
        lines.append(f"| {key} | {cells} |")

    # sources.csv から、確認できていないものを拾う
    src = rows("sources.csv")
    stuck = [r for r in src if r["状態"] != "確認済み"]
    lines += ["", "## 取れていないもの（sources.csv の「未発見」「一部確認」）", "",
              f"全 {len(src)} 件のうち {len(stuck)} 件。", "",
              "| 地区 | 年度 | 部 | 状態 | 分かっていること |", "|---|---|---|---|---|"]
    for r in sorted(stuck, key=lambda r: (r["地区"], r["年度"], r["部・ブロック"])):
        memo = (r["メモ"] or "").replace("|", "／")[:78]
        lines.append(f"| {r['地区']} | {r['年度']} | {r['部・ブロック']} | {r['状態']} | {memo} |")

    lines += ["", "## 分かっている限界", "",
              "- **星取表は早大学院が入っている組しか残っていない。** 第5地区の取れ高が突出しているのは"
              "同校が第5地区で、同じ組の相手校がまとめて入るため。他地区の2008〜2023年度は、"
              "この経路では埋まらない",
              "- **地区コレクタは2024年度より前を持っていない。** 各リーグのサイトが過去ページを"
              "残していないため（第7地区だけは2024・2025年度の最終順位が残っているが、"
              "試合ごとの結果は載っていない）",
              "- **第8地区は結果が JavaScript で描かれるページが多く、本文を取れていない。**"
              "いま入っているのは電大高の部活動ページから拾えた分だけ",
              "",
              "### 第8地区（Player!）を調べた結果 — 2026-09-25",
              "",
              "`web.playerapp.tokyo/competition/{id}`（14485=2024年度1部・16069=2025年度2部・"
              "16071=2025年度3部）は、スクリプトだけでは中身を取れない。次の4つを確かめた。",
              "",
              "1. `api.ookami.me` の素直な形（`/v1/competitions/{id}` など4通り）は全部 404",
              "2. ページの HTML は 41KB あるが、本文は 208 文字しかない。"
              "`window.__INITIAL_STATE__`・`__NEXT_DATA__` の類も無く、完全に描画してから中身が入る",
              "3. 埋め込みの JSON-LD はパンくずだけで、試合結果は入っていない",
              "4. 配信されている JS（client 113KB・chunk 3.5KB/48KB・vendors 318KB）を"
              "URL らしき文字列で検索したが、API の行き先が1つも出てこない。実行時に組み立てている",
              "",
              "取るならブラウザを動かす経路（Playwright で1回だけ開いて通信を覗き、"
              "その行き先をスクリプトに渡す）しかない。**同じ4つを繰り返さないこと。**",
              "- junior-soccer.jp の東京のリーグ索引（2,558件）を全部見たが、高校の地区リーグは"
              "8件しか登録されていない。この経路はこれ以上伸びない",
              ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:26]))
    print(f"...\n→ {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
