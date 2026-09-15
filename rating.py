"""強さの点数（Elo）の計算の本体。大会の試合に、リーグ戦（Tリーグ・プリンス関東・地区リーグ）を足して1本の時系列で計算する。

- 大会（out/matches.csv）は学校のトップチームとして扱う
- リーグ戦のチームは「学校のキー」（Aチーム）／「学校のキー（B）」（控え）／「クラブ名」を別々のチームとして持つ。
  控えの負けが学校の点数を下げないようにするため
- 並べ方: 日付順。大会で日付の書かれていない試合は、同じ大会・段階で一番早い日付（それも無ければ段階の目安日）に置き、
  同じ日の中は 大会の段階 → 回戦 → リーグの節 の順
- 年度（4月始まり）が変わるたびに、全チームの点数を平均へ戻す（CARRY）
- PK 決着は引き分け（0.5）。得点差が大きいほど大きく動かす（1点差以内 1倍・2点差 1.5倍・3点差以上 (11+差)/8 倍）

設定（K・CARRY・リーグの重み・控えの最初の点数・仮の期間）は rating_backtest.py で過去の大会の試合を当てる力を比べて決め、ADOPTED に置いた。
比べた結果は notes/rating_backtest.md。
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from build_outputs import normalize
from collect_tleague import squad_of

ROOT = Path(__file__).parent
BASE = 1500.0

STAGE_ORDER = [("関東", ""), ("総体", "支部予選"), ("総体", "一次"), ("総体", "二次"), ("選手権", "一次"), ("選手権", "二次"), ("新人戦", "")]
STAGE_DEFAULT = {0: (4, 1), 1: (4, 25), 2: (5, 10), 3: (5, 25), 4: (9, 1), 5: (10, 15), 6: (11, 15)}  # 段階ごとの目安日（月, 日）
ROUND_ORDER = {"3位決定戦": 90, "決勝": 80, "ブロック決勝": 70, "準決勝": 60, "準々決勝": 50}
# 階層ごとの最初の点数（そのチームがリーグ戦で初めて出てきたときだけ使う）
RESERVE_STEP = 100
LEVEL_PRIOR = {"プリンス": 300, "T1": 200, "T2": 150, "T3": 100, "T4": 50, "T5": 0, "1部": -50, "2部": -100, "3部": -150, "地区": -100}


@dataclass
class Config:
    k: float = 32.0
    carry: float = 0.75
    league_weight: float = 0.0  # 0 ならリーグ戦を使わない（大会だけ）
    use_tleague: bool = True
    use_district: bool = True
    use_prince: bool = True
    level_prior: bool = False
    reserve_prior: bool = False  # 控え（B・C…）は、その学校の A の点数から 1段ごとに RESERVE_STEP 点引いた値で始める
    provisional: int = 0  # 試合数がこれ未満のチームとの試合では、相手の点数を動かさない（まだ点数が当てにならないため）
    name: str = ""


@dataclass
class Game:
    date: tuple
    year: int
    kind: str  # "大会" / "T" / "地区" / "プリンス"
    a: str
    b: str
    ga: int
    gb: int
    pk: bool
    level: str = ""
    row: dict | None = field(default=None, repr=False)  # 大会の行（試合前の点数を書き戻す）


def stage_rank(r: dict) -> int:
    for i, (series, key) in enumerate(STAGE_ORDER):
        if r["大会"] == series and key in r["段階"]:
            return i
    return 99


def round_rank(r: dict) -> int:
    if r["ラウンド"] in ROUND_ORDER:
        return ROUND_ORDER[r["ラウンド"]]
    m = re.match(r"(\d+)回戦", r["ラウンド"])
    return int(m[1]) if m else 0


def md_to_date(year: int, m: int, d: int) -> tuple:
    """年度と月日から (西暦, 月, 日)。1〜3月は翌年。"""
    return (year + 1 if m < 4 else year, m, d)


def played_tournament(r: dict) -> bool:
    return r["状態"] in ("終了", "スコアのみ記載（赤線未反映）", "赤線が両側（スコアで判定）") and r["得点A"] != "" and r["得点B"] != ""


def tournament_games(rows: list[dict]) -> list[Game]:
    groups = defaultdict(list)
    for r in rows:
        groups[(int(r["年度"]), r["大会"], r["段階"], r["地区・支部"])].append(r)
    games = []
    for (year, *_), rs in groups.items():
        dated = []
        for r in rs:
            m = re.match(r"(\d{1,2})/(\d{1,2})", r["日付"] or "")
            r["_date"] = md_to_date(year, int(m[1]), int(m[2])) if m else None
            if r["_date"]:
                dated.append(r["_date"])
        first = min(dated) if dated else None
        for r in rs:
            if not played_tournament(r):
                continue
            a, b = normalize(r["チームA"]), normalize(r["チームB"])
            if not a or not b:
                continue
            sr = stage_rank(r)
            date = r["_date"] or first or md_to_date(year, *STAGE_DEFAULT.get(sr, (4, 1)))
            pk = r["PK_A"] != "" and r["PK_B"] != ""
            r["kA"], r["kB"] = a, b
            games.append(Game((*date, 0, sr, round_rank(r)), year, "大会", a, b, int(r["得点A"]), int(r["得点B"]), pk, row=r))
    return games


def team_key(name: str, school: str, squad: str, schools: set) -> str:
    """リーグ戦のチームのキー。学校のAチーム＝学校のキー、控え＝「学校（B）」、クラブ＝名前。"""
    if school in schools:
        return school if squad == "A" else f"{school}（{squad}）"
    return re.sub(r"\s+", "", name)


def level_of(league: str, div: str) -> str:
    if league.startswith("プリンス"):
        return "プリンス"
    if re.fullmatch(r"T[1-5]", league):
        return league
    m = re.match(r"([1-3])部", div or "")
    return f"{m[1]}部" if m else "地区"


def league_games(cfg: Config, schools: set) -> list[Game]:
    srcs = []
    if cfg.use_tleague:
        srcs.append(("T", ROOT / "data/leagues/tleague_matches.csv"))
    if cfg.use_district:
        srcs.append(("地区", ROOT / "data/leagues/district_matches.csv"))
    if cfg.use_prince:
        srcs.append(("プリンス", ROOT / "data/leagues/prince_kanto1_2026_matches.csv"))
    games = []
    for kind, path in srcs:
        if not path.exists():
            continue
        for r in csv.DictReader(path.open(encoding="utf-8-sig")):
            if r["実施"] != "済" or r["ホーム得点"] == "" or r["アウェイ得点"] == "":
                continue
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", r.get("日付") or "")
            year = int(r["年度"])
            if not m:
                continue  # 日付の無いリーグ戦は時系列に置けないので使わない
            if kind == "プリンス":
                hb, hs = squad_of(r["ホーム"])
                ab, as_ = squad_of(r["アウェイ"])
                hsch, asch = normalize(hb), normalize(ab)
            else:
                hsch, hs, asch, as_ = r["ホーム学校"], r["ホーム区分"], r["アウェイ学校"], r["アウェイ区分"]
            a = team_key(r["ホーム"], hsch, hs, schools)
            b = team_key(r["アウェイ"], asch, as_, schools)
            if not a or not b or a == b:
                continue
            sec = int(re.sub(r"\D", "", str(r.get("節") or "")) or 0)
            lvl = level_of(r.get("リーグ", ""), r.get("部") or r.get("ブロック") or "")
            games.append(Game((int(m[1]), int(m[2]), int(m[3]), 1, 0, sec), year, kind, a, b, int(r["ホーム得点"]), int(r["アウェイ得点"]), False, level=lvl))
    return games


# 採用した設定（2026-09-15。rating_backtest.py で比べて一番当たった組み合わせ。結果は notes/rating_backtest.md）
ADOPTED = Config(k=88, carry=1.0, league_weight=0.5, reserve_prior=True, provisional=10, level_prior=True,
                 name="K88・持ち越し1.0・リーグ重み0.5（全リーグ）・控えの最初の点数・仮の期間10試合・階層で最初の点数")


def win_prob(ea: float, eb: float) -> float:
    return 1 / (1 + 10 ** ((eb - ea) / 400))


def margin_mult(margin: int) -> float:
    return 1.0 if margin <= 1 else 1.5 if margin == 2 else (11 + margin) / 8


def run(tournament_rows: list[dict], cfg: Config, eval_years: tuple = ()) -> dict:
    """点数を計算する。eval_years の大会の試合について、試合前の見込みと結果を集める（当たり具合の比較用）。"""
    schools = {normalize(r[c]) for r in tournament_rows for c in ("チームA", "チームB")} - {""}
    games = tournament_games(tournament_rows)
    if cfg.league_weight > 0:
        games += league_games(cfg, schools)
    games.sort(key=lambda g: g.date)
    elo: dict = defaultdict(lambda: BASE)
    seen: set = set()
    hist: dict = defaultdict(dict)
    n_games: dict = defaultdict(int)
    preds = []
    year = None
    for g in games:
        if g.year != year:
            if year is not None:
                for k in list(elo):
                    hist[k][year] = round(elo[k])
                    elo[k] = BASE + (elo[k] - BASE) * cfg.carry
            year = g.year
        for t in (g.a, g.b):
            if t not in seen:
                seen.add(t)
                m = re.fullmatch(r"(.+)（([B-J])）", t)
                if cfg.reserve_prior and m and m[1] in seen:
                    elo[t] = elo[m[1]] - RESERVE_STEP * (ord(m[2]) - ord("A"))
                elif cfg.level_prior and g.kind != "大会":
                    elo[t] = BASE + LEVEL_PRIOR.get(g.level, 0)
        ea, eb = elo[g.a], elo[g.b]
        s = 0.5 if g.pk else 1.0 if g.ga > g.gb else 0.0 if g.ga < g.gb else 0.5
        p = win_prob(ea, eb)
        if g.kind == "大会":
            if g.row is not None:
                g.row["_eloA"], g.row["_eloB"] = round(ea), round(eb)
            if g.year in eval_years:
                preds.append((p, s, n_games[g.a], n_games[g.b]))
        w = 1.0 if g.kind == "大会" else cfg.league_weight
        d = cfg.k * w * margin_mult(abs(g.ga - g.gb)) * (s - p)
        # 仮の期間: 試合数の少ない相手との試合では、こちらの点数は動かさない（相手の点数だけ動く）
        pa = cfg.provisional and n_games[g.b] < cfg.provisional
        pb = cfg.provisional and n_games[g.a] < cfg.provisional
        elo[g.a] += 0 if pa and not pb else d
        elo[g.b] -= 0 if pb and not pa else d
        n_games[g.a] += 1
        n_games[g.b] += 1
    if year is not None:
        for k in list(elo):
            hist[k][year] = round(elo[k])
    return {"elo": dict(elo), "hist": {k: dict(v) for k, v in hist.items()}, "n_games": dict(n_games), "preds": preds, "schools": schools}
