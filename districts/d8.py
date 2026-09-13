"""第8地区（8地区ユースリーグ）の試合を集める（notes/district_collector_spec.md 準拠）。

第8地区には地区全体の結果ページが無く、地区リーグの公式サイトも順位表を持たない。
このため以下の2校の部活動サイトから、そのページに載っている試合だけを拾う。
順位表は作れないので、collect() は常に空リストを返す（仕様で許容されている）。

- 東京電機大学高等学校サッカー部（results.html）: 「YYYY年８地区ユースリーグN部Xブロック」
  という見出しの下に、節ごとのスコアカード（div.sposcore＝日付とcaption、player×2、
  total×2）が並んでいる。電大高視点のページなので、電大高が常に左（先）に書かれている。
  ホーム/アウェイの区別は無いので、仕様の「区別が無ければ左・右」に従い、電大高を
  「ホーム」欄に置く。対象は 2026年度２部Aブロック・2025年度３部Aブロック・
  2024年度３部Bブロック（このページで確認できる、依頼にある3ブロック）。
  「順位決定戦」「最終節」など「第N節」以外のcaptionもそのまま「節」欄に入れる。
  年度をまたぐ節（例: 2024年度３部Bの最終盤が翌1月）は、節の並び順で月が急に
  小さくなった（前の節より6か月以上巻き戻った）ときだけ暦年を1つ進めて日付を作る。

- 都立東村山高等学校サッカー部ニュース: 電大高との対戦は電大高側のページに既にあるため
  重複させない。電大高側に出てこない東村山の試合（対 都立武蔵野北高校・明法高校・
  東海大菅生高校）は、東村山サッカー部ニュースの個別記事本文から拾った。これらの記事は
  表形式のスコアではなく文章なので、対戦相手とスコアはこのファイルの記述時に本文を
  読んで人手で確認済みの値を定数として持たせている（自動再抽出はしない。文章表現から
  スコアを機械的に読み取るのは誤読のリスクが高いため）。練習試合の記事（例: 6/7 対
  都立青山高校）はユースリーグの試合ではないため対象外。

Player!（web.playerapp.tokyo）はReactで描画されておりcurlでは本文が読めないため対象外。
2024年度3部A・2024年度1部（ブロック不明）・2026年度1部・2026年度2部B・2026年度3部A等、
確認済みURLが無いブロックは扱わない（data/leagues/sources.csv で「未発見」）。

保存先: raw/web/district/d8/。同じサイトへのアクセスは1.5秒以上あける。
"""

from __future__ import annotations

import re
import time
import unicodedata
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw/web/district/d8"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

地区 = "第8地区"
リーグ = "8地区ユースリーグ"

DENDAI_URL = "https://dendai-highschool-soccer.1web.jp/results.html"
DENDAI_FILE = "dendai_results.html"

# (年度, 部, 電大高サイトの見出しテキストそのまま)
DENDAI_BLOCKS = [
    (2026, "2部A", "2026年８地区ユースリーグ２部Aブロック"),
    (2025, "3部A", "2025年８地区ユースリーグ３部Aブロック"),
    (2024, "3部B", "2024年８地区ユースリーグ３部Bブロック"),
]

# 都立東村山高校サッカー部ニュース: 電大高側に出てこない2026年度2部Aの試合。
# (ファイル名, URL, 対戦相手の生表記, ホーム(東村山)得点, アウェイ得点, 日付, 節)
# スコア・対戦相手は本文（下記URL）を読んで確認済み。詳細は district/d8 の報告を参照。
HIGASHIMURAYAMA_ARTICLES = [
    (
        "higashimurayama_20260404.html",
        "https://www.metro.ed.jp/higashimurayama-h/activities/2026/04/1_1_2_1_1_1_1_1_1_1_1_1_1_1_1_1_2_1_1__51.html",
        "都立武蔵野北高校", 1, 2, "2026-04-04", "第1節",
    ),
    (
        "higashimurayama_20260419.html",
        "https://www.metro.ed.jp/higashimurayama-h/activities/2026/04/1_1_2_1_1_1_1_1_1_1_1_1_1_1_1_1_2_1_1_52.html",
        "明法高校", 0, 3, "2026-04-19", "第3節",
    ),
    (
        "higashimurayama_20260614.html",
        "https://www.metro.ed.jp/higashimurayama-h/activities/2026/06/1_1_2_1_1_1_1_1_1_1_1_1_1_1_1_1_2_1_1__56.html",
        "東海大菅生高校", 0, 0, "2026-06-14", "",
    ),
]


def fetch(url: str, path: Path, refresh: bool) -> bytes:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes()


def _team_school(name: str) -> tuple[str, str]:
    base, sq = squad_of(name)
    return normalize(base), sq


def _rows_from_heading(soup: BeautifulSoup, heading: str, year: int, block: str) -> list[dict]:
    h = next((c for c in soup.find_all("h3") if c.get_text(" ", strip=True) == heading), None)
    if h is None:
        return []
    lc = h.find_parent("div", class_="lc")
    node = lc.find_next_sibling("div", class_="lc") if lc else None
    out: list[dict] = []
    cur_year = year
    prev_month = None
    while node is not None:
        if node.find("h3"):
            break
        card = node.find("div", class_="sposcore")
        if card:
            cap = card.find("div", class_="caption")
            players = card.find_all("div", class_="player")
            totals = card.find_all("div", class_="total")
            if cap and len(players) == 2 and len(totals) == 2:
                cap_text = unicodedata.normalize("NFKC", cap.get_text(" ", strip=True))
                mo = re.search(r"(\d+)月(\d+)日", cap_text)
                if mo:
                    month, day = int(mo[1]), int(mo[2])
                    if prev_month is not None and month < prev_month - 6:
                        cur_year += 1  # 年度をまたいだ（例: 10月の次が1月）
                    prev_month = month
                    label = cap_text.split("【")[0].strip()
                    home_raw = players[0].get_text(" ", strip=True)
                    away_raw = players[1].get_text(" ", strip=True)
                    hs_text = totals[0].get_text(" ", strip=True)
                    as_text = totals[1].get_text(" ", strip=True)
                    if re.fullmatch(r"\d+", hs_text) and re.fullmatch(r"\d+", as_text):
                        h_school, h_sq = _team_school(home_raw)
                        a_school, a_sq = _team_school(away_raw)
                        out.append({
                            "地区": 地区, "リーグ": リーグ, "年度": year, "部": block,
                            "節": label, "日付": f"{cur_year}-{month:02d}-{day:02d}",
                            "ホーム": home_raw, "アウェイ": away_raw,
                            "ホーム得点": int(hs_text), "アウェイ得点": int(as_text),
                            "実施": "済",
                            "ホーム学校": h_school, "ホーム区分": h_sq,
                            "アウェイ学校": a_school, "アウェイ区分": a_sq,
                            "出典": DENDAI_URL,
                        })
        node = node.find_next_sibling("div", class_="lc")
    return out


def _dendai_matches(refresh: bool) -> list[dict]:
    raw = fetch(DENDAI_URL, RAW / DENDAI_FILE, refresh)
    soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")
    out: list[dict] = []
    for year, block, heading in DENDAI_BLOCKS:
        out += _rows_from_heading(soup, heading, year, block)
    return out


def _higashimurayama_matches(refresh: bool) -> list[dict]:
    out: list[dict] = []
    for fname, url, opponent_raw, hs, as_, date, label in HIGASHIMURAYAMA_ARTICLES:
        fetch(url, RAW / fname, refresh)  # 保存済みなら取りに行かない（鮮度保持・存在確認のため呼ぶ）
        h_school, h_sq = _team_school("東村山")
        a_school, a_sq = _team_school(opponent_raw)
        out.append({
            "地区": 地区, "リーグ": リーグ, "年度": 2026, "部": "2部A",
            "節": label, "日付": date,
            "ホーム": "東村山", "アウェイ": opponent_raw,
            "ホーム得点": hs, "アウェイ得点": as_,
            "実施": "済",
            "ホーム学校": h_school, "ホーム区分": h_sq,
            "アウェイ学校": a_school, "アウェイ区分": a_sq,
            "出典": url,
        })
    return out


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    """(順位表の行, 試合の行) を返す。順位表は作れないため常に空リスト。"""
    matches = _dendai_matches(refresh) + _higashimurayama_matches(refresh)
    return [], matches


if __name__ == "__main__":
    s, m = collect()
    print(f"standings={len(s)} matches={len(m)}")
