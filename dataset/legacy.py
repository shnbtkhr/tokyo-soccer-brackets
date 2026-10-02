"""9表（Vault の Datasets/tokyo-hs-soccer/）-> 旧来の形（アダプタ）。

段階1では `tests/test_dataset_roundtrip.py` の往復テスト（T2〜T5）が使う。
段階2ではサイトの組み立てがこれを使う想定（`notes/dataset-migration-phase1.md` 参照）。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset import common, paths  # noqa: E402
from dataset.export import league_comp_id  # noqa: E402

TABLE_NAMES = [
    "schools.csv", "school_names.csv", "teams.csv", "competitions.csv",
    "matches.csv", "standings.csv", "sources.csv", "match_sources.csv", "corrections.csv",
]


def load_tables(base: Path | None = None) -> dict[str, list[dict]]:
    d = base or paths.dataset_dir()
    return {name: common.read_csv(d / name) for name in TABLE_NAMES}


class Adapter:
    """9表を読み込み、school_id/team_id <-> legacy_key の突き合わせをキャッシュする。"""

    def __init__(self, base: Path | None = None) -> None:
        t = load_tables(base)
        self.schools_by_id = {r["school_id"]: r for r in t["schools.csv"]}
        self.teams_by_id = {r["team_id"]: r for r in t["teams.csv"]}
        self.comps_by_id = {r["comp_id"]: r for r in t["competitions.csv"]}
        self.sources_by_id = {r["source_id"]: r for r in t["sources.csv"]}
        self.matches = t["matches.csv"]
        self.standings = t["standings.csv"]
        self.match_sources = t["match_sources.csv"]
        # (legacy_key, squad) -> team_id （校名の書き方は使わない。school の legacy_key と teams の squad から辿る）
        self.team_id_of: dict[tuple[str, str], str] = {}
        for team_id, tr in self.teams_by_id.items():
            sc = self.schools_by_id.get(tr["school_id"])
            if sc:
                self.team_id_of[(sc["legacy_key"], tr["squad"])] = team_id
        # match_id -> match_sources の主（role=主）の行。並び順（src_row・src_seq）を引くのに使う
        self.primary_source_by_match: dict[str, dict] = {}
        for ms in self.match_sources:
            if ms["role"] == "主":
                self.primary_source_by_match[ms["match_id"]] = ms
        # match_id -> matches.csv の行（role=重複の生スコア復元に使う）
        self.matches_by_id: dict[str, dict] = {m["match_id"]: m for m in self.matches}
        # 生の書き方（name）-> school_id（school_names.csv）。role=重複 の行は学校・区分の列を
        # 持たないので、生の書き方から学校を引き、legacy_key を除いた残りを区分として復元する
        self.name_to_school_id: dict[str, str] = {r["name"]: r["school_id"] for r in t["school_names.csv"]}

    def resolve_name(self, raw: str) -> tuple[str, str]:
        """生の書き方（例: 「大森学園C」）-> (legacy_key, squad)。school_names.csv を使う。"""
        sid = self.name_to_school_id.get(raw)
        if not sid:
            return "", ""
        legacy_key = self.schools_by_id.get(sid, {}).get("legacy_key", "")
        if legacy_key and raw.startswith(legacy_key):
            squad = raw[len(legacy_key):] or "A"
        else:
            squad = "A"
        return legacy_key, squad

    def legacy_key_of_team(self, team_id: str) -> str:
        tr = self.teams_by_id.get(team_id)
        if not tr:
            return ""
        return self.schools_by_id.get(tr["school_id"], {}).get("legacy_key", "")

    def squad_of_team(self, team_id: str) -> str:
        return self.teams_by_id.get(team_id, {}).get("squad", "")

    def team_id_for(self, legacy_key: str, squad: str) -> str:
        return self.team_id_of.get((legacy_key, squad), "")


# ---------------------------------------------------------------------------
# T2: 大会の往復
# ---------------------------------------------------------------------------


def _restore_block(series: str, new_stage_old_text: str, block: str) -> str:
    """新 block -> 旧「ブロック」。「Aブロック」「Bブロック」（選手権2次予選）以外は先頭に → を戻す。"""
    if not block:
        return ""
    if series == "選手権" and new_stage_old_text == "二次予選" and block in ("Aブロック", "Bブロック"):
        return block
    return "→" + block


def _restore_score_text(score_a: str, score_b: str, pk_a: str, pk_b: str, extra_time: str) -> str:
    if score_a == "" and score_b == "":
        return ""
    t = f"{score_a}-{score_b}"
    if pk_a != "" and pk_b != "":
        t += f" (PK {pk_a}-{pk_b})"
    elif extra_time == "1":
        t += " (延長)"
    return t


STATUS_NEW_TO_OLD_STATE = {
    "済": "終了", "勝者のみ": "スコア記載なし", "不戦": "不戦勝・棄権",
}  # 段階2（materialize.py）が build_teams()・connections.py・build_years.py の文字列一致判定に使うため
# "結果不明" だけは別処理（_restore_result_unknown）。STATUS_OLD_TO_NEW（export.py）は
# "未実施"（スコア無し）と "勝者不明"（スコアはあるが勝者が決まらない）の両方をここへ合流させており、
# 合流前の区別はスコアの有無だけで一意に戻せる（実測：未実施はスコア無しが5261件、勝者不明は
# スコア有りが21件で、ぶれは無い）。build_outputs.build_teams() は "未実施" の行だけをスキップするため、
# 一律 "未実施" に戻すと "勝者不明"（結果は分からないが試合は行われた）の21試合が誤って消える
# （2026-10-01、段階2の比較で2016年度選手権・城東×専大附属戦が消えて発覚）


def _restore_result_unknown(score_a: str, score_b: str) -> str:
    return "勝者不明" if (score_a != "" and score_b != "") else "未実施"


def tournament_rows(base: Path | None = None) -> list[dict]:
    """legacy.tournament_rows() -> out/matches.csv の行と同じ列を持つ dict のリスト（大会のみ）。"""
    a = Adapter(base)
    rows = []
    for m in a.matches:
        comp = a.comps_by_id.get(m["comp_id"])
        if not comp or comp["format"] != "トーナメント":
            continue
        series = comp["series"]
        old_stage_text = common.join_stage(series, comp["stage"], comp["edition"])
        _edition, rest, _new, _level = common.split_stage(series, old_stage_text)
        block = _restore_block(series, rest, m["block"])
        raw_a, raw_b = m["raw_a"], m["raw_b"]
        winner_raw = ""
        if m["winner"] and m["winner"] == m["team_a"]:
            winner_raw = raw_a
        elif m["winner"] and m["winner"] == m["team_b"]:
            winner_raw = raw_b
        src = a.sources_by_id.get(m["source_id"], {})
        rows.append({
            "年度": comp["season"], "大会": series, "段階": old_stage_text,
            "地区・支部": m["area"], "ブロック": block, "ページ": m["page"], "ラウンド": m["round"],
            "日付": m["date_text"], "試合番号": m["match_no"],
            "チームA": raw_a, "チームB": raw_b,
            "スコア": _restore_score_text(m["score_a"], m["score_b"], m["pk_a"], m["pk_b"], m["extra_time"]),
            "得点A": m["score_a"], "得点B": m["score_b"], "PK_A": m["pk_a"], "PK_B": m["pk_b"],
            "前後半": m["halves"], "勝者": winner_raw,
            "状態": (_restore_result_unknown(m["score_a"], m["score_b"]) if m["status"] == "結果不明"
                    else STATUS_NEW_TO_OLD_STATE.get(m["status"], "")),
            "備考": m["note"],
            "チームA_正規化": a.legacy_key_of_team(m["team_a"]), "チームB_正規化": a.legacy_key_of_team(m["team_b"]),
            "出典PDF": src.get("url", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# T3: リーグの往復（leagues.load_all() と同じ形）
# ---------------------------------------------------------------------------


_SQUAD_LETTERS = set("ABCDEFGHIJ" + "ＡＢＣＤＥＦＧＨＩＪ")


def _restore_squad(feed: str, raw: str, legacy_key: str, squad: str) -> str:
    """新 teams.squad -> 旧「区分」。段階1の変換規則で失われる情報を出典（feed）別に復元する。

    - プリンス・Tリーグ過去：load_all() は常に区分を空欄にしている（_mk への渡し方がそうなっているため）
    - goalnote・Tリーグ公式：常に明示（空欄が存在しない。実測で確認済み）なので teams.squad をそのまま使う
    - 星取表：空欄と明示が混在する。次の両方を満たすときだけ明示（squad をそのまま使う）とみなし、
      それ以外は空欄とする：(1) raw が legacy_key と文字として一致しない (2) raw の末尾1文字が
      区分の文字（A〜J）である。どちらか一方だけでは判定を誤る実例が両方あった：
      「駒澤大学」（raw が legacy_key「駒澤大高」と一致しないが末尾は区分の文字でない＝空欄）、
      「西A」（raw の末尾は区分の文字だが、この行自身の学校名が「西A」で raw と一致＝空欄）
    """
    if feed in ("プリンス", "Tリーグ過去"):
        return ""
    if feed == "星取表":
        ends_with_letter = bool(raw) and len(raw) > 1 and raw[-1] in _SQUAD_LETTERS
        # 全角/半角のゆれ（「西Ａ」vs「西A」）で raw と legacy_key の単純な文字列比較がすり抜けた
        # 実例があったため、NFKC で正規化してから比べる
        same_as_school = unicodedata.normalize("NFKC", raw) == unicodedata.normalize("NFKC", legacy_key)
        if not same_as_school and ends_with_letter:
            return squad
        return ""
    return squad


def league_rows(base: Path | None = None) -> list[dict]:
    """legacy.league_rows() -> leagues.load_all() と同じ形の dict のリスト（リーグのみ・済のみ）。"""
    a = Adapter(base)
    rows = []
    for m in a.matches:
        comp = a.comps_by_id.get(m["comp_id"])
        if not comp or comp["format"] != "リーグ" or m["status"] != "済":
            continue
        season = comp["season"]
        src = a.sources_by_id.get(m["source_id"], {})
        feed = src.get("feed", "")
        if feed == "Tリーグ過去":
            # leagues.py の _mk2 が Tリーグ過去（archive/history）だけ「リーグ」に文字列 "Tリーグ" を
            # そのまま渡し、実際の部（T1〜T5）は「区分」側に入れている
            league_name = "Tリーグ"
        elif re.fullmatch(r"T[1-5]", comp["stage"]):
            # 星取表・Tリーグ公式は「リーグ」列そのものが T1〜T5 のときだけ series=Tリーグ・
            # stage=T値に分けている（league_comp_id の is_t 分岐）。stage が T1〜T5 の形なら、
            # 元の「リーグ」もその値そのもの
            league_name = comp["stage"]
        else:
            # 星取表には「リーグ」列が既に "Tリーグ"（総称）で、実際の部は「区分」列に
            # "T4リーグB" のような形で入っている行もある。この場合 stage は T1〜T5 の形にならない
            league_name = comp["series"]
        div = m["block"]
        home_key = a.legacy_key_of_team(m["team_a"])
        away_key = a.legacy_key_of_team(m["team_b"])
        home_squad_raw = a.squad_of_team(m["team_a"])
        away_squad_raw = a.squad_of_team(m["team_b"])
        ps = a.primary_source_by_match.get(m["match_id"], {})
        src_seq = int(ps["src_seq"]) if ps.get("src_seq") not in (None, "") else 0
        rows.append({
            "年度": str(season), "リーグ": league_name, "区分": div, "日付": m["date_text"],
            "ホーム学校": home_key, "ホーム区分": _restore_squad(feed, m["raw_a"], home_key, home_squad_raw),
            "アウェイ学校": away_key, "アウェイ区分": _restore_squad(feed, m["raw_b"], away_key, away_squad_raw),
            "得点H": int(m["score_a"]), "得点A": int(m["score_b"]),
            "出典": src.get("url", ""), "出どころ": feed,
            "_src_seq": src_seq,
        })
    # leagues.load_all() は (年度,リーグ,日付) で安定ソートする。同じ組の中の並びは、選別前の
    # 候補列 order（日付の有無→出どころ→元の並び）での位置がそのまま残る。src_seq はその位置そのもの
    rows.sort(key=lambda r: r["_src_seq"])
    rows.sort(key=lambda r: (r["年度"], r["リーグ"], r["日付"]))
    for r in rows:
        del r["_src_seq"]
    return rows


# ---------------------------------------------------------------------------
# T4: 点数の往復（rating.league_games が読む3経路の生 CSV 形）
# ---------------------------------------------------------------------------

FEED_TO_FILE = {"goalnote": "district_matches.csv", "Tリーグ公式": "tleague_matches.csv", "プリンス": "prince_kanto1_2026_matches.csv"}


def feed_rows(feed: str, base: Path | None = None) -> list[dict]:
    """legacy.feed_rows(feed) -> goalnote・Tリーグ公式・プリンスの生 CSV と同じ形の行（済のみ）。

    rating.league_games() が実際に読む列だけを正確に埋める。未実施（予定）行は rating 側の
    `実施 != "済"` フィルタでどのみち捨てられるため、ここでは含めない。

    rating.league_games() は leagues.load_all() の重なり整理（同じ試合を1行にまとめる処理）を
    通さず、生の CSV を1行ずつそのまま読む。そのため、load_all() が「重なり」として落とした行
    （match_sources の role=重複）も、出典（feed）が一致する限りここに含める必要がある
    （2026-09-30、日体大荏原Bなどの控えチームの試合で実際に抜けていたのを確認して対応）。
    """
    if feed not in FEED_TO_FILE:
        raise ValueError(feed)
    a = Adapter(base)
    rows = []

    for m in a.matches:
        if m["status"] != "済":
            continue
        src = a.sources_by_id.get(m["source_id"], {})
        if src.get("feed") != feed:
            continue
        comp = a.comps_by_id.get(m["comp_id"])
        if not comp:
            continue
        season = comp["season"]
        is_t = comp["series"] == "Tリーグ"
        league_name = comp["stage"] if is_t else comp["series"]
        home_key = a.legacy_key_of_team(m["team_a"])
        away_key = a.legacy_key_of_team(m["team_b"])
        home_squad = _restore_squad(feed, m["raw_a"], home_key, a.squad_of_team(m["team_a"]))
        away_squad = _restore_squad(feed, m["raw_b"], away_key, a.squad_of_team(m["team_b"]))
        ps = a.primary_source_by_match.get(m["match_id"], {})
        src_row = int(ps["src_row"]) if ps.get("src_row") not in (None, "") else 0
        row = {
            "年度": str(season), "リーグ": league_name, "日付": m["date_text"],
            "ホーム": m["raw_a"], "アウェイ": m["raw_b"],
            "ホーム得点": m["score_a"], "アウェイ得点": m["score_b"], "実施": "済",
            "ホーム学校": home_key, "ホーム区分": home_squad,
            "アウェイ学校": away_key, "アウェイ区分": away_squad,
            "出典": src.get("url", ""),
        }
        if feed == "goalnote":
            row["地区"] = ""
            row["部"] = m["block"]
            row["節"] = m["round"]
        elif feed == "Tリーグ公式":
            row["ブロック"] = m["block"]
            row["節"] = m["round"]
            row["時刻"] = ""
            row["会場"] = ""
        rows.append((src_row, row))

    # load_all() の重なり整理で落ちた、この feed 自身の生の行（役割=重複）。スコアは
    # 同じ試合の生き残り行（matches.csv）と必ず同じ（load_all() の key() がスコアも鍵に含むため）。
    # flipped ならホーム・アウェイを入れ替える。学校・区分は生の書き方から school_names.csv で引く
    for ms in a.match_sources:
        if ms["role"] != "重複" or ms.get("src_row") in (None, ""):
            continue
        src = a.sources_by_id.get(ms["source_id"], {})
        if src.get("feed") != feed:
            continue
        parent = a.matches_by_id.get(ms["match_id"])
        if not parent or parent["status"] != "済":
            continue
        flipped = ms["flipped"] in ("1", 1, True)
        # raw_a/raw_b はこの出典（重複した行）自身のホーム・アウェイそのまま（捕捉時点で既に正しい向き）。
        # flipped は「生き残った試合」から見た向きの参考情報であり、スコアの対応づけにだけ使う
        # （生き残った試合の score_a/score_b はどちらがこの行のホーム側の得点かを直接教えてくれない）
        raw_home, raw_away = ms["raw_a"], ms["raw_b"]
        score_home, score_away = (parent["score_b"], parent["score_a"]) if flipped else (parent["score_a"], parent["score_b"])
        home_key, home_squad = a.resolve_name(raw_home)
        away_key, away_squad = a.resolve_name(raw_away)
        if not home_key or not away_key:
            continue  # school_names.csv に無い書き方（起きていないはずだが、念のため）
        comp = a.comps_by_id.get(parent["comp_id"])
        # load_all() の key() は年度も鍵に含むので、重複行は生き残り行と必ず同じ年度
        row = {
            "年度": str(comp["season"]) if comp else "",
            "リーグ": "", "日付": ms["date_text"],
            "ホーム": raw_home, "アウェイ": raw_away,
            "ホーム得点": score_home, "アウェイ得点": score_away, "実施": "済",
            "ホーム学校": home_key, "ホーム区分": home_squad,
            "アウェイ学校": away_key, "アウェイ区分": away_squad,
            "出典": src.get("url", ""),
        }
        if feed == "goalnote":
            row["地区"] = ""
            row["部"] = ""  # 生き残り行の区分（block）は別の試合のものなので使えない
            row["節"] = ms["round"]
        elif feed == "Tリーグ公式":
            row["ブロック"] = ""
            row["節"] = ms["round"]
            row["時刻"] = ""
            row["会場"] = ""
        rows.append((int(ms["src_row"]), row))

    rows.sort(key=lambda pair: pair[0])  # rating.league_games() は csv.DictReader のファイル順に読む
    return [row for _src_row, row in rows]


# ---------------------------------------------------------------------------
# T5: 順位表の往復
# ---------------------------------------------------------------------------


def find_standing(a: Adapter, season: int, league_name: str, div: str, block: str,
                   legacy_key: str, squad: str) -> dict | None:
    comp_id, _series, _stage = league_comp_id(season, league_name, div)
    team_id = a.team_id_for(legacy_key, squad)
    if not team_id:
        return None
    for r in a.standings:
        if r["comp_id"] == comp_id and r["block"] == block and r["team_id"] == team_id:
            return r
    return None
