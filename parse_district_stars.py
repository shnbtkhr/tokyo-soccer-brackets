"""地区リーグの星取表 PDF（早大学院サッカー部が公開しているもの）から1試合1行を作る。

2008〜2026年度の「地区トップリーグ／NSリーグ／Tリーグ／ユニティリーグ」の星取表。
リーグの名前は年によって変わるが、表の形は変わらない。行と列に同じ順でチームが並び、
交点に勝敗の印（○●△）と得点が入る。

読み方は罫線を使わず、印の位置から格子を組み立てる。

1. 「YYYY年度　…」の見出しで表を切り分ける
2. 印（○●△）の x をまとめて列、y をまとめて行にする
3. 行の左端にある文字をチーム名として拾う。星取表は行と列が同じ順なので、列の名前は
   行から借りる（列見出しは「大泉」、行は「都立大泉」のように省略されていることがある）
4. 交点の印の下にある数字2つが、その行のチームから見た得点と失点

対角線（自分どうし）と、まだ行われていない試合（印も数字も無い）は飛ばす。
行 i と行 j の両方に同じ試合が入っているので、i < j の側だけを採り、もう片方は
食い違いの検査に使う。

  uv run python parse_district_stars.py --list    # 表の一覧と読めた試合数
  uv run python parse_district_stars.py           # CSV を書く

出力: data/leagues/district_stars_matches.csv
出典: https://waseda-gakuinfc.com/ （PDF は pdfs/district/ に取得済み）
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pymupdf

from build_outputs import normalize

ROOT = Path(__file__).parent
SRC = ROOT / "pdfs/district"
OUT = ROOT / "data/leagues/district_stars_matches.csv"
MARKS = "○●△◎×"
WIN, LOSE, DRAW = "○◎", "●×", "△"
# 同じ年度で新旧2版ある場合は新しいほうだけを読む
SKIP = {"waseda_2026-Tリーグ・ユニティリーグ・NSリーグ星取表20260603"}


def spans_of(page: pymupdf.Page) -> list[dict]:
    out = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                t = s["text"].strip()
                if t:
                    x0, y0, x1, _ = s["bbox"]
                    out.append({"y": round(y0, 1), "x0": round(x0, 1), "x1": round(x1, 1),
                                "cx": round((x0 + x1) / 2, 1), "t": t})
    out.sort(key=lambda s: (s["y"], s["x0"]))
    return out


def cluster(vals: list[float], tol: float) -> list[float]:
    """近い値をひとまとめにして、代表値（平均）を返す。"""
    out: list[list[float]] = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def league_of(title: str) -> dict:
    """見出しから、年度・リーグ名・部やブロックを取り出す。"""
    t = unicodedata.normalize("NFKC", title).replace("　", " ")
    year = int(re.match(r"(\d{4})年度", t)[1])
    name = next((n for n in ("地区トップリーグ", "NSリーグ", "Tokyo Unity League",
                             "ユニティリーグ", "Tリーグ", "T3リーグ", "T4リーグ") if n in t), "")
    if name in ("T3リーグ", "T4リーグ"):
        name = "Tリーグ"
    rest = t[len("2014年度"):].replace(name, " ").strip()
    rest = re.sub(r"\s+", " ", rest)
    return {"year": year, "league": name or rest.split(" ")[0], "division": rest,
            "ranking": bool(re.search(r"順位決定", t))}


DATE = re.compile(r"\d{1,2}月\s*\d{1,2}日")


def parse_single(reg: list[dict]) -> list[dict]:
    """順位決定戦など、1試合だけの表を読む。

    星取表と違って「期日／キックオフ／グループA／vs／グループB／会場」の1行もので、
    得点は対戦行の上、PK は下に置かれる。見出しの x をそのまま列の位置として使う。
    """
    head = next((s for s in reg if s["t"] == "期日"), None)
    if head is None:
        return []
    band = [s for s in reg if abs(s["y"] - head["y"]) <= 4]
    hx = next((s["cx"] for s in band if s["t"].endswith(("グループA", "ＨＯＭＥ", "HOME"))), None)
    ax = next((s["cx"] for s in band if s["t"].endswith(("グループB", "ＡＷＡＹ", "AWAY"))), None)
    if hx is None or ax is None:
        return []

    out = []
    for fix in [s for s in reg if s["y"] > head["y"] and DATE.match(s["t"])]:
        row = [s for s in reg if abs(s["y"] - fix["y"]) <= 4]
        near = lambda x: min((s for s in row if abs(s["cx"] - x) <= 40 and not DATE.match(s["t"])),  # noqa: E731
                             key=lambda s: abs(s["cx"] - x), default=None)
        home, away = near(hx), near(ax)
        if not home or not away or home is away:
            continue
        # 得点は対戦行のすぐ上（PK は下）。「2 - 1」の数字2つを拾う
        up = sorted((s for s in reg if fix["y"] - 14 < s["y"] < fix["y"] - 1
                     and re.fullmatch(r"\d{1,2}", s["t"])), key=lambda s: s["cx"])
        if len(up) < 2:
            continue
        out.append({"ホーム": home["t"], "アウェイ": away["t"],
                    "得点H": int(up[0]["t"]), "得点A": int(up[1]["t"]), "二重": False})
    return out


def parse_table(title: str, reg: list[dict]) -> tuple[dict, list[dict], list[str]]:
    """1つの星取表から試合を読む。(見出しの情報, 試合, 気づいたこと) を返す。"""
    meta = league_of(title)
    notes: list[str] = []
    marks = [s for s in reg if s["t"] in MARKS]
    if len(marks) < 2:
        single = parse_single(reg)
        return meta, single, [] if single else ["印が見つからない"]

    cols = cluster([s["cx"] for s in marks], 12)
    rows = cluster([s["y"] for s in marks], 8)
    pitch = min((cols[i + 1] - cols[i] for i in range(len(cols) - 1)), default=36)
    half = pitch / 2
    # 得点の行が印の何 px 下に来るかは表によって違う（11〜19px）。次の行に食い込まない
    # ところまでを1つの升目とみなす
    ypitch = min((rows[i + 1] - rows[i] for i in range(len(rows) - 1)), default=21)
    below = ypitch * 0.85

    # 行の左端にあるチーム名。印の左端より左に出ているものを拾う
    left = cols[0] - half
    names: list[str] = []
    for ry in rows:
        cands = [s for s in reg if abs(s["y"] - ry) <= 11 and s["x1"] <= left + 2
                 and s["t"] not in MARKS and not re.fullmatch(r"[\d.\-－ ]+", s["t"])]
        names.append(min(cands, key=lambda s: s["x0"])["t"] if cands else "")
    if len(cols) != len(rows):
        notes.append(f"行 {len(rows)} と列 {len(cols)} の数が合わない")
    if any(not n for n in names):
        notes.append(f"名前の取れない行が {sum(1 for n in names if not n)}")

    n = min(len(rows), len(cols))
    seen: dict[tuple[int, int], dict] = {}
    for i in range(n):
        ry = rows[i]
        for j in range(n):
            if i == j:
                continue
            cx = cols[j]
            cell = [s for s in reg if abs(s["cx"] - cx) <= half and ry - 6 <= s["y"] <= ry + below]
            mk = next((s["t"] for s in cell if s["t"] in MARKS), "")
            # 「2－3」の区切りが右の数字にくっついて「－3」と1つの文字列になる年がある
            nums = [(s["x0"], int(re.sub(r"^[-－]", "", s["t"])))
                    for s in cell if re.fullmatch(r"[-－]?\d{1,2}", s["t"]) and s["y"] > ry + 4]
            nums.sort()
            if not mk and len(nums) < 2:
                continue
            gf, ga = (nums[0][1], nums[1][1]) if len(nums) >= 2 else (None, None)
            seen[(i, j)] = {"mark": mk, "gf": gf, "ga": ga, "extra": len(nums) > 2}

    out, conflicts = [], 0
    for (i, j), a in seen.items():
        if i > j:
            continue
        b = seen.get((j, i))
        # 対になる升目と突き合わせる。食い違ったら、どちらが正しいか決められないので飛ばす
        if b and a["gf"] is not None and b["gf"] is not None and (a["gf"], a["ga"]) != (b["ga"], b["gf"]):
            conflicts += 1
            continue
        if a["gf"] is None and b and b["gf"] is not None:
            a = {"mark": a["mark"], "gf": b["ga"], "ga": b["gf"], "extra": b["extra"]}
        if a["gf"] is None:
            continue
        home, away = names[i], names[j]
        if not home or not away:
            continue
        res = "勝" if a["mark"] in WIN else "負" if a["mark"] in LOSE else "分" if a["mark"] in DRAW else ""
        by_score = "勝" if a["gf"] > a["ga"] else "負" if a["gf"] < a["ga"] else "分"
        if res and res != by_score:
            conflicts += 1
            continue
        out.append({"ホーム": home, "アウェイ": away, "得点H": a["gf"], "得点A": a["ga"],
                    "二重": a["extra"]})
    if conflicts:
        notes.append(f"印と得点、または対になる升目が食い違う {conflicts} 件は見送り")
    twice = sum(1 for m in out if m["二重"])
    if twice:
        notes.append(f"1つの升目に3つ以上の数字（2回戦制の可能性） {twice} 件")
    return meta, out, notes


def split_side(name: str) -> tuple[str, str]:
    """「國學院久我山C」→（国学院久我山, C）。Bチーム以下は同じ学校として扱う。"""
    m = re.match(r"^(.*?)([A-ZＡ-Ｚ])$", name.strip())
    if m and len(m[1]) >= 2:
        return normalize(m[1]), unicodedata.normalize("NFKC", m[2])
    return normalize(name), ""


def parse_pdf(path: Path) -> tuple[list[dict], list[str]]:
    rows, log = [], []
    doc = pymupdf.open(path)
    for page in doc:
        sp = spans_of(page)
        heads = [s for s in sp if re.match(r"\d{4}年度", s["t"])]
        for k, h in enumerate(heads):
            end = heads[k + 1]["y"] if k + 1 < len(heads) else 10_000
            reg = [s for s in sp if h["y"] < s["y"] < end]
            meta, ms, notes = parse_table(h["t"], reg)
            for m in ms:
                sh, dh = split_side(m["ホーム"])
                sa, da = split_side(m["アウェイ"])
                if not sh or not sa or sh == sa:
                    continue
                rows.append({
                    "年度": meta["year"], "リーグ": meta["league"], "区分": meta["division"],
                    "ホーム": m["ホーム"], "ホーム学校": sh, "ホーム区分": dh,
                    "アウェイ": m["アウェイ"], "アウェイ学校": sa, "アウェイ区分": da,
                    "得点H": m["得点H"], "得点A": m["得点A"], "出典": path.name,
                })
            label = unicodedata.normalize("NFKC", h["t"]).replace("　", " ")
            log.append(f'    {label[:42]:44} {len(ms):3} 試合' + ("  ※ " + " / ".join(notes) if notes else ""))
    return rows, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="表ごとの読み取り件数だけ出す")
    args = ap.parse_args()

    rows: list[dict] = []
    for path in sorted(SRC.glob("*.pdf")):
        if path.stem in SKIP:
            continue
        got, log = parse_pdf(path)
        rows += got
        print(f"{path.stem[:52]:54} {len(got):4} 試合")
        if args.list:
            print("\n".join(log))
    if not rows:
        print("読めた試合がありません")
        return 1

    by = defaultdict(int)
    for r in rows:
        by[(r["年度"], r["リーグ"])] += 1
    print("\n年度・リーグ別")
    for k in sorted(by):
        print(f"  {k[0]} {k[1]:16} {by[k]:4}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n合計 {len(rows)} 試合 → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
