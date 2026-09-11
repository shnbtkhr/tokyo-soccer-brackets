"""チーム視点のスカウティングページ（HTML）および AIスカウトプロンプトを作る。

入力:
- out/scout/<チーム>_<大会>.json（analyze_team.py の出力）
- out/teams.csv（大会段階ごとの最終到達）
- scout/<ブロック>.json（日程・会場・公開情報。手で管理する）
出力:
- out/scout/<チーム_slug>.html（scout_template.html にデータを埋め込んだもの）
- out/scout/<チーム_slug>_scout_prompt.md（LLMスカウトプロンプト。--export-prompt 指定時）
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from analyze_team import win_prob
from build_outputs import normalize

ROOT = Path(__file__).parent


def generate_prompt_markdown(data: dict) -> str:
    me = data["me"]
    block_label = data["blockLabel"]
    teams_data = data["teams"]
    me_info = teams_data.get(me, {})

    lines = [
        f"# 【AIスカウティング分析指示書】{block_label} - {me}視点",
        "",
        "## システムロール",
        "あなたは高校サッカー戦術アナリストおよびスカウティングコーチです。",
        "以下の構造化データに基づき、指導者および選手向けに「対戦相手分析・警戒ポイント・戦術的対策」をわかりやすくまとめてください。",
        "",
        f"## 1. 自チーム情報 ({me})",
        f"- Eloレーティング: {me_info.get('elo')} (東京都順位: {me_info.get('eloRank', 'N/A')}位)",
        f"- 山（ブロック）優勝確率: {me_info.get('blockWin', 0) * 100:.1f}%",
        "",
        "## 2. 山の対戦校・ライバル比較",
    ]

    for k, t in teams_data.items():
        if k == me:
            continue
        lines.append(f"### ■ {t.get('display', k)}")
        lines.append(f"- Elo: {t.get('elo')} (都順位: {t.get('eloRank', 'N/A')}位)")
        lines.append(
            f"- {me}との直接対決予想勝率 (vsMe): {t.get('vsMe', 0) * 100:.1f}% (対戦可能性: {t.get('meetProb', 0) * 100:.1f}%)"
        )

        info = t.get("info", {})
        if info.get("summary"):
            lines.append(f"- チーム特徴概要: {info['summary']}")

        style = t.get("style", {})
        if style and style.get("points"):
            lines.append("- 戦術・スタイルの強み:")
            for p in style["points"]:
                lines.append(f"  * {p}")
        lines.append("")

    lines.extend(
        [
            "## 3. 分析・アウトプット作成要求",
            "1. **対戦相手優先警戒リスト**: 当たる可能性が高く、脅威となる相手Top2のピックアップと理由",
            "2. **局面別対策**: セットプレー（ロングスロー含む）、相手のキーマン・ビルドアップへのハーフウェーラインでのプレッシング設計",
            "3. **選手向けメンタル＆試合運びアドバイス**: 先制された場合・競り合い（PK戦）での留意点",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="スカウティングHTMLおよびAIプロンプトを生成"
    )
    ap.add_argument(
        "--team", "-t", default="武蔵丘", help="主視点となるチーム名 (例: 武蔵丘)"
    )
    ap.add_argument(
        "--block-config",
        "-b",
        type=Path,
        default=ROOT / "scout/sen2026_block10.json",
        help="ブロック定義JSON",
    )
    ap.add_argument(
        "--out",
        "-o",
        type=Path,
        default=None,
        help="出力HTMLパス (省略時は out/scout/<チーム_slug>.html)",
    )
    ap.add_argument(
        "--export-prompt",
        action="store_true",
        help="AI分析指示書Markdownを同時に書き出す",
    )
    args = ap.parse_args()

    me = normalize(args.team)
    manual = json.loads(args.block_config.read_text(encoding="utf-8"))

    # analyze_team の出力を参照（存在しない場合は手動データ等から基本構造を作成）
    json_path = ROOT / "out/scout/musashigaoka_sen2026.json"
    if not json_path.exists():
        json_path = ROOT / "out/scout/musashigaoka_sen2026.json"

    a = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    leagues_path = ROOT / "out/scout/leagues_2026.json"
    leagues = (
        json.loads(leagues_path.read_text(encoding="utf-8"))
        if leagues_path.exists()
        else {}
    )
    areas_path = ROOT / "out/scout/member_areas.json"
    areas = json.loads(areas_path.read_text(encoding="utf-8")) if areas_path.exists() else {}

    block = a.get("block", list(manual.get("slots", {}).keys()))
    stages = {k: [] for k in block}

    teams_csv = ROOT / "out/teams.csv"
    if teams_csv.exists():
        for t in csv.DictReader(teams_csv.open(encoding="utf-8-sig")):
            k = t["学校_正規化"]
            if k in stages:
                stages[k].append(
                    {
                        "year": int(t["年度"]),
                        "series": t["大会"],
                        "stage": t["段階"]
                        + (" " + t["地区・支部"] if t["地区・支部"] else ""),
                        "reach": t["最終到達"],
                        "record": f"{t['勝']}勝 {t['PK勝']}PK勝 {t['PK負']}PK負 {t['敗']}敗",
                        "path": t["戦績"],
                    }
                )
    order = {"関東": 0, "総体": 1, "選手権": 2, "新人戦": 3}
    for k in stages:
        stages[k].sort(
            key=lambda s: (-s["year"], order.get(s["series"], 9), s["stage"])
        )

    elo = {k: a.get("teams", {}).get(k, {}).get("elo", 1500) for k in block}
    decided_list = a.get("decided", manual.get("decided", []))

    alive = {k: True for k in block}
    for d in decided_list:
        for t in d.get("teams", [d.get("a"), d.get("b")]):
            if t and t != d.get("winner"):
                alive[t] = False

    def p(x, y):
        return win_prob(elo[x], elo[y])

    b = block
    r1 = {
        b[0]: p(b[0], b[1]),
        b[1]: p(b[1], b[0]),
        b[2]: p(b[2], b[3]),
        b[3]: p(b[3], b[2]),
    }
    for i in (4, 6):
        x, y = b[i], b[i + 1]
        r1[x], r1[y] = (1.0 if alive[x] else 0.0), (1.0 if alive[y] else 0.0)
        if alive[x] and alive[y]:
            r1[x], r1[y] = p(x, y), p(y, x)
    meet = {}
    my_r1 = r1.get(me, 0.5)

    # 相手の位置に応じた対戦確率計算
    if me in (b[2], b[3]):
        opp_r1 = b[3] if me == b[2] else b[2]
        meet[opp_r1] = 1.0
    for o in (b[0], b[1]):
        meet[o] = my_r1 * r1.get(o, 0.5)

    my_r2 = my_r1 * sum(r1.get(o, 0.5) * p(me, o) for o in (b[0], b[1]) if o in elo)
    r2_right = {}
    for o in b[4:]:
        other = [q for q in b[4:] if q != o and (b.index(q) // 2) != (b.index(o) // 2)]
        r2_right[o] = r1.get(o, 0.5) * sum(
            r1.get(q, 0.5) * p(o, q) for q in other if q in elo
        )
    for o in b[4:]:
        meet[o] = my_r2 * r2_right.get(o, 0.5)

    data = {
        "me": me,
        "block": block,
        "asOf": manual.get("asOf", ""),
        "blockLabel": manual.get("blockLabel", ""),
        "schedule": manual.get("schedule", []),
        "slots": manual.get("slots", {}),
        "decided": manual.get("decided", []),
        "teams": {
            k: {
                **{
                    f: a.get("teams", {}).get(k, {}).get(f)
                    for f in (
                        "elo",
                        "eloRank",
                        "eloHistory",
                        "summary",
                        "bySeries",
                        "recent",
                        "games",
                        "names",
                    )
                    if a.get("teams", {}).get(k)
                },
                "display": manual.get("display", {}).get(k, k),
                "alive": alive.get(k, True),
                "blockWin": a.get("blockWinProb", {}).get(k, 0.0),
                "vsMe": a.get("comparisons", {}).get(k, {}).get("winProb"),
                "meetProb": round(meet.get(k, 0.0), 3) if k != me else None,
                "headToHead": a.get("comparisons", {}).get(k, {}).get("headToHead", []),
                "common": a.get("comparisons", {}).get(k, {}).get("common", []),
                "stages": stages.get(k, []),
                "info": manual.get("info", {}).get(k, {}),
                "leagues": leagues.get(k, []),
                "area": areas.get(k),
                "style": manual.get("style", {}).get(k),
            }
            for k in block
        },
        "nTeamsRated": a.get("nTeamsRated", 0),
        "ratingsTop": a.get("ratingsTop", [])[:30],
        "method": manual.get("method", []),
        "styleNone": manual.get("styleNone", ""),
        "formNote": manual.get("formNote", []),
        "pyramid": manual.get("pyramid", []),
        "pyramidNote": manual.get("pyramidNote", ""),
    }

    html = (ROOT / "scout/scout_template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))

    out_path = args.out
    if out_path is None:
        slug = "musashigaoka" if me == "武蔵丘" else normalize(me).lower()
        out_path = ROOT / f"out/scout/{slug}.html"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size // 1024} KB)")

    if args.export_prompt:
        prompt_md = generate_prompt_markdown(data)
        prompt_path = out_path.parent / f"{out_path.stem}_scout_prompt.md"
        prompt_path.write_text(prompt_md, encoding="utf-8")
        print(f"wrote {prompt_path} ({prompt_path.stat().st_size // 1024} KB)")

    for k in block:
        print(
            k,
            "meet",
            data["teams"][k]["meetProb"],
            "vsMe",
            data["teams"][k]["vsMe"],
            "blockWin",
            data["teams"][k]["blockWin"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
