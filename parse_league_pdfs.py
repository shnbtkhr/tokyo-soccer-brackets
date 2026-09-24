"""T リーグの日程 PDF（T1-1.pdf など）から、1試合1行のデータを読む。

pdfs/leagues/<年度>_<ファイル名>.pdf が対象。星取表（-star）は順位の集計なので読まず、
日程表だけを読む。1行は「節・期日・キックオフ・HOME・得点・得点・AWAY・会場」の並びで、
まだ行われていない試合は得点が空になっている。

  uv run python parse_league_pdfs.py

出力: data/leagues/tleague_archive_matches.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

from build_outputs import normalize

ROOT = Path(__file__).parent
SRC = ROOT / "pdfs/leagues"
OUT = ROOT / "data/leagues/tleague_archive_matches.csv"


def cells(page: pymupdf.Page) -> list[tuple[float, float, str]]:
    """文字を (y, x, 内容) で取り出す。表の罫線は使わず、並びで行を作る。"""
    out = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for sp in line.get("spans", []):
                t = sp["text"].strip()
                if t:
                    out.append((round(sp["bbox"][1], 1), round(sp["bbox"][0], 1), t))
    return sorted(out)


def rows_of(page: pymupdf.Page) -> list[tuple[float, list[str]]]:
    """y が近い文字を1行にまとめ、(y, セルの並び) で返す。"""
    rows, cur, y0 = [], [], None
    for y, x, t in cells(page):
        if y0 is None or abs(y - y0) <= 3.5:
            cur.append((x, t))
            y0 = y if y0 is None else y0
        else:
            rows.append((y0, [t for _, t in sorted(cur)]))
            cur, y0 = [(x, t)], y
    if cur:
        rows.append((y0, [t for _, t in sorted(cur)]))
    return rows


DATE = re.compile(r"(\d{1,2})月\s*(\d{1,2})日")
TIME = re.compile(r"^\d{1,2}:\d{2}$")
SEP = ("vs", "VS", "ｖｓ", "-", "－", "ー", "−")


def clean(name: str) -> str:
    """チーム名の前に付く節・ブロックの印（第1節・A など）を落とす。"""
    t = name.strip()
    t = re.sub(r"^第\s*\d+\s*節\s*", "", t)
    t = re.sub(r"^[A-Za-zＡ-Ｚ]\s+", "", t)
    t = re.sub(r"^(節|会場|HOME|AWAY)\s*", "", t)
    return t.strip()


def match_row(r: list[str]) -> dict | None:
    """「ホーム 得点 vs 得点 アウェイ 会場」の並びを読む。まだの試合は得点が空。"""
    # 見出し行（節・期日・HOME・AWAY …）は試合ではない
    if any(c in ("HOME", "AWAY", "節", "会場", "対　戦") for c in r):
        return None
    idx = [i for i, c in enumerate(r) if c in SEP]
    for i in idx:
        left, right = r[:i], r[i + 1:]
        if not left or not right:
            continue
        # 区切りの前後が得点（1〜2桁）なら、その外側がチーム名
        if re.fullmatch(r"\d{1,2}", left[-1]) and right and re.fullmatch(r"\d{1,2}", right[0]):
            home = " ".join(x for x in left[:-1] if not TIME.match(x) and not DATE.search(x))
            gh, ga = left[-1], right[0]
            away = right[1] if len(right) > 1 else ""
            venue = " ".join(right[2:])
        else:
            home = " ".join(x for x in left if not TIME.match(x) and not DATE.search(x))
            gh = ga = ""
            away = right[0] if right else ""
            venue = " ".join(right[1:])
        home, away = clean(home), clean(away)
        if not home or not away:
            continue
        return {"home": home, "gh": gh, "ga": ga, "away": away, "venue": venue.strip()}
    return None


def parse(path: Path) -> list[dict]:
    m = re.match(r"(\d{4})_([A-Za-z0-9]+)", path.stem)
    if not m:
        return []
    season, div = int(m[1]), m[2].replace("_", "").upper()
    doc = pymupdf.open(path)
    out = []
    for page in doc:
        rows = rows_of(page)
        # 日付と時刻は、同じ行にあるとは限らない（別のセルに分かれている年がある）。
        # そこで、いちばん近い高さにある日付を結びつける
        dates = [(y, DATE.search(" ".join(r))) for y, r in rows if DATE.search(" ".join(r))]
        times = [(y, t) for y, r in rows for t in r if TIME.match(t)]
        for y, r in rows:
            mm = match_row(r)
            if not mm:
                continue
            near = min(dates, key=lambda d: abs(d[0] - y), default=None)
            if not near or abs(near[0] - y) > 40:
                continue
            mo, da = near[1].groups()
            year = season + (0 if int(mo) >= 4 else 1)
            kick = min(times, key=lambda t: abs(t[0] - y), default=(None, ""))[1] if times else ""
            out.append({
                "年度": season, "リーグ": div, "日付": f"{year}-{int(mo):02d}-{int(da):02d}", "キックオフ": kick,
                "ホーム": mm["home"], "学校H": normalize(mm["home"]), "得点H": mm["gh"],
                "アウェイ": mm["away"], "学校A": normalize(mm["away"]), "得点A": mm["ga"],
                "会場": mm["venue"], "出典": path.name,
            })
    return out


def main() -> int:
    rows = []
    for p in sorted(SRC.glob("*.pdf")):
        if "star" in p.stem:
            continue
        got = parse(p)
        rows += got
        print(f"  {p.name:26} {len(got):3} 試合")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    done = sum(1 for r in rows if r["得点H"])
    print(f"合計 {len(rows)} 試合（スコアあり {done}） → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
