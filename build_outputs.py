"""parse_bracket.py の出力（out/json/*.json）から、配布用の CSV と Gemini Notebook 用の Markdown を作る。

- out/matches.csv  … 1行 = 1試合（全大会）
- out/teams.csv    … 1行 = 1校 × 1大会段階（勝敗の集計と、各試合の結果の並び）
- out/notebook/*.md … 大会系統ごと（総体・選手権・新人戦・関東）に試合一覧と学校別戦績

corrections.csv に、目視で確かめた訂正を置く（自動では取れなかった数か所）。
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pymupdf

ROOT = Path(__file__).parent
BASE_URL = "https://tokyosoccer-u18.com"
SHIBU = {"higashi": "東支部（第1・2地区）", "naka": "中支部（第3・4地区）", "minami": "南支部（第5・6地区）", "nishi": "西支部（第7・8地区）"}
SERIES_TITLE = {
    "総体": "高校総体（インターハイ）東京都予選",
    "選手権": "全国高校サッカー選手権 東京大会",
    "新人戦": "地区新人選手権大会",
    "関東": "関東高校サッカー大会 東京都予選",
}
SERIES_FILE = {"総体": "sotai", "選手権": "senshuken", "新人戦": "shinjin", "関東": "kanto"}


def file_meta(stem: str) -> dict:
    if m := re.fullmatch(r"sotai(\d\d)_(1|2)jt", stem):
        y = 2000 + int(m[1])
        return {"series": "総体", "year": y, "stage": "一次トーナメント" if m[2] == "1" else "二次トーナメント", "area": "", "order": int(m[2]) + 1, "url": f"{BASE_URL}/SOTAI{m[1]}/{stem}.pdf"}
    if m := re.fullmatch(r"(\d\d)sotai_\d*(higashi|naka|minami|nishi)\d*", stem):
        y = 2000 + int(m[1])
        return {"series": "総体", "year": y, "stage": "支部予選", "area": SHIBU[m[2]], "order": 1, "url": f"{BASE_URL}/SOTAI{m[1]}/{stem}.pdf"}
    if m := re.fullmatch(r"sen(\d\d)_(1|2)j", stem):
        y = 2000 + int(m[1])
        return {"series": "選手権", "year": y, "stage": f"第{y - 2022 + 101}回 " + ("一次予選" if m[2] == "1" else "二次予選"), "area": "", "order": int(m[2]), "url": f"{BASE_URL}/SEN{m[1]}/{stem}.pdf"}
    if m := re.fullmatch(r"sinj(\d\d)_(\d)", stem):
        y = 2000 + int(m[1])
        return {"series": "新人戦", "year": y, "stage": "地区大会", "area": f"第{m[2]}地区", "order": int(m[2]), "url": f"{BASE_URL}/SINJ{m[1]}/{stem}.pdf"}
    if stem == "kanto2024":
        return {"series": "関東", "year": 2024, "stage": "東京都予選", "area": "", "order": 1, "url": f"{BASE_URL}/SINJ23/{stem}.pdf"}
    if stem == "2025kanto":
        return {"series": "関東", "year": 2025, "stage": "東京都予選", "area": "", "order": 1, "url": f"{BASE_URL}/SINJ24/{stem}.pdf"}
    raise ValueError(stem)


def normalize(name: str) -> str:
    """名寄せ用のキー。原文は別に残すので、ここでは多少強引に寄せてよい。"""
    s = unicodedata.normalize("NFKC", name or "")
    s = re.sub(r"[(（][^)）]*[)）]", "", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^(東京都立|都立|都・|国立|国・|私立|私・|区立)", "", s)
    s = re.sub(r"^都(?=[^市・])(?=.{2,})", "", s)  # 「都日比谷」。都市大は残す
    s = re.sub(r"(高等学校|高校)$", "", s)
    s = re.sub(r"(?<=[一-龥])ケ(?=[一-龥])", "ヶ", s)
    return s.translate(str.maketrans("國學髙﨑", "国学高崎"))


def load_corrections() -> dict:
    fixes = defaultdict(list)
    path = ROOT / "corrections.csv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                fixes[(row["file"], row["team1"], row["team2"])].append(row)
    return fixes


def apply_corrections(stem: str, matches: list[dict], fixes: dict) -> None:
    for m in matches:
        for fx in fixes.get((stem, m["team1"], m["team2"]), []):
            if fx["field"] in ("score1", "score2", "pk1", "pk2"):
                m[fx["field"]] = int(fx["value"])
            elif fx["field"] == "notes":
                m["notes"] = m["notes"] + [fx["value"]]
            m.setdefault("corrected", []).append(fx["reason"])


def round_names(page: dict, block_mode: bool) -> dict[int, str]:
    ms = page["matches"]
    facing_trees = set()
    for m in ms:
        if m["orient"] == "facing":
            by = {x["id"]: x for x in ms}
            facing_trees.update({by[m["slot1"]["from"]]["tree"], by[m["slot2"]["from"]]["tree"]})
    names = {}
    size = defaultdict(int)
    for m in ms:
        size[m["tree"]] += 1
    big = max(size.values()) if size else 0
    for m in ms:
        if m["orient"] == "facing":
            names[m["id"]] = "決勝"
            continue
        # 大きな山の横にある1試合だけの山は3位決定戦（「3決」とだけ書かれた表や、何も書かれていない表がある）
        if "3位決定戦" in m["notes"] or (not block_mode and size[m["tree"]] == 1 and big > 3):
            names[m["id"]] = "3位決定戦"
            continue
        rfin = m["ncol"] - m["col"] + (1 if m["tree"] in facing_trees else 0)
        if block_mode:
            # 小さな山が並ぶ表（一次予選・支部予選）。山の最後だけ「ブロック決勝」、ほかは回戦で呼ぶ
            names[m["id"]] = "ブロック決勝" if rfin == 0 else f"{m['col']}回戦"
        else:
            names[m["id"]] = {0: "決勝", 1: "準決勝", 2: "準々決勝"}.get(rfin, f"{m['col']}回戦")
    return names


def status_of(m: dict) -> str:
    if any("不戦" in n or "棄権" in n for n in m["notes"]):
        return "不戦勝・棄権"
    if m["winner_slot"] is None:
        return "未実施" if m["score1"] is None and m["score2"] is None else "勝者不明"
    if m["score1"] is None or m["score2"] is None:
        return "スコア記載なし"
    if m.get("winner_source") == "score":
        return "スコアのみ記載（赤線未反映）"
    if m.get("winner_source") == "score_red_both":
        return "赤線が両側（スコアで判定）"
    return "終了"


def score_text(m: dict, for_slot: int = 1) -> str:
    s1, s2 = m["score1"], m["score2"]
    p1, p2 = m["pk1"], m["pk2"]
    if for_slot == 2:
        s1, s2, p1, p2 = s2, s1, p2, p1
    if s1 is None and s2 is None:
        return ""
    t = f"{'' if s1 is None else s1}-{'' if s2 is None else s2}"
    if p1 is not None and p2 is not None:
        t += f" (PK {p1}-{p2})"
    if "延長" in m["notes"] and p1 is None:
        t += " (延長)"
    return t


def build() -> None:
    fixes = load_corrections()
    rows = []
    for path in sorted((ROOT / "out/json").glob("*.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        stem = path.stem
        meta = file_meta(stem)
        pdf_title = pymupdf.open(ROOT / "pdfs" / f"{stem}.pdf").metadata.get("title") or ""
        n_trees = max(len({m["tree"] for m in p["matches"] if m["tree"] >= 0 and "3位決定戦" not in m["notes"]}) for p in r["pages"])
        block_mode = n_trees > 2
        for p in r["pages"]:
            apply_corrections(stem, p["matches"], fixes)
            names = round_names(p, block_mode)
            by = {m["id"]: m for m in p["matches"]}
            tree_label = {}
            for m in p["matches"]:
                if m["parent"] is None and m["orient"] != "facing":
                    lab = (m["root_label"] or "").strip()
                    tree_label[m["tree"]] = lab
            for m in p["matches"]:
                w = m["winner_slot"]
                block = ""
                if m["orient"] != "facing":
                    lab = tree_label.get(m["tree"], "")
                    if meta["series"] == "選手権" and meta["stage"].endswith("二次予選"):
                        block = "Aブロック" if m["tree"] == 0 else "Bブロック"
                    elif block_mode and lab and lab != "3位決定戦" and not re.search(r"[ぁ-ん]", lab) and len(lab) <= 6:
                        block = "→" + unicodedata.normalize("NFKC", lab)
                notes = [n for n in m["notes"] if not n.startswith(("extra:", "text:", "facing")) and not (n == "延長" and m["pk1"] is None)]
                rows.append(
                    {
                        "年度": meta["year"],
                        "大会": meta["series"],
                        "段階": meta["stage"],
                        "地区・支部": meta["area"],
                        "ブロック": block,
                        "ページ": p["page"] + 1,
                        "ラウンド": names[m["id"]],
                        "列": m["col"],
                        "日付": unicodedata.normalize("NFKC", m["date"] or ""),
                        "試合番号": m["match_no"] or "",
                        "チームA": m["team1"] or "",
                        "チームB": m["team2"] or "",
                        "スコア": score_text(m),
                        "得点A": "" if m["score1"] is None else m["score1"],
                        "得点B": "" if m["score2"] is None else m["score2"],
                        "PK_A": "" if m["pk1"] is None else m["pk1"],
                        "PK_B": "" if m["pk2"] is None else m["pk2"],
                        "前後半": " / ".join(m["halves"]),
                        "勝者": (m["team1"] if w == 1 else m["team2"] if w == 2 else "") or "",
                        "状態": status_of(m),
                        "備考": " ".join(notes + (["目視で訂正"] if m.get("corrected") else [])),
                        "チームA_正規化": normalize(m["team1"]),
                        "チームB_正規化": normalize(m["team2"]),
                        "出典PDF": meta["url"],
                        "PDFタイトル": pdf_title,
                        "_order": (meta["series"], meta["year"], meta["order"], meta["area"], p["page"], block if m["orient"] != "facing" else "~", 98 if names[m["id"]] == "3位決定戦" else m["col"] if m["orient"] != "facing" else 99, m["bar"][2] if m["orient"] != "facing" else 9999),
                        "_winner_slot": w,
                    }
                )
    rows.sort(key=lambda r: r["_order"])
    out = ROOT / "out"
    cols = [k for k in rows[0] if not k.startswith("_")]
    with (out / "matches.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    teams = build_teams(rows)
    with (out / "teams.csv").open("w", encoding="utf-8-sig", newline="") as f:
        tc = ["年度", "大会", "段階", "地区・支部", "学校", "学校_正規化", "試合数", "勝", "PK勝", "PK負", "敗", "不戦勝", "最終到達", "戦績"]
        wr = csv.DictWriter(f, fieldnames=tc, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(teams)
    write_markdown(rows, teams, out / "notebook")
    print(f"matches: {len(rows)}  teams: {len(teams)}")


def build_teams(rows: list[dict]) -> list[dict]:
    """学校ごとの勝敗。PK は勝敗と分けて数える（勝率の計算方法を使う側が選べるように）。"""
    acc: dict = {}
    for r in rows:
        if r["状態"] == "未実施":
            continue
        for side, other in (("A", "B"), ("B", "A")):
            name = r[f"チーム{side}"]
            if not name:
                continue
            key = (r["年度"], r["大会"], r["段階"], r["地区・支部"], normalize(name))
            t = acc.setdefault(key, {"年度": r["年度"], "大会": r["大会"], "段階": r["段階"], "地区・支部": r["地区・支部"], "学校": name, "学校_正規化": normalize(name), "試合数": 0, "勝": 0, "PK勝": 0, "PK負": 0, "敗": 0, "不戦勝": 0, "最終到達": "", "_games": [], "_last": None})
            won = r["勝者"] == name
            lost = bool(r["勝者"]) and not won
            pk = r["PK_A"] != "" and r["PK_B"] != ""
            walk = r["状態"] == "不戦勝・棄権"
            if walk and won:
                t["不戦勝"] += 1
            elif won:
                t["PK勝" if pk else "勝"] += 1
            elif lost:
                t["PK負" if pk else "敗"] += 1
            if not walk:
                t["試合数"] += 1
            sc = r["スコア"]
            if side == "B" and sc:
                a, b = r["得点A"], r["得点B"]
                sc = f"{b}-{a}" + (f" (PK {r['PK_B']}-{r['PK_A']})" if pk else "") + (" (延長)" if "(延長)" in r["スコア"] else "")
            mark = "○" if won else "●" if lost else "－"
            if walk:
                sc = "不戦勝" if won else "不戦敗"
            t["_games"].append(f"{r['ラウンド']} {mark}{sc} {r[f'チーム{other}']}".strip())
            t["_last"] = (r["ラウンド"], won, r["ブロック"])
    out = []
    for t in acc.values():
        rnd, won, block = t["_last"] or ("", False, "")
        if rnd == "3位決定戦":
            t["最終到達"] = "3位" if won else "4位"
        elif won:
            if rnd == "決勝" and block in ("Aブロック", "Bブロック"):
                t["最終到達"] = f"{block}優勝（東京代表・全国大会出場）"
            elif rnd == "決勝":
                t["最終到達"] = "優勝"
            elif rnd == "ブロック決勝":
                t["最終到達"] = "ブロック決勝勝利" + (f"（{block[1:]}へ進出）" if block.startswith("→") else "")
            else:
                # 開催中の大会で、次の試合がまだ行われていない
                t["最終到達"] = f"{rnd}勝利（次戦未実施）" if rnd else ""
        else:
            t["最終到達"] = f"{rnd}敗退" if rnd else ""
        t["戦績"] = " → ".join(t["_games"])
        out.append(t)
    out.sort(key=lambda t: (t["大会"], t["年度"], t["段階"], t["地区・支部"], t["学校_正規化"]))
    return out


def md_table(headers: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "／")  # noqa: E731
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(esc(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def write_markdown(rows: list[dict], teams: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for series, title in SERIES_TITLE.items():
        rs = [r for r in rows if r["大会"] == series]
        ts = [t for t in teams if t["大会"] == series]
        years = sorted({r["年度"] for r in rs})
        parts = [
            f"# 東京都 {title} 試合結果（{years[0]}〜{years[-1]}年度）",
            "",
            "東京都高体連サッカー専門部（tokyosoccer-u18.com）が公開しているトーナメント表 PDF から、"
            "対戦カード・スコア・勝者をプログラムで読み取ったデータ。PDF の赤線（勝ち上がり）を線の座標から判定している。",
            "",
            "## このデータの読み方",
            "",
            "- 1行が1試合。「スコア」は左のチーム（チームA）から見た得点。PK 戦は「1-1 (PK 4-5)」、延長で決着した試合は「(延長)」と書く",
            "- 「勝者」は PDF の赤線で判定した。赤線がまだ引かれていない試合（開催中の大会）はスコアから判定し、状態欄に書いた",
            "- 状態が「未実施」の試合は、PDF 作成時点で行われていなかった試合。「スコア記載なし」は勝者の赤線だけがあり、スコアが書かれていない試合",
            "- 学校名は PDF の表記のまま。年度や大会によって「都・駒場」「駒場」のように表記が異なる。学校別戦績の見出しは代表的な表記",
            "- 「ブロック決勝」は、その山の勝者が次の段階（→ の後ろの枠）へ進む試合。大会全体の決勝ではない",
            "- 勝率を計算するときは、PK 勝・PK 負を分けて数えてある。PK 戦を引き分けとみなすか勝敗とみなすかは用途に応じて選ぶ",
            "",
        ]
        for y in years:
            yr = [r for r in rs if r["年度"] == y]
            parts.append(f"## {y}年度 {title}")
            parts.append("")
            stages = []
            for r in yr:
                k = (r["段階"], r["地区・支部"])
                if k not in stages:
                    stages.append(k)
            for stage, area in stages:
                sr = [r for r in yr if (r["段階"], r["地区・支部"]) == (stage, area)]
                parts.append(f"### {y}年度 {title}{'' if stage in title else ' ' + stage}{' ' + area if area else ''}")
                parts.append("")
                parts.append(f"出典: {sr[0]['出典PDF']}（PDF タイトル: {sr[0]['PDFタイトル'] or 'なし'}）")
                if "作業用" in (sr[0]["PDFタイトル"] or ""):
                    parts.append("注意: この PDF のタイトルは「作業用」となっており、最終版でない可能性がある。")
                pending = sum(r["状態"] == "未実施" for r in sr)
                if pending:
                    parts.append(f"注意: {pending} 試合が PDF 作成時点で未実施（開催中の大会）。")
                parts.append("")
                table = [
                    [r["ブロック"], r["ラウンド"], r["日付"], r["チームA"], r["スコア"], r["チームB"], r["勝者"], r["状態"] if r["状態"] != "終了" else "", " ".join(x for x in [r["前後半"] and f"前後半 {r['前後半']}", r["備考"]] if x)]
                    for r in sr
                ]
                parts.append(md_table(["ブロック", "ラウンド", "日付", "チームA", "スコア", "チームB", "勝者", "状態", "備考"], table))
                parts.append("")
            yt = [t for t in ts if t["年度"] == y]
            if yt:
                parts.append(f"### {y}年度 {title} 学校別の戦績")
                parts.append("")
                parts.append(
                    md_table(
                        ["学校", "段階", "試合数", "勝", "PK勝", "PK負", "敗", "最終到達", "戦績（○勝ち ●負け）"],
                        [[t["学校"], f"{t['段階']}{' ' + t['地区・支部'] if t['地区・支部'] else ''}", t["試合数"], t["勝"], t["PK勝"], t["PK負"], t["敗"], t["最終到達"], t["戦績"]] for t in sorted(yt, key=lambda t: (t["学校_正規化"], t["段階"]))],
                    )
                )
                parts.append("")
        path = out_dir / f"{SERIES_FILE[series]}.md"
        path.write_text("\n".join(parts), encoding="utf-8")
        print(f"{path.name}: {len(rs)} matches, {len(path.read_text(encoding='utf-8'))} chars")
    write_school_index(teams, out_dir / "schools.md")


SERIES_ORDER = {"総体": 0, "選手権": 1, "新人戦": 2, "関東": 3}


def write_school_index(teams: list[dict], path: Path) -> None:
    """学校ごとに、全大会・全年度の戦績を1か所にまとめる。

    大会系統ごとのファイルでは1校の情報が十数か所に散らばり、Gemini が「◯◯高校の全大会の成績」を
    答えるときに一部を取りこぼした（2026-09-11 実測）。学校名で引いたときに1つの塊が当たるようにする。
    """
    by_school: dict[str, list[dict]] = defaultdict(list)
    for t in teams:
        by_school[t["学校_正規化"]].append(t)
    parts = [
        "# 東京都 高校サッカー 学校別 全大会戦績（2022〜2026年度）",
        "",
        "高校総体（インターハイ）東京都予選・全国高校サッカー選手権 東京大会・地区新人選手権大会・関東高校サッカー大会 東京都予選の結果を、学校ごとにまとめたもの。"
        "東京都高体連サッカー専門部のトーナメント表 PDF をプログラムで読み取った。",
        "",
        "- 見出しは学校名（表記ゆれを寄せた名前）。「表記」欄に PDF 上の表記を残した",
        "- 勝・PK勝・PK負・敗は分けて数えた。不戦勝は試合数に含めない",
        "- 「最終到達」はその大会段階での最後の結果。支部予選や一次予選のブロック決勝に勝った場合は、次の段階（二次トーナメントなど）の行も続く",
        "- 大会に出ていない、またはシードで予選が免除された段階の行は無い",
        "",
    ]
    for key in sorted(by_school, key=lambda k: (-len(by_school[k]), k)):
        ts = sorted(by_school[key], key=lambda t: (t["年度"], SERIES_ORDER[t["大会"]], t["段階"]))
        names = sorted({t["学校"] for t in ts})
        tot = {k: sum(int(t[k]) for t in ts) for k in ("試合数", "勝", "PK勝", "PK負", "敗")}
        parts.append(f"## {key}")
        parts.append("")
        parts.append(f"表記: {'、'.join(names)}　／　通算: {tot['試合数']}試合 {tot['勝']}勝 {tot['PK勝']}PK勝 {tot['PK負']}PK負 {tot['敗']}敗")
        parts.append("")
        parts.append(
            md_table(
                ["年度", "大会", "段階", "試合数", "勝", "PK勝", "PK負", "敗", "最終到達", "戦績（○勝ち ●負け）"],
                [[t["年度"], t["大会"], f"{t['段階']}{' ' + t['地区・支部'] if t['地区・支部'] else ''}", t["試合数"], t["勝"], t["PK勝"], t["PK負"], t["敗"], t["最終到達"], t["戦績"]] for t in ts],
            )
        )
        parts.append("")
    path.write_text("\n".join(parts), encoding="utf-8")
    print(f"{path.name}: {len(by_school)} schools, {len(path.read_text(encoding='utf-8'))} chars")


if __name__ == "__main__":
    build()
