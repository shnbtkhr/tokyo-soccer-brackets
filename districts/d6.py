"""第6地区（第6地区リーグU-18、通称・第6地区ユースリーグ）の順位表と試合を集める。決まりは notes/district_collector_spec.md。

2026年度: 公式ポータル tokyo6league.com は各部のページから Google サイト（sites.google.com/gakugei-hs.info/league6）へ誘導しており、
          そこに埋め込まれた Google フォーム回答シートを gviz/tq?tqx=out:csv で取得すると、1行=1試合の結果ログが取れる（5ブロック: 1部・2部A・2部B・3部A・3部B）。
          順位表ページは無いため、試合結果から集計する（出典末尾に「（試合から計算）」を付ける）。
2024年度: 地区一元の結果ページは見つかっていない。都立芦花高校の部活動ページに3部A（芦花の所属ブロック）の最終成績と、
          シーズン途中の試合結果が一部だけ載っている（芦花以外のチームの成績・順位は不明）。

取得したページは raw/web/district/d6/ に保存し、refresh=True か未保存のときだけ取りに行く（同じサイトへは1.5秒以上あける）。
"""

from __future__ import annotations

import csv
import io
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw/web/district/d6"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CHIKU = "第6地区"
LEAGUE = "第6地区リーグU-18（通称・第6地区ユースリーグ）"

# 2026年度: Googleフォーム回答シート（1試合1行）。カテゴリー列の値ごとに、使われる列グループが違う。
GVIZ_URL = "https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv"
GVIZ_PATH = RAW / "sheet_league6_gviz.csv"
# カテゴリー名 -> (ホーム, アウェイ, 日付, 会場, ホーム得点, アウェイ得点) の列インデックス（0始まり）
GVIZ_GROUPS = {
    "1部": (2, 3, 4, 5, 6, 7),
    "2部A": (9, 10, 11, 12, 13, 14),
    "2部B": (16, 17, 18, 19, 20, 21),
    "3部A": (23, 24, 25, 26, 27, 28),
    "3部B": (30, 31, 32, 33, 34, 35),
}
GVIZ_MONTH_COL, GVIZ_DAY_COL = 49, 50
GVIZ_YEAR = 2026  # フォームの月は4〜9のみ（2026年度内に収まる）

# 2024年度: 都立芦花高校の部活動ページ（3部Aの最終成績と一部の試合結果）
ROKA_FINAL_URL = "https://www.metro.ed.jp/roka-h/activities/2025/01/clubentry_90.html"
ROKA_FINAL_PATH = RAW / "roka_clubentry90.html"
ROKA_MID_URL = "https://www.metro.ed.jp/roka-h/activities/2024/07/clubentry_75.html"
ROKA_MID_PATH = RAW / "metro_roka_clubentry75.html"


def fetch(url: str, path: Path, refresh: bool) -> str:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes().decode("utf-8", "replace")


def std_row(year: int, bu: str, rank, name: str, w="", d="", l="", gf="", ga="", src: str = "") -> dict:
    base, sq = squad_of(name)
    row = {"地区": CHIKU, "リーグ": LEAGUE, "年度": year, "部": bu, "順位": rank,
           "チーム": name, "学校": normalize(base), "区分": sq, "出典": src}
    row["勝点"] = "" if w == "" or d == "" else 3 * w + d
    row["試合"] = "" if w == "" or d == "" or l == "" else w + d + l
    row["勝"], row["分"], row["敗"] = w, d, l
    row["得点"], row["失点"] = gf, ga
    row["得失点"] = "" if gf == "" or ga == "" else gf - ga
    return row


def match_row(year: int, bu: str, home: str, away: str, hs, as_, done: str, src: str, date: str = "", sec: str = "") -> dict:
    row = {"地区": CHIKU, "リーグ": LEAGUE, "年度": year, "部": bu, "節": sec, "日付": date,
           "ホーム": home, "アウェイ": away, "ホーム得点": hs, "アウェイ得点": as_, "実施": done, "出典": src}
    hb, hsq = squad_of(home)
    ab, asq = squad_of(away)
    row["ホーム学校"], row["ホーム区分"] = normalize(hb), hsq
    row["アウェイ学校"], row["アウェイ区分"] = normalize(ab), asq
    return row


# ---------- 2026年度: Googleフォーム回答シート（試合から計算） ----------

def gviz_matches(csv_text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(csv_text)))
    out = []
    for r in rows[1:]:
        cat = r[1].strip()
        cols = GVIZ_GROUPS.get(cat)
        if not cols:
            continue
        home, away, _date, _venue, hs, as_ = (r[c].strip() for c in cols)
        if not home or not away or hs == "" or as_ == "":
            continue
        month, day = r[GVIZ_MONTH_COL].strip(), r[GVIZ_DAY_COL].strip()
        date = f"{GVIZ_YEAR}-{int(month):02d}-{int(day):02d}" if month.isdigit() and day.isdigit() else ""
        out.append(match_row(2026, cat, home, away, int(hs), int(as_), "済", GVIZ_URL, date))
    return out


def standings_from_matches(year: int, bu: str, matches: list[dict], src: str) -> list[dict]:
    stat: dict[str, list[int]] = {}
    for m in matches:
        if m["年度"] != year or m["部"] != bu:
            continue
        for team, gf, ga in ((m["ホーム"], m["ホーム得点"], m["アウェイ得点"]), (m["アウェイ"], m["アウェイ得点"], m["ホーム得点"])):
            s = stat.setdefault(team, [0, 0, 0, 0, 0])  # 勝, 分, 敗, 得点, 失点
            if gf > ga:
                s[0] += 1
            elif gf == ga:
                s[1] += 1
            else:
                s[2] += 1
            s[3] += gf
            s[4] += ga
    ranked = sorted(stat.items(), key=lambda kv: (-(3 * kv[1][0] + kv[1][1]), -(kv[1][3] - kv[1][4]), kv[0]))
    return [std_row(year, bu, i + 1, name, w, d, l, gf, ga, src + "（試合から計算）")
             for i, (name, (w, d, l, gf, ga)) in enumerate(ranked)]


# ---------- 2024年度: 都立芦花高校の部活動ページ ----------

def roka_final_2024(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article") or soup.body
    text = unicodedata.normalize("NFKC", art.get_text("\n", strip=True))
    m = re.search(r"第6地区リーグU18\s*3部A\s*\n(\d+)勝(\d+)敗\s*(\d+)位", text)
    if not m:
        return []
    w, l, rank = int(m[1]), int(m[2]), int(m[3])
    return [std_row(2024, "3部A", rank, "芦花", w, 0, l, src=ROKA_FINAL_URL)]


def roka_mid_2024(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article") or soup.body
    text = unicodedata.normalize("NFKC", art.get_text("\n", strip=True))
    out = []
    for m in re.finditer(r"(\d{1,2})月(\d{1,2})日[^\n]*?[▲◎△]芦花(\d+)[－-]([^\d\n]+?)(\d+)(?=\n|$)", text):
        month, day, hs, away, as_ = m.groups()
        date = f"2024-{int(month):02d}-{int(day):02d}"
        out.append(match_row(2024, "3部A", "芦花", away.strip(), int(hs), int(as_), "済", ROKA_MID_URL, date))
    return out


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    standings: list[dict] = []
    matches: list[dict] = []

    csv_text = fetch(GVIZ_URL, GVIZ_PATH, refresh)
    m2026 = gviz_matches(csv_text)
    matches += m2026
    for bu in GVIZ_GROUPS:
        standings += standings_from_matches(2026, bu, m2026, GVIZ_URL)

    final_html = fetch(ROKA_FINAL_URL, ROKA_FINAL_PATH, refresh)
    standings += roka_final_2024(final_html)
    mid_html = fetch(ROKA_MID_URL, ROKA_MID_PATH, refresh)
    matches += roka_mid_2024(mid_html)

    return standings, matches


if __name__ == "__main__":
    s, m = collect()
    print(f"順位表 {len(s)} 行・試合 {len(m)} 行")
