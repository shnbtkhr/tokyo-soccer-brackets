"""第3地区（第3地区ユースリーグ）の順位表と試合を集める。決まりは notes/district_collector_spec.md。

2026年度: ws.eniblo.com（7ブロック: 1部・2部A・2部B・3部A・3部B・3部C・3部D）。勝敗表（グリッド）と順位表（ranks.html）の両方が公開されている。
2024年度: junior-soccer.jp の勝敗グリッド（2部A・3部C・3部D。順位表ページは無いので試合から計算）と、
          juniorsoccer-news.com のブログ記事（1部・2部B・3部A・3部B。最終順位のみで試合ごとの結果は無い）。
2025年度: 公式Wix（kmnkzt1530.wixsite.com）のブログ記事に最終結果の一部（優勝・準優勝）だけが載っている。試合ごとの結果・順位表は未特定のため、判明した順位のみを記録する。

取得したページは raw/web/district/d3/ に保存し、refresh=True か未保存のときだけ取りに行く（同じサイトへは1.5秒以上あける）。
"""

from __future__ import annotations

import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw/web/district/d3"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CHIKU = "第3地区"
LEAGUE = "第3地区ユースリーグ"

# 2026年度: ws.eniblo.com の7ブロック（data/leagues/sources.csv で確認済みのURL）
ENIBLO_2026 = [
    ("1部", "1bu", "https://ws.eniblo.com/YZezPNf8HYgIbzABs3/"),
    ("2部A", "2buA", "https://ws.eniblo.com/6TRkWT3l4eqWypXPEz/"),
    ("2部B", "2buB", "https://ws.eniblo.com/WNlqrd5NRPqtv9vxKw/"),
    ("3部A", "3buA", "https://ws.eniblo.com/vXwlUaacWCy9NaZ3D2/"),
    ("3部B", "3buB", "https://ws.eniblo.com/6LfQ0YtO939PdhyS1P/"),
    ("3部C", "3buC", "https://ws.eniblo.com/4wp4WRHRPP2JDy9i58/"),
    ("3部D", "3buD", "https://ws.eniblo.com/79SqSF8lncWz80vpmO/"),
]

# 2024年度: junior-soccer.jp の勝敗グリッド（順位表ページは無いので試合から計算する）
MATRIX_2024 = [
    ("2部A", "47948", "https://junior-soccer.jp/kanto/tokyo/league/table/47948"),
    ("3部C", "50057", "https://junior-soccer.jp/kanto/tokyo/league/table/50057"),
    ("3部D", "47953", "https://junior-soccer.jp/kanto/tokyo/league/table/47953"),
]

# 2024年度: juniorsoccer-news.com のブログ記事（最終順位のみ。試合ごとの結果は無い）
NEWS_2024_URL = "https://www.juniorsoccer-news.com/post-1629009"
NEWS_2024_PATH = RAW / "juniorsoccer-news_1629009.html"
NEWS_2024_BLOCKS = ["1部", "2部B", "3部A", "3部B"]

# 2025年度: 公式Wixブログ（最終結果の一部のみ）
WIX_2025_URL = "https://kmnkzt1530.wixsite.com/youthleage/single-post/" + urllib.parse.quote("2025年度リーグ戦結果")
WIX_2025_PATH = RAW / "post_2025_E5_B9_B4_E5_BA_A6_E3_83_AA_E3_83_BC_E3_82_B0_E6_88_A6_E7_B5_90_E6_9E_9C.html"

SCORE_RE = re.compile(r"^(\d+)([○●△])(\d+)$")


def fetch(url: str, path: Path, refresh: bool) -> str:
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        time.sleep(1.5)
    return path.read_bytes().decode("utf-8", "replace")


def team_fields(name: str) -> dict:
    base, sq = squad_of(name)
    return {"チーム": name, "学校": normalize(base), "区分": sq}


def std_row(year: int, bu: str, rank, name: str, w="", d="", l="", gf="", ga="", src: str = "") -> dict:
    row = {"地区": CHIKU, "リーグ": LEAGUE, "年度": year, "部": bu, "順位": rank, "出典": src}
    row.update(team_fields(name))
    ten = "" if w == "" or d == "" else 3 * w + d
    shiai = "" if w == "" or d == "" or l == "" else w + d + l
    row["勝点"], row["試合"], row["勝"], row["分"], row["敗"] = ten, shiai, w, d, l
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


# ---------- 2026年度: ws.eniblo.com ----------

def eniblo_ranks(html: str, bu: str, src: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="rank_table")
    out = []
    for tr in table.find("tbody").find_all("tr"):
        c = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(c) < 9:
            continue
        rank, name, w, d, l, ten, gf, ga = int(c[0]), c[1], int(c[2]), int(c[3]), int(c[4]), int(c[5]), int(c[6]), int(c[7])
        row = std_row(2026, bu, rank, name, w, d, l, gf, ga, src)
        row["勝点"] = ten  # ページの勝点をそのまま使う（3*勝+分と食い違えばcollect()側の検算で分かる）
        out.append(row)
    return out


def eniblo_matches(html: str, bu: str, src: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="result_table")
    headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")][1:]
    out = []
    for i, tr in enumerate(table.find("tbody").find_all("tr")):
        tds = tr.find_all("td")
        for j, td in enumerate(tds[1:]):
            if j <= i:
                continue
            score = td.find("span", class_="score_text")
            if not score:
                continue
            hs, as_ = re.split(r"\s*-\s*", score.get_text(strip=True))
            out.append(match_row(2026, bu, headers[i], headers[j], int(hs), int(as_), "済", src))
    return out


# ---------- 2024年度: junior-soccer.jp の勝敗グリッド（試合から計算） ----------

def matrix_table(html: str, bu: str) -> tuple[list[str], list[list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    heading_prefix = f"【{bu}】"
    table = None
    for t in soup.find_all("table"):
        h = t.find_previous(["h1", "h2", "h3", "h4"])
        if h and heading_prefix in h.get_text(strip=True):
            table = t
            break
    if table is None:
        table = soup.find_all("table")[0]
    rows = table.find_all("tr")[1:]  # 先頭行はヘッダ（連結されたチーム名）なので飛ばす
    teams, cells = [], []
    for tr in rows:
        c = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if not c or not c[0]:
            continue
        teams.append(c[0])
        cells.append(c[1:])
    return teams, cells


def matrix_to_rows(year: int, bu: str, teams: list[str], cells: list[list[str]], src: str) -> tuple[list[dict], list[dict]]:
    standings, matches = [], []
    n = len(teams)
    for i, name in enumerate(teams):
        w = d = l = gf = ga = 0
        for j in range(n):
            if j == i or j >= len(cells[i]):
                continue
            m = SCORE_RE.match(cells[i][j])
            if not m:
                continue
            a, sym, b = int(m[1]), m[2], int(m[3])
            gf += a
            ga += b
            if sym == "○":
                w += 1
            elif sym == "△":
                d += 1
            else:
                l += 1
            if j > i:
                matches.append(match_row(year, bu, name, teams[j], a, b, "済", src))
        rank_txt = cells[i][-1] if cells[i] else ""
        rank = int(rank_txt) if rank_txt.isdigit() else ""
        standings.append(std_row(year, bu, rank, name, w, d, l, gf, ga, src + "（試合から計算）"))
    return standings, matches


# ---------- 2024年度: juniorsoccer-news.com（最終順位のみ） ----------

def news_2024_standings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article") or soup.body
    text = art.get_text("", strip=True)
    out = []
    for bu in NEWS_2024_BLOCKS:
        m = re.search(re.escape(bu) + r"　最終結果掲載！(.*?)リーグ戦績表", text)
        if not m:
            continue
        for chunk in m.group(1).split("、"):
            mm = re.match(r"^(\d+)位：(.+)$", chunk)
            if not mm:
                continue
            rank = int(mm[1])
            name = re.sub(r"（[^）]*）$", "", mm[2]).strip()
            if not name:
                continue
            out.append(std_row(2024, bu, rank, name, src=NEWS_2024_URL))
    return out


# ---------- 2025年度: 公式Wixブログ（優勝・準優勝のみ） ----------

WIX_2025_PATTERNS = [
    ("1部", re.compile(r"1部リーグ優勝(?:\([^)]*\))?\s*(\S+)")),
    ("2部A", re.compile(r"2部Aリーグ優勝\s*(\S+?)\s*2位\s*(\S+)")),
    ("2部B", re.compile(r"2部Bリーグ優勝\s*(\S+?)\s*2位\s*(\S+)")),
    ("3部A", re.compile(r"3部A優勝\s*(\S+)")),
    ("3部B", re.compile(r"3部B優勝\s*(\S+)")),
    ("3部C", re.compile(r"3部C優勝\s*(\S+)")),
    ("3部D", re.compile(r"3部D優勝\s*(\S+)")),
]


def wix_2025_standings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article") or soup.body
    text = unicodedata.normalize("NFKC", art.get_text("\n", strip=True))
    text = "".join(text.split("\n"))  # Wixは要素ごとに改行が入るため連結してから正規表現で拾う
    out = []
    for bu, pat in WIX_2025_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        teams = [t for t in m.groups() if t]
        for rank, name in enumerate(teams, start=1):
            out.append(std_row(2025, bu, rank, name, src=WIX_2025_URL))
    return out


def collect(refresh: bool = False) -> tuple[list[dict], list[dict]]:
    standings: list[dict] = []
    matches: list[dict] = []

    for bu, slug, url in ENIBLO_2026:
        top_html = fetch(url, RAW / f"eniblo_{slug}.html", refresh)
        ranks_html = fetch(url + "ranks.html", RAW / f"eniblo_{slug}_ranks.html", refresh)
        standings += eniblo_ranks(ranks_html, bu, url + "ranks.html")
        matches += eniblo_matches(top_html, bu, url)

    for bu, ident, url in MATRIX_2024:
        html = fetch(url, RAW / f"junior-soccer_{ident}.html", refresh)
        teams, cells = matrix_table(html, bu)
        s, m = matrix_to_rows(2024, bu, teams, cells, url)
        standings += s
        matches += m

    news_html = fetch(NEWS_2024_URL, NEWS_2024_PATH, refresh)
    standings += news_2024_standings(news_html)

    wix_html = fetch(WIX_2025_URL, WIX_2025_PATH, refresh)
    standings += wix_2025_standings(wix_html)

    return standings, matches


if __name__ == "__main__":
    s, m = collect()
    print(f"順位表 {len(s)} 行・試合 {len(m)} 行")
