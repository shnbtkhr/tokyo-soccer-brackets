"""第7地区（第7地区ユースリーグ）の順位表・試合を集める（notes/district_collector_spec.md 準拠）。

2026年度: 1つの公開スプレッドシート（ブロックごとに別ID）の中に3タブ
  （星取表 gid=1051712607／順位表 gid=513876327／全試合結果 gid=80189940）があり、
  順位表タブと全試合結果タブをそれぞれCSVで取得する
  （`https://docs.google.com/spreadsheets/d/e/<ID>/pub?gid=<gid>&single=true&output=csv`
  にリダイレクト追従すると取れる。data/leagues/sources.csv で確認済みのURL）。

2024・2025年度: Googleサイトの過去データページ（archives/<年度>/Scores/<ブロック>）に
  「[]内は勝ち点」形式の最終順位のみが文章で書かれている（節ごとの試合結果は無い）。
  本文の可視テキストは1文字ずつ別のspanに分かれておりBeautifulSoupのget_text()では
  正しく繋がらないため、<meta property="og:description"> の中の整形済みテキストを読む。
  「アローレ八王子U-184位」のようにチーム名の末尾の数字と次の順位の数字が地続きになる
  箇所があるので、正規表現の総当たりではなく「次に来るはずの順位」を直接探して切る。

保存先: raw/web/district/d7/。同じサイト（docs.google.com／sites.google.com）へのアクセスは
1.5秒以上あける。
"""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw/web/district/d7"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

地区 = "第7地区"
リーグ = "第7地区ユースリーグ"
BLOCKS = ("1部", "2部A", "2部B", "3部A", "3部B")

# 2026年度: ブロック名 -> 公開スプレッドシートID（data/leagues/sources.csv 101〜105行で確認済み）
SHEETS_2026 = {
    "1部": "2PACX-1vQVPxsdzQeHgNi4Bg02sDdW2DYT-H-jTe8Q3NttnomTX3wCBomCCepRUQPb_Szwlq6D9RkOnPZnznB2",
    "2部A": "2PACX-1vQDgq8t4JUX3Bwny3MQXdTAYZz1ya47lHunDLtuGBYg3R_y30tCEiB5YIfLLXnNPXTVL_FTW0FzIOC6",
    "2部B": "2PACX-1vSnG2t7r30I6bfEEBBGZRKWZo3ixiupiIdVCBR4RyKdn1TUhL8C6i2pEiNNaZ4yslVIUR5LF92BaFMS",
    "3部A": "2PACX-1vQx2FQdzhqIHTKWyZgvsblEu1BNjxh8D164OyzusdtyTV3U3iqZhlZdR2x2Iiu-FXllAvaRzSJW3AUI",
    "3部B": "2PACX-1vSz-Rl0rEvqrXiYZjx_kzGuJ4RUw2SNB336r2xVEhaeSiIrUKWdA3VM-XDAJIXoihKh_eDUxW1Hw5Nl",
}
STEM_2026 = {"1部": "1st", "2部A": "2a", "2部B": "2b", "3部A": "3a", "3部B": "3b"}
GID_STANDINGS = 513876327
GID_MATCHES = 80189940

# 2024・2025年度: Googleサイトの過去データページ（結果ページのURL = 順位表ページのURL、静的テキスト）
ARCHIVE_PAGES = {
    2024: {
        "1部": ("gsite_2024_1st.html", "https://sites.google.com/view/youthleague-7/archives/2024/Scores/1st-division"),
        "2部A": ("gsite_2024_2a.html", "https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-a"),
        "2部B": ("gsite_2024_2b.html", "https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-b"),
        "3部A": ("gsite_2024_3a.html", "https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-a"),
        "3部B": ("gsite_2024_3b.html", "https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-b"),
    },
    2025: {
        "1部": ("gsite_2025_1.html", "https://sites.google.com/view/youthleague-7/archives/2025/Scores/1"),
        "2部A": ("gsite_2025_2a.html", "https://sites.google.com/view/youthleague-7/archives/2025/Scores/2a"),
        "2部B": ("gsite_2025_2b.html", "https://sites.google.com/view/youthleague-7/archives/2025/Scores/2b"),
        "3部A": ("gsite_2025_3a.html", "https://sites.google.com/view/youthleague-7/archives/2025/Scores/3a"),
        "3部B": ("gsite_2025_3b.html", "https://sites.google.com/view/youthleague-7/archives/2025/Scores/3b"),
    },
}


def fetch(url: str, path: Path, refresh: bool) -> bytes:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes()


def _team_school(name: str) -> tuple[str, str]:
    base, sq = squad_of(name)
    return normalize(base), sq


def _standings_csv_url(sheet_id: str, gid: int) -> str:
    return f"https://docs.google.com/spreadsheets/d/e/{sheet_id}/pub?gid={gid}&single=true&output=csv"


def _int_or_blank(s: str):
    s = (s or "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else ""


def standings_2026(block: str, refresh: bool) -> list[dict]:
    stem = STEM_2026[block]
    url = _standings_csv_url(SHEETS_2026[block], GID_STANDINGS)
    raw = fetch(url, RAW / f"2026_{stem}_standings.csv", refresh)
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig", "replace"))))
    out = []
    for r in rows[1:]:
        if len(r) < 10 or not r[0].strip().isdigit() or not r[1].strip():
            continue
        school, sq = _team_school(r[1].strip())
        out.append({
            "地区": 地区, "リーグ": リーグ, "年度": 2026, "部": block,
            "順位": int(r[0]), "チーム": r[1].strip(), "学校": school, "区分": sq,
            "勝点": _int_or_blank(r[2]), "試合": _int_or_blank(r[3]),
            "勝": _int_or_blank(r[4]), "分": _int_or_blank(r[5]), "敗": _int_or_blank(r[6]),
            "得点": _int_or_blank(r[7]), "失点": _int_or_blank(r[8]), "得失点": _int_or_blank(r[9]),
            "出典": url,
        })
    return out


def matches_2026(block: str, refresh: bool) -> list[dict]:
    stem = STEM_2026[block]
    url = _standings_csv_url(SHEETS_2026[block], GID_MATCHES)
    raw = fetch(url, RAW / f"2026_{stem}_matches.csv", refresh)
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig", "replace"))))
    out = []
    for r in rows[2:]:  # 0行目=案内文、1行目=ヘッダ
        if len(r) < 7 or not r[0].strip():
            continue
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", r[0].strip())
        if not m:
            continue
        home, away = r[2].strip(), r[6].strip()
        if not home or not away:
            continue
        date = f"2026-{int(m[1]):02d}-{int(m[2]):02d}"
        hs, as_ = r[3].strip(), r[5].strip()
        done = bool(re.fullmatch(r"\d+", hs)) and bool(re.fullmatch(r"\d+", as_))
        h_school, h_sq = _team_school(home)
        a_school, a_sq = _team_school(away)
        out.append({
            "地区": 地区, "リーグ": リーグ, "年度": 2026, "部": block,
            "節": "", "日付": date,
            "ホーム": home, "アウェイ": away,
            "ホーム得点": int(hs) if done else "", "アウェイ得点": int(as_) if done else "",
            "実施": "済" if done else "未",
            "ホーム学校": h_school, "ホーム区分": h_sq, "アウェイ学校": a_school, "アウェイ区分": a_sq,
            "出典": url,
        })
    return out


def _parse_final_standings(text: str) -> list[tuple[str, str, str]]:
    """og:description の「1位 [pts]：チーム（メモ）2位 [pts]：チーム…」を
    (順位, 勝ち点, チーム名) のリストに割る。

    「アローレ八王子U-184位」のようにチーム名の末尾の数字と次の順位表記が地続きに
    なる箇所があるため、\\d+位 の総当たり正規表現では誤読する。次に来るはずの順位
    （expected+1）の文字列そのものを探して切ることで、この曖昧さを避ける。
    """
    results: list[tuple[str, str, str]] = []
    rank = 1
    pos = 0
    while True:
        marker = f"{rank}位"
        idx = text.find(marker, pos)
        if idx == -1:
            break
        j = idx + len(marker)
        while j < len(text) and text[j] == " ":
            j += 1
        if j >= len(text) or text[j] != "[":
            break
        close = text.index("]", j)
        pts = text[j + 1:close].strip()
        k = close + 1
        if k < len(text) and text[k] in "：:":
            k += 1
        next_marker = f"{rank + 1}位"
        cutoffs = [x for x in (text.find(next_marker, k), text.find("不参加", k), text.find("※", k)) if x != -1]
        end = min(cutoffs) if cutoffs else len(text)
        team = re.sub(r"[（(][^）)]*[）)]\s*$", "", text[k:end].strip()).strip()
        team = re.sub(r"\s+", " ", team)
        results.append((str(rank), pts, team))
        pos = end
        rank += 1
    for m in re.finditer(r"不参加\s*\[([-\d]*)\]\s*[：:]\s*([^\n※]+)", text):
        team = re.sub(r"[（(][^）)]*[）)]\s*$", "", m.group(2).strip()).strip()
        team = re.sub(r"\s+", " ", team)
        results.append(("", m.group(1).strip(), team))
    return results


def standings_archive(year: int, block: str, refresh: bool) -> list[dict]:
    fname, url = ARCHIVE_PAGES[year][block]
    raw = fetch(url, RAW / fname, refresh)
    soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")
    meta = soup.find("meta", property="og:description")
    if not meta or not meta.get("content"):
        return []
    out = []
    for rank_s, pts_s, team in _parse_final_standings(meta["content"]):
        if not team:
            continue
        school, sq = _team_school(team)
        pts = _int_or_blank(pts_s) if pts_s != "-" else ""
        out.append({
            "地区": 地区, "リーグ": リーグ, "年度": year, "部": block,
            "順位": int(rank_s) if rank_s else "", "チーム": team, "学校": school, "区分": sq,
            "勝点": pts, "試合": "", "勝": "", "分": "", "敗": "",
            "得点": "", "失点": "", "得失点": "",
            "出典": url,
        })
    return out


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    """(順位表の行, 試合の行) を返す。refresh=False なら保存済みのページだけで動く。"""
    standings: list[dict] = []
    matches: list[dict] = []
    for year in (2024, 2025):
        for block in BLOCKS:
            standings += standings_archive(year, block, refresh)
    for block in BLOCKS:
        standings += standings_2026(block, refresh)
        matches += matches_2026(block, refresh)
    return standings, matches


if __name__ == "__main__":
    s, m = collect()
    print(f"standings={len(s)} matches={len(m)}")
