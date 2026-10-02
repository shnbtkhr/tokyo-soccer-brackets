"""段階1の受け入れテスト T1〜T6（notes/dataset-migration-phase1.md）と、名寄せ（2026-10-02）の T7。

  uv run python -m pytest tests/test_dataset_roundtrip.py -v

Vault（dataset.paths.dataset_dir()）に表が書き出し済みであることを前提にする
（先に `uv run python -m dataset.export` を実行しておく）。

T2〜T5 は「旧データを損なわず表へ変換できているか」を確かめるテストなので、名寄せを当てない
書き出し（export.run(apply_merges=False)。一時フォルダへ書く）に対して、旧データを直接読む
モード（SOCCER_SOURCE=legacy）で走らせる。名寄せ後の Vault は旧データと一致しなくてよい
（試合の match_id・学校の割り当てが変わるのが目的のため）。
T1・T6・T7 は名寄せ後の Vault に対して走らせる。
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


@pytest.fixture(scope="session")
def unmerged_dir(tmp_path_factory):
    """名寄せを当てずに書き出した表（T2〜T5 用）。school_id・source_id は Vault から引き継ぐ。"""
    from dataset import export

    d = tmp_path_factory.mktemp("unmerged")
    export.run(verbose=False, out_dir=d, apply_merges=False)
    return d


@pytest.fixture
def legacy_source(monkeypatch):
    """読む側（leagues・analyze_team・rating）が実物の out/・data/ を読むようにする。"""
    monkeypatch.setenv("SOCCER_SOURCE", "legacy")


pytestmark = pytest.mark.skipif(not _dataset_present(), reason="Vault に9表がまだ書き出されていない（先に dataset.export を実行）")


# --------------------------------------------------------------------------- T1


def test_t1_check_passes():
    problems = check.run(verbose=False)
    assert problems == [], f"dataset.check に {len(problems)} 件の問題: {problems[:20]}"


# --------------------------------------------------------------------------- T2


def test_t2_tournament_roundtrip(unmerged_dir, legacy_source):
    old_rows = common.read_csv(ROOT / "out/matches.csv")
    new_rows = legacy.tournament_rows(unmerged_dir)

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


def test_t3_league_roundtrip(unmerged_dir, legacy_source):
    orig = leagues.load_all()
    new = legacy.league_rows(unmerged_dir)
    assert orig == new


# --------------------------------------------------------------------------- T4


FEED_TO_PATH = {
    "Tリーグ公式": rating.ROOT / "data/leagues/tleague_matches.csv",
    "goalnote": rating.ROOT / "data/leagues/district_matches.csv",
    "プリンス": rating.ROOT / "data/leagues/prince_kanto1_2026_matches.csv",
}
PATH_TO_FEED = {v: k for k, v in FEED_TO_PATH.items()}


def test_t4_rating_roundtrip(monkeypatch, unmerged_dir, legacy_source):
    tournament_rows = analyze_team.load_matches()
    baseline = rating.run(tournament_rows, rating.ADOPTED)

    real_open = Path.open

    def fake_open(self, *args, **kwargs):
        feed = PATH_TO_FEED.get(self)
        if feed is None:
            return real_open(self, *args, **kwargs)
        rows = legacy.feed_rows(feed, unmerged_dir)
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


def test_t5_standings_roundtrip(unmerged_dir):
    a = legacy.Adapter(unmerged_dir)
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
    export.run(verbose=False)  # 名寄せあり（既定）。school_merges.csv は入力なので書き換えない
    after = {name: (d / name).read_bytes() for name in paths.TABLES}
    changed = [name for name in paths.TABLES if before[name] != after[name]]
    assert not changed, f"2回目の書き出しでファイルが変わった: {changed}"


# --------------------------------------------------------------------------- T7


def test_t7_merges_applied(unmerged_dir):
    """名寄せを当てた Vault：試合の総数が変わらず、まとめた学校をどの表も参照せず、
    すべての variant_key がまとめ先の学校に解決される。"""
    d = paths.dataset_dir()
    tables = {name: common.read_csv(d / name) for name in paths.TABLES}
    merges = tables["school_merges.csv"]
    assert merges, "school_merges.csv が空"

    # (a) 保存則：（名寄せ後の試合数）＋（名寄せで 重複 になった試合数）＝（名寄せ前の試合数）。
    #     match_sources の行数は変わらない（落ちた試合も出典の行として残る＝来歴を失わない）
    um = common.read_csv(unmerged_dir / "matches.csv")
    ums = common.read_csv(unmerged_dir / "match_sources.csv")
    n_dup_before = sum(1 for r in ums if r["role"] == "重複")
    n_dup_after = sum(1 for r in tables["match_sources.csv"] if r["role"] == "重複")
    turned = n_dup_after - n_dup_before
    assert turned >= 0
    assert len(tables["matches.csv"]) + turned == len(um), (len(tables["matches.csv"]), turned, len(um))
    assert len(tables["match_sources.csv"]) == len(ums), (len(tables["match_sources.csv"]), len(ums))
    assert len({r["match_id"] for r in tables["matches.csv"]}) == len(tables["matches.csv"]), "match_id が重複している"
    # すべての match_sources が、実在する試合を指す
    ids = {r["match_id"] for r in tables["matches.csv"]}
    assert not [r for r in tables["match_sources.csv"] if r["match_id"] not in ids], "match_sources が存在しない試合を指す"

    # (b) まとめた学校を、どの表も参照しない
    school_by_id = {r["school_id"]: r for r in tables["schools.csv"]}
    merged_ids = {r["school_id"] for r in tables["schools.csv"] if r["merged_into"]}
    assert len(merged_ids) == len(merges)
    team_school = {r["team_id"]: r["school_id"] for r in tables["teams.csv"]}
    assert not [t for t, s in team_school.items() if s in merged_ids], "teams.csv がまとめた学校を参照している"
    assert not [r["name"] for r in tables["school_names.csv"] if r["school_id"] in merged_ids], "school_names.csv がまとめた学校を参照している"
    for r in tables["matches.csv"]:
        for side in ("team_a", "team_b", "winner"):
            if r[side]:
                assert team_school[r[side]] not in merged_ids, (side, r["match_id"])
    for r in tables["standings.csv"]:
        assert team_school[r["team_id"]] not in merged_ids, r["team_id"]

    # (c) すべての variant_key が、まとめ先の学校（merged_into の行き先）に解決される
    by_key = {r["legacy_key"]: r for r in tables["schools.csv"]}
    for m in merges:
        v, c = by_key[m["variant_key"]], by_key[m["canonical_key"]]
        assert v["merged_into"] == c["school_id"], m
        assert not c["merged_into"], m
        assert c["school_id"] in school_by_id
    a = legacy.Adapter(d)
    # 実体化の側：まとめ先の legacy_key と区分でチームが引ける（squad 指定があれば、その区分）
    for m in merges:
        c = by_key[m["canonical_key"]]
        squads = {t["squad"] for t in tables["teams.csv"] if t["school_id"] == c["school_id"]}
        if m["squad"]:
            assert m["squad"] in squads, m
        assert a.team_id_for(c["legacy_key"], m["squad"] or "A") or not m["squad"], m
