"""Tリーグ（高円宮杯 JFA U-18 サッカーリーグ 東京）の全試合と順位表を集める。

サイトに残っているのは 2025・2026 年度（2024 年度以前は公開されていない）。
T1〜T5 の各ブロックについて、schedule.php（節・日時・ホーム・スコア・アウェイ・会場）と rank.php（順位表）を読む。
ブロック番号（ltno）は star_table.php の生の HTML から拾う（「&ltno=」が HTML の &lt; と誤読されるため、BeautifulSoup を通さずに正規表現で探す）。

取得したページは raw/web/tleague/ に保存し、--refresh のときだけ取り直す（アクセスは 1.5 秒以上あける）。
出力:
- data/leagues/tleague_matches.csv   … 1行 = 1試合
- data/leagues/tleague_standings.csv … 1行 = 1チーム × ブロック
- data/leagues/tleague.md             … AI・Notebook 用の要約（順位表）
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize

ROOT = Path(__file__).parent
RAW = ROOT / "raw/web/tleague"
OUT = ROOT / "data/leagues"
BASE = "https://www.tleague-u18.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SEASONS = (2025, 2026)
SQUAD = re.compile(r"^(.*?)[\s・]?([A-JＡ-Ｊ])$")  # 地区リーグには F〜I まで控えがある（東海大高輪台F・紅葉川Ｉ）


def fetch(url: str, path: Path, refresh: bool) -> str:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes().decode("utf-8", "replace")


def squad_of(name: str) -> tuple[str, str]:
    """「修徳B」→（修徳, B）。末尾の英字が控えチームの印。印が無ければ A チーム。"""
    n = name.strip()
    if re.search(r"(FC|SC|F\.C)$", n, re.I):  # 「大森FC」の C は控えの印ではない
        return n, "A"
    m = SQUAD.match(n)
    # 校名が1文字の学校（芝・東）もあるので、残りが1文字でも印とみる。ただし英字だけの名前（クラブ）は分けない
    if m and m[1].strip() and not re.fullmatch(r"[\x00-\x7f]+", m[1]) and not re.search(r"(U-?1[5-8]|FC|F\.C)$", m[1], re.I):
        return m[1].strip(), m[2].translate(str.maketrans("ＡＢＣＤＥＦＧＨＩＪ", "ABCDEFGHIJ"))
    return n, "A"


def rows_of(table) -> list[list[str]]:
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def blocks(dy: int, dt: int, refresh: bool) -> list[tuple[str, str]]:
    """(ltno, ブロック名) の一覧。ブロックに分かれていない部は [("", "")]。"""
    raw = fetch(f"{BASE}/star_table.php?dy={dy}&dt={dt}", RAW / f"star_{dy}_{dt}.html", refresh)
    found = {}
    for no, label in re.findall(rf"dt={dt}&(?:amp;)?ltno=(\d+)[^>]*>\s*([^<]{{1,20}}?)\s*<", raw):
        if "ブロック" in label or "グループ" in label:
            found.setdefault(no, label.replace(f"T{dt}", "").strip())
    return sorted(found.items(), key=lambda kv: int(kv[0])) or [("", "")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    matches, standings = [], []
    for dy in SEASONS:
        for dt in range(1, 6):
            for no, label in blocks(dy, dt, args.refresh):
                q = f"dy={dy}&dt={dt}" + (f"&ltno={no}" if no else "")
                sched = BeautifulSoup(fetch(f"{BASE}/schedule.php?{q}", RAW / f"schedule_{dy}_{dt}_{no or 0}.html", args.refresh), "html.parser")
                rank = BeautifulSoup(fetch(f"{BASE}/rank.php?{q}", RAW / f"rank_{dy}_{dt}_{no or 0}.html", args.refresh), "html.parser")
                league = f"T{dt}"
                src = f"{BASE}/schedule.php?{q}"
                n_before = len(matches)
                for r in rows_of(sched.find("table")) if sched.find("table") else []:
                    if len(r) != 6 or not r[0].isdigit():
                        continue
                    sec, when, home, score, away, venue = r
                    m = re.fullmatch(r"(\d+)-(\d+)", score.replace(" ", ""))
                    d = re.match(r"(\d{2})/(\d{2})", when)
                    hb, hs = squad_of(home)
                    ab, as_ = squad_of(away)
                    matches.append({
                        "年度": dy, "リーグ": league, "ブロック": label, "節": int(sec),
                        "日付": f"{dy if not d or int(d[1]) >= 4 else dy + 1}-{d[1]}-{d[2]}" if d else "", "時刻": when[6:].strip() if d else "",
                        "ホーム": home, "アウェイ": away, "ホーム得点": int(m[1]) if m else "", "アウェイ得点": int(m[2]) if m else "",
                        "会場": venue, "実施": "済" if m else "未",
                        "ホーム学校": normalize(hb), "ホーム区分": hs, "アウェイ学校": normalize(ab), "アウェイ区分": as_, "出典": src,
                    })
                for r in rows_of(rank.find("table")) if rank.find("table") else []:
                    if len(r) == 10 and r[1].isdigit():
                        base, sq = squad_of(r[0])
                        standings.append({
                            "年度": dy, "リーグ": league, "ブロック": label, "順位": int(r[9]), "チーム": r[0], "学校": normalize(base), "区分": sq,
                            "勝点": int(r[1]), "試合": int(r[2]), "勝": int(r[3]), "敗": int(r[4]), "分": int(r[5]),
                            "得点": int(r[6]), "失点": int(r[7]), "得失点": int(r[8]), "出典": f"{BASE}/rank.php?{q}",
                        })
                print(f"{dy} {league} {label or '-':<8} 試合 {len(matches) - n_before:3d}")
    with (OUT / "tleague_matches.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(matches[0].keys()))
        w.writeheader()
        w.writerows(matches)
    with (OUT / "tleague_standings.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(standings[0].keys()))
        w.writeheader()
        w.writerows(standings)
    write_md(matches, standings)
    played = sum(m["実施"] == "済" for m in matches)
    print(f"試合 {len(matches)}（実施済み {played}）・順位表 {len(standings)} 行")
    return 0


def write_md(matches: list, standings: list) -> None:
    md = ["# Tリーグ（高円宮杯 JFA U-18 サッカーリーグ 東京）2025・2026年度", "",
          "出典: https://www.tleague-u18.com/ （collect_tleague.py で収集。2024年度以前はサイトに残っていない）", "",
          "- 東京都のリーグの階層: プレミア → プリンス関東 → T1 → T2 → T3 → T4 → T5 → 各地区のリーグ",
          "- チーム名の末尾の英字（B・C・D…）は控えチーム。CSV の「区分」は印の無いものを A としている",
          "- **注意**: 2026年度に T1 より上にいる東京の高校は帝京だけ（プリンスリーグ関東1部。出典: https://www.juniorsoccer-news.com/post-1782850 ）。"
          "Tリーグの「帝京B」「帝京C」は2・3番手のチームなので、帝京の成績をそのまま学校の強さとして扱わないこと。"
          "國學院久我山・成立学園・駒澤大高・東京成徳大高は、印の無いチームがトップチーム",
          "- 学校名の略称（久我山＝國學院久我山、実践＝実践学園、成立＝成立学園、駒大＝駒澤大高、専大附＝専修大附、東京成徳＝東京成徳大高）は scout/school_aliases.json で名寄せしている",
          f"- 収録: 試合 {len(matches)}（実施済み {sum(m['実施'] == '済' for m in matches)}）。全試合は data/leagues/tleague_matches.csv", ""]
    key = lambda s: (s["年度"], s["リーグ"], s["ブロック"])  # noqa: E731
    for k in sorted({key(s) for s in standings}, key=lambda k: (-k[0], k[1], k[2])):
        rows = sorted([s for s in standings if key(s) == k], key=lambda s: s["順位"])
        md += [f"## {k[0]}年度 {k[1]} {k[2]}".rstrip(), "", "| 順位 | チーム | 試合 | 勝点 | 勝 | 分 | 敗 | 得点 | 失点 | 得失点 |", "|---|---|---|---|---|---|---|---|---|---|"]
        md += [f"| {s['順位']} | {s['チーム']} | {s['試合']} | {s['勝点']} | {s['勝']} | {s['分']} | {s['敗']} | {s['得点']} | {s['失点']} | {s['得失点']:+d} |" for s in rows]
        md.append("")
    (OUT / "tleague.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
