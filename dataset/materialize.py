"""Vault の9表 -> 旧来の形のファイル（実体化）。out/legacy/ に書き出す。

  uv run python -m dataset.materialize

読む側（analyze_team.py・rating.py・leagues.py・...）は dataset.source.path(...) 経由でこちらを読む
（SOCCER_SOURCE=legacy なら実物の out/・data/ を読む。既定ではここが書いたファイルを読む）。

実体化するファイル:
  out/legacy/out/matches.csv                               <- legacy.tournament_rows()
  out/legacy/out/teams.csv                                 <- build_outputs.build_teams(上と同じ行)
  out/legacy/out/scout/member_areas.json                   <- schools.csv（district 列が埋まっている行）
  out/legacy/data/leagues/district_stars_matches.csv       <- 星取表（本ファイルの star_rows）
  out/legacy/data/leagues/district_matches.csv             <- legacy.feed_rows("goalnote")
  out/legacy/data/leagues/tleague_matches.csv              <- legacy.feed_rows("Tリーグ公式")
  out/legacy/data/leagues/tleague_archive_matches.csv      <- Tリーグ過去（PDF）
  out/legacy/data/leagues/tleague_history_matches.csv      <- Tリーグ過去（高校サッカードットコム）
  out/legacy/data/leagues/prince_kanto1_2026_matches.csv   <- legacy.feed_rows("プリンス")
  out/legacy/data/leagues/district_standings.csv
  out/legacy/data/leagues/tleague_standings.csv
  out/legacy/data/leagues/tleague_history_standings.csv
  out/legacy/data/leagues/prince_kanto1_2026_standings.csv

2026-10-01、段階2の比較で見つかった3つのギャップを SCHEMA.md 側で埋めた（schools.roster_name・
standings.raw_team・match_sources.src_row を大会の試合にも追加）。これにより旧来の形への
実体化はほぼ完全になった（out/matches.csv の並びも含めて厳密に復元できる）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_outputs  # noqa: E402
from dataset import common, legacy, paths  # noqa: E402

OUT = ROOT / "out/legacy"

report: dict = {"notes": []}


def note(msg: str) -> None:
    report["notes"].append(msg)
    print(f"[materialize] {msg}")


# ---------------------------------------------------------------------------
# out/matches.csv・out/teams.csv
# ---------------------------------------------------------------------------

OUT_MATCHES_COLS = [
    "年度", "大会", "段階", "地区・支部", "ブロック", "ページ", "ラウンド", "列", "日付", "試合番号",
    "チームA", "チームB", "スコア", "得点A", "得点B", "PK_A", "PK_B", "前後半", "勝者", "状態", "備考",
    "チームA_正規化", "チームB_正規化", "出典PDF", "PDFタイトル",
]

OUT_TEAMS_COLS = ["年度", "大会", "段階", "地区・支部", "学校", "学校_正規化", "試合数", "勝", "PK勝", "PK負", "敗", "不戦勝", "最終到達", "戦績"]


def materialize_tournament(a: legacy.Adapter) -> list[dict]:
    rows = legacy.tournament_rows(paths.dataset_dir())
    for r in rows:
        r["列"] = ""  # 読む側は使わない（build_outputs.py の PDF 読み取り用の内部列）
    # tournament_rows() は出典PDFのURLしか持たないので、sources.csv から PDFタイトルを引く
    url_to_title = {s["url"]: s.get("title", "") for s in a.sources_by_id.values()}
    for r in rows:
        r["PDFタイトル"] = url_to_title.get(r["出典PDF"], "")

    # 行の並びを、元の out/matches.csv と同じにする。2026-10-01、match_sources.src_row が
    # 大会の試合にも入った（out/matches.csv での1始まりの行番号そのもの）。legacy.tournament_rows()
    # は a.matches を comp.format=="トーナメント" で絞って1対1で rows を作るので、同じ絞り方で
    # a.matches をもう一度たどれば rows と match_id が対応づく（以前は src_row が無く、
    # 出典PDFの登場順＋ページ＋ラウンド進行順で近似していたが、今はこれで正確に復元できる）。
    tournament_matches = [
        m for m in a.matches
        if (comp := a.comps_by_id.get(m["comp_id"])) and comp["format"] == "トーナメント"
    ]
    if len(tournament_matches) != len(rows):
        raise ValueError(f"tournament_rows()（{len(rows)}件）と大会の試合数（{len(tournament_matches)}件）が食い違う")
    for r, m in zip(rows, tournament_matches):
        ps = a.primary_source_by_match.get(m["match_id"], {})
        r["_src_row"] = int(ps["src_row"]) if ps.get("src_row") not in (None, "") else 0
    rows.sort(key=lambda r: r["_src_row"])
    for r in rows:
        del r["_src_row"]

    rewrite_merged_raw_names(rows)
    common.write_csv(OUT / "out/matches.csv", OUT_MATCHES_COLS, rows)
    return rows


def rewrite_merged_raw_names(rows: list[dict]) -> None:
    """名寄せ（school_merges.csv）でまとめた学校の生の校名を、まとめ先の legacy_key に書き換える。

    読む側（rating.py・analyze_team.py・build_*.py）は「チームA」「チームB」「勝者」の生の校名を
    自分で normalize() し直す（「チームA_正規化」の列は見ない）。そのため「正規化」の列だけをまとめ先に
    しても、点数の計算は variant の学校を別の学校として数え続ける。ここで生の校名そのものを
    まとめ先のキーに置き換えれば、読む側のコードを変えずに1校として扱われる。
    原文の書き方は Vault の表（matches.csv の raw_a・raw_b）に残っている。実体化したファイルだけの書き換え。
    """
    merges = common.read_csv(paths.dataset_dir() / "school_merges.csv")
    variants = {m["variant_key"] for m in merges}
    if not variants:
        return
    n = 0
    for r in rows:
        for side, key_col in (("A", "チームA_正規化"), ("B", "チームB_正規化")):
            raw = r[f"チーム{side}"]
            if build_outputs.normalize(raw) in variants and r[key_col]:
                if r["勝者"] == raw:
                    r["勝者"] = r[key_col]
                r[f"チーム{side}"] = r[key_col]
                n += 1
    note(f"名寄せ：大会の生の校名 {n}件をまとめ先のキーに置き換えた")


def materialize_teams(tournament_rows: list[dict]) -> None:
    teams = build_outputs.build_teams(tournament_rows)
    common.write_csv(OUT / "out/teams.csv", OUT_TEAMS_COLS, teams)


# ---------------------------------------------------------------------------
# out/scout/member_areas.json
# ---------------------------------------------------------------------------


# schools.csv の note 列は他の目的（区分未確認・別ID疑い・roster_only の注記）にも使い回すため、
# それらに一致する内容は加盟校一覧由来の note として復元しない（export.py が実際に書く固定文言）
_NON_ROSTER_NOTE_PREFIXES = ("区分未確認", "加盟校一覧のみ（試合記録なし）", "移行時点では別ID")


def materialize_member_areas(a: legacy.Adapter) -> None:
    """2026-10-01、schools.roster_name の追加で、加盟校一覧（試合0件の学校も含む）を
    schools.csv だけから完全に復元できるようになった（以前は district 列・legacy_key だけを
    使っていたため、0試合の加盟校2校が再現できなかった）。"""
    out = {}
    for sc in a.schools_by_id.values():
        if not sc.get("roster_name"):
            continue
        entry = {
            "area": int(sc["district"]), "city": sc.get("city", ""),
            "kind": sc.get("kind", ""), "name": sc["roster_name"],
        }
        note = sc.get("note", "")
        if note and not note.startswith(_NON_ROSTER_NOTE_PREFIXES):
            entry["note"] = note  # 加盟校一覧の生データに付いていた注意書き（例: 狛江）
        out[sc["legacy_key"]] = entry
    (OUT / "out/scout").mkdir(parents=True, exist_ok=True)
    (OUT / "out/scout/member_areas.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# リーグ戦の生ファイル（6つ）
# ---------------------------------------------------------------------------

DISTRICT_STARS_COLS = ["年度", "リーグ", "区分", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分", "得点H", "得点A", "出典"]
TLEAGUE_ARCHIVE_COLS = ["年度", "リーグ", "日付", "キックオフ", "ホーム", "学校H", "得点H", "アウェイ", "学校A", "得点A", "会場", "出典"]
TLEAGUE_HISTORY_COLS = ["年度", "リーグ", "日時", "ホーム", "学校H", "アウェイ", "学校A", "得点H", "得点A", "状態", "出典"]
DISTRICT_MATCHES_COLS = ["地区", "リーグ", "年度", "部", "節", "日付", "ホーム", "アウェイ", "ホーム得点", "アウェイ得点", "実施",
                          "ホーム学校", "ホーム区分", "アウェイ学校", "アウェイ区分", "出典"]
TLEAGUE_MATCHES_COLS = ["年度", "リーグ", "ブロック", "節", "日付", "時刻", "ホーム", "アウェイ", "ホーム得点", "アウェイ得点", "会場", "実施",
                         "ホーム学校", "ホーム区分", "アウェイ学校", "アウェイ区分", "出典"]
PRINCE_MATCHES_COLS = ["年度", "リーグ", "日付", "ホーム", "アウェイ", "ホーム得点", "アウェイ得点", "実施", "ホーム学校", "アウェイ学校", "出典"]


def star_rows(a: legacy.Adapter) -> list[dict]:
    """district_stars_matches.csv（星取表）の行を、matches・match_sources から復元する。"""
    rows = []
    for ms in a.match_sources:
        if ms["role"] not in ("主", "重複") or ms.get("src_row") in (None, ""):
            continue
        src = a.sources_by_id.get(ms["source_id"], {})
        if src.get("feed") != "星取表":
            continue
        m = a.matches_by_id.get(ms["match_id"])
        if not m:
            continue
        comp = a.comps_by_id.get(m["comp_id"])
        if not comp:
            continue
        # legacy.league_rows() の星取表（feed != "Tリーグ過去"）分岐と同じ条件にする（2026-10-01、
        # comp["series"]=="Tリーグ" かどうかだけで切り替える簡略式は誤り: 星取表には "T4リーグB" の
        # ように raw の「リーグ」列が生の文字列 "Tリーグ" のまま series になっているだけのケースがあり、
        # これは stage が T[1-5] 丁度一致ではないので series をそのまま使うのが正しい）
        league_name = comp["stage"] if re.fullmatch(r"T[1-5]", comp["stage"]) else comp["series"]
        if ms["role"] == "主":
            raw_a, raw_b = m["raw_a"], m["raw_b"]
            home_key, away_key = a.legacy_key_of_team(m["team_a"]), a.legacy_key_of_team(m["team_b"])
            home_squad = legacy._restore_squad("星取表", raw_a, home_key, a.squad_of_team(m["team_a"]))
            away_squad = legacy._restore_squad("星取表", raw_b, away_key, a.squad_of_team(m["team_b"]))
            score_a, score_b = m["score_a"], m["score_b"]
            block = m["block"]
        else:
            raw_a, raw_b = ms["raw_a"], ms["raw_b"]
            home_key, home_squad = a.resolve_name(raw_a)
            away_key, away_squad = a.resolve_name(raw_b)
            if not home_key or not away_key:
                continue
            flipped = ms["flipped"] in ("1", 1, True)
            score_a, score_b = (m["score_b"], m["score_a"]) if flipped else (m["score_a"], m["score_b"])
            block = ""  # 生き残り行の区分は別の試合のものなので使えない（goalnote の重複と同じ扱い）
        rows.append({
            "_src_row": int(ms["src_row"]),
            "年度": comp["season"], "リーグ": league_name, "区分": block,
            "ホーム": raw_a, "ホーム学校": home_key, "ホーム区分": home_squad,
            "アウェイ": raw_b, "アウェイ学校": away_key, "アウェイ区分": away_squad,
            "得点H": score_a, "得点A": score_b, "出典": src.get("url", ""),
        })
    rows.sort(key=lambda r: r["_src_row"])
    for r in rows:
        del r["_src_row"]
    return rows


def tleague_legacy_rows(a: legacy.Adapter, want_kind: str) -> list[dict]:
    """tleague_archive_matches.csv / tleague_history_matches.csv の行（Tリーグ過去。重複なし＝全件 role=主）。"""
    rows = []
    for ms in a.match_sources:
        if ms["role"] != "主" or ms.get("src_row") in (None, ""):
            continue
        src = a.sources_by_id.get(ms["source_id"], {})
        if src.get("feed") != "Tリーグ過去" or src.get("kind") != want_kind:
            continue
        m = a.matches_by_id.get(ms["match_id"])
        if not m:
            continue
        comp = a.comps_by_id.get(m["comp_id"])
        if not comp:
            continue
        rows.append({
            "_src_row": int(ms["src_row"]),
            "年度": comp["season"], "リーグ": comp["stage"],
            "日付": m["date_text"], "日時": m["date_text"],
            "学校H": a.legacy_key_of_team(m["team_a"]), "学校A": a.legacy_key_of_team(m["team_b"]),
            "得点H": m["score_a"], "得点A": m["score_b"], "出典": src.get("url", ""),
        })
    rows.sort(key=lambda r: r["_src_row"])
    for r in rows:
        del r["_src_row"]
    return rows


def materialize_league_matches(a: legacy.Adapter) -> None:
    common.write_csv(OUT / "data/leagues/district_stars_matches.csv", DISTRICT_STARS_COLS, star_rows(a))
    common.write_csv(OUT / "data/leagues/district_matches.csv", DISTRICT_MATCHES_COLS, legacy.feed_rows("goalnote", paths.dataset_dir()))
    common.write_csv(OUT / "data/leagues/tleague_matches.csv", TLEAGUE_MATCHES_COLS, legacy.feed_rows("Tリーグ公式", paths.dataset_dir()))
    common.write_csv(OUT / "data/leagues/tleague_archive_matches.csv", TLEAGUE_ARCHIVE_COLS, tleague_legacy_rows(a, "トーナメント表PDF"))
    common.write_csv(OUT / "data/leagues/tleague_history_matches.csv", TLEAGUE_HISTORY_COLS, tleague_legacy_rows(a, "Webページ"))
    common.write_csv(OUT / "data/leagues/prince_kanto1_2026_matches.csv", PRINCE_MATCHES_COLS, legacy.feed_rows("プリンス", paths.dataset_dir()))


# ---------------------------------------------------------------------------
# 順位表の生ファイル（4つ）
# ---------------------------------------------------------------------------

DISTRICT_STANDINGS_COLS = ["地区", "リーグ", "年度", "部", "順位", "チーム", "学校", "区分", "勝点", "試合", "勝", "分", "敗", "得点", "失点", "得失点", "出典"]
TLEAGUE_STANDINGS_COLS = ["年度", "リーグ", "ブロック", "順位", "チーム", "学校", "区分", "勝点", "試合", "勝", "敗", "分", "得点", "失点", "得失点", "出典"]
TLEAGUE_HISTORY_STANDINGS_COLS = ["年度", "リーグ", "順位", "チーム", "学校", "勝点", "試合", "勝", "敗", "分", "得点", "失点", "出典"]
PRINCE_STANDINGS_COLS = ["年度", "リーグ", "順位", "チーム", "学校", "勝点", "試合", "勝", "敗", "分", "得点", "失点", "得失点", "出典"]

FEED_TO_STANDINGS_FILE = {
    "goalnote": ("district_standings.csv", DISTRICT_STANDINGS_COLS, "district"),
    "Tリーグ公式": ("tleague_standings.csv", TLEAGUE_STANDINGS_COLS, "tleague"),
    "Tリーグ過去": ("tleague_history_standings.csv", TLEAGUE_HISTORY_STANDINGS_COLS, "history"),
    "プリンス": ("prince_kanto1_2026_standings.csv", PRINCE_STANDINGS_COLS, "prince"),
}


def standings_rows_for(a: legacy.Adapter, feed: str) -> list[dict]:
    _fname, _cols, kind = FEED_TO_STANDINGS_FILE[feed]
    rows = []
    for s in a.standings:
        src = a.sources_by_id.get(s["source_id"], {})
        if src.get("feed") != feed:
            continue
        comp = a.comps_by_id.get(s["comp_id"])
        team_id = s["team_id"]
        if not comp or team_id not in a.teams_by_id:
            continue
        squad = a.squad_of_team(team_id)
        school = a.legacy_key_of_team(team_id)
        team_disp = s.get("raw_team", "")  # 2026-10-01、standings.raw_team の追加で生の表記をそのまま復元できる
        src_text = src.get("url", "")
        if s.get("basis") == "試合から計算" and "（試合から計算）" not in src_text:
            src_text += "（試合から計算）"
        row = {
            "年度": comp["season"], "リーグ": comp["series"] if comp["series"] != "Tリーグ" else comp["stage"],
            "順位": s["rank"], "チーム": team_disp, "学校": school,
            "勝点": s["points"], "試合": s["played"], "勝": s["won"], "敗": s["lost"], "分": s["drawn"],
            "得点": s["goals_for"], "失点": s["goals_against"], "出典": src_text,
        }
        if kind in ("district", "tleague", "prince"):
            gf, ga = s.get("goals_for"), s.get("goals_against")
            row["得失点"] = str(int(gf) - int(ga)) if gf not in (None, "") and ga not in (None, "") else ""
        if kind == "district":
            row["地区"] = ""  # Vault に地区番号を持つ列が無い（area は大会のみ。league_coverage.py のみが使うが比較対象外）
            row["部"] = comp["stage"]
            row["区分"] = squad
        elif kind == "tleague":
            # 元の列は「Aブロック」のように末尾に「ブロック」がつく（Vault の block 列はこの接尾辞を
            # 外して持つ。SCHEMA.md の決め方に合わせたもの）。build_seeds.py・build_index.py が
            # この表示文字列をそのまま使うので、書き出すときに接尾辞を戻す
            row["ブロック"] = (s["block"] + "ブロック") if s["block"] else ""
            row["区分"] = squad
        # 元の順位表ファイルは基本的に comp・block の中は順位の昇順（標準出力で確認）。
        # standings.csv 自体には行の並び（src_row 相当）を持つ列が無いので、rank で近似する
        # （読む側はどれも学校名で引くか明示的に並べ替えるので、実害は無いはず）
        row["_src_row"] = (s["comp_id"], s["block"], int(s["rank"]) if s["rank"] not in (None, "") else 0, s["team_id"])
        rows.append(row)
    rows.sort(key=lambda r: r["_src_row"])
    for r in rows:
        del r["_src_row"]
    return rows


def materialize_standings(a: legacy.Adapter) -> None:
    for feed, (fname, cols, _kind) in FEED_TO_STANDINGS_FILE.items():
        common.write_csv(OUT / "data/leagues" / fname, cols, standings_rows_for(a, feed))


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------


def run() -> dict:
    a = legacy.Adapter()
    tournament_rows = materialize_tournament(a)
    materialize_teams(tournament_rows)
    materialize_member_areas(a)
    materialize_league_matches(a)
    materialize_standings(a)
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run() is not None else 1)
