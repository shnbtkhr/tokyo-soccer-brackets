"""段階1の受け入れテスト T1〜T6（notes/dataset-migration-phase1.md）。

  uv run python -m pytest tests/test_dataset_roundtrip.py -v

Vault（dataset.paths.dataset_dir()）に9表が書き出し済みであることを前提にする
（先に `uv run python -m dataset.export` を実行しておく）。
"""

from __future__ import annotations

import csv
import io
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_team  # noqa: E402
import leagues  # noqa: E402
import rating  # noqa: E402
from dataset import check, common, legacy, paths  # noqa: E402

TOURNAMENT_COLS = [
    "年度", "大会", "段階", "地区・支部", "ブロック", "ページ", "ラウンド", "日付", "試合番号",
    "チームA", "チームB", "スコア", "得点A", "得点B", "PK_A", "PK_B", "前後半", "勝者", "備考",
    "チームA_正規化", "チームB_正規化", "出典PDF",
]


def _dataset_present() -> bool:
    d = paths.dataset_dir()
    return all((d / name).exists() for name in (
        "schools.csv", "matches.csv", "competitions.csv", "teams.csv", "sources.csv",
    ))


pytestmark = pytest.mark.skipif(not _dataset_present(), reason="Vault に9表がまだ書き出されていない（先に dataset.export を実行）")


# --------------------------------------------------------------------------- T1


def test_t1_check_passes():
    problems = check.run(verbose=False)
    assert problems == [], f"dataset.check に {len(problems)} 件の問題: {problems[:20]}"


# --------------------------------------------------------------------------- T2


def test_t2_tournament_roundtrip():
    old_rows = common.read_csv(ROOT / "out/matches.csv")
    new_rows = legacy.tournament_rows()

    assert len(old_rows) == len(new_rows), f"行数が違う: 旧{len(old_rows)} 新{len(new_rows)}"

    def fingerprint(rows):
        c = Counter()
        for r in rows:
            key = tuple(r[c_] for c_ in TOURNAMENT_COLS) + (analyze_team.played(r),)
            c[key] += 1
        return c

    old_fp = fingerprint(old_rows)
    new_fp = fingerprint(new_rows)
    assert old_fp == new_fp, "行の内容（指定列 + played()）が一致しない"


# --------------------------------------------------------------------------- T3


def test_t3_league_roundtrip():
    orig = leagues.load_all()
    new = legacy.league_rows()
    assert orig == new


# --------------------------------------------------------------------------- T4


FEED_TO_PATH = {
    "Tリーグ公式": rating.ROOT / "data/leagues/tleague_matches.csv",
    "goalnote": rating.ROOT / "data/leagues/district_matches.csv",
    "プリンス": rating.ROOT / "data/leagues/prince_kanto1_2026_matches.csv",
}
PATH_TO_FEED = {v: k for k, v in FEED_TO_PATH.items()}


def test_t4_rating_roundtrip(monkeypatch):
    tournament_rows = analyze_team.load_matches()
    baseline = rating.run(tournament_rows, rating.ADOPTED)

    real_open = Path.open

    def fake_open(self, *args, **kwargs):
        feed = PATH_TO_FEED.get(self)
        if feed is None:
            return real_open(self, *args, **kwargs)
        rows = legacy.feed_rows(feed)
        buf = io.StringIO()
        if rows:
            fieldnames = list(rows[0].keys())
            w = csv.DictWriter(buf, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        buf.seek(0)
        return buf

    monkeypatch.setattr(Path, "open", fake_open)

    tournament_rows2 = analyze_team.load_matches()  # out/matches.csv は差し替えていないので同じ内容
    replayed = rating.run(tournament_rows2, rating.ADOPTED)

    assert replayed["elo"] == baseline["elo"]
    assert replayed["hist"] == baseline["hist"]
    assert replayed["n_games"] == baseline["n_games"]


# --------------------------------------------------------------------------- T5


STANDINGS_FILES = [
    ("data/leagues/district_standings.csv", "リーグ", "部", "区分", "部"),
    ("data/leagues/tleague_standings.csv", "リーグ", None, "区分", "ブロック"),
    ("data/leagues/tleague_history_standings.csv", "リーグ", None, None, None),
    ("data/leagues/prince_kanto1_2026_standings.csv", "リーグ", None, None, None),
]


def test_t5_standings_roundtrip():
    a = legacy.Adapter()
    checked = 0
    missing = []
    for fname, leaguecol, divcol, squadcol, blockcol in STANDINGS_FILES:
        for r in common.read_csv(ROOT / fname):
            season = int(r["年度"])
            league_name = r[leaguecol]
            div = (r.get(divcol) or "") if divcol else ""
            block = (r.get(blockcol) or "").strip() if blockcol else ""
            if block.endswith("ブロック"):
                block = block[: -len("ブロック")]
            school = r["学校"]
            squad = (r.get(squadcol) or "A") if squadcol else "A"
            new_row = legacy.find_standing(a, season, league_name, div, block, school, squad)
            if new_row is None:
                missing.append((fname, r["年度"], league_name, school, squad))
                continue
            checked += 1

            def same(new_val, old_val):
                # 順位表の行によっては値が空欄（試合数0の新規参加チーム等）。空欄は空欄どうしで一致すればよい
                if old_val == "":
                    return new_val == "" or new_val is None
                return new_val != "" and new_val is not None and int(new_val) == int(old_val)

            assert same(new_row["rank"], r["順位"]), (fname, r, new_row)
            assert same(new_row["played"], r["試合"]), (fname, r, new_row)
            assert same(new_row["won"], r["勝"]), (fname, r, new_row)
            assert same(new_row["drawn"], r["分"]), (fname, r, new_row)
            assert same(new_row["lost"], r["敗"]), (fname, r, new_row)
            assert same(new_row["goals_for"], r["得点"]), (fname, r, new_row)
            assert same(new_row["goals_against"], r["失点"]), (fname, r, new_row)
            assert same(new_row["points"], r["勝点"]), (fname, r, new_row)
            # 2026-10-01、standings.raw_team 追加（出典そのままの「チーム」表記）。
            assert new_row["raw_team"] == r["チーム"], (fname, r, new_row)

    assert not missing, f"{len(missing)} 件、standings.csv から復元できない行がある（例: {missing[:10]}）"
    assert checked > 0


# --------------------------------------------------------------------------- T6


def test_t6_export_is_idempotent():
    from dataset import export

    d = paths.dataset_dir()
    before = {name: (d / name).read_bytes() for name in paths.TABLES}
    export.run(verbose=False)
    after = {name: (d / name).read_bytes() for name in paths.TABLES}
    changed = [name for name in paths.TABLES if before[name] != after[name]]
    assert not changed, f"2回目の書き出しでファイルが変わった: {changed}"
