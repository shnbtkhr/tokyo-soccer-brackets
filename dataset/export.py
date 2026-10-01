"""旧データ（out/matches.csv・leagues.py の5経路・訂正・校名の寄せ）を SCHEMA.md の9表に変換し、
Vault（dataset.paths.dataset_dir()）へ書き出す。

  uv run python -m dataset.export

段階1はサイトの組み立てを切り替えない。既存スクリプトは読むだけで、書き換えない
（唯一の例外は build_outputs.drop_version_duplicates() の out/dropped_duplicates.csv 出力）。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_outputs  # noqa: E402
from dataset import common, league_source, paths  # noqa: E402


class StopForReview(Exception):
    """「実装を止めて報告する」場面で送出する。"""


# ---------------------------------------------------------------------------
# 学校・名前の登録
# ---------------------------------------------------------------------------


class SchoolRegistry:
    def __init__(self) -> None:
        self.seen: dict[str, dict] = {}
        self.names: dict[str, dict] = {}
        self.conflicts: list[tuple[str, str, str]] = []
        # name -> key -> {"feed":str, "row":dict}  (最初に見つけたサンプル行。既知問題レポート用)
        self.name_examples: dict[str, dict[str, dict]] = {}

    def touch_school(self, key: str, season: int, in_tournament: bool = False, in_league: bool = False) -> None:
        if not key:
            return
        s = self.seen.setdefault(key, {"first_season": season, "in_tournament": False, "in_league": False})
        s["first_season"] = min(s["first_season"], season)
        if in_tournament:
            s["in_tournament"] = True
        if in_league:
            s["in_league"] = True

    def touch_name(self, name: str, key: str, season: int, feed: str = "", row: dict | None = None) -> None:
        if not name or not key:
            return
        n = self.names.get(name)
        if n is None:
            self.names[name] = {"school_key": key, "first": season, "last": season}
        elif n["school_key"] != key:
            self.conflicts.append((name, n["school_key"], key))
        else:
            n["first"] = min(n["first"], season)
            n["last"] = max(n["last"], season)
        ex = self.name_examples.setdefault(name, {})
        if key not in ex:
            ex[key] = {"feed": feed, "row": row or {}}


LEAGUE_RAW_FILES = [
    ("district_stars_matches.csv", "星取表", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分"),
    ("district_matches.csv", "goalnote", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分"),
    ("tleague_matches.csv", "Tリーグ公式", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分"),
    ("tleague_archive_matches.csv", "Tリーグ過去", "ホーム", "学校H", None, "アウェイ", "学校A", None),
    ("tleague_history_matches.csv", "Tリーグ過去", "ホーム", "学校H", None, "アウェイ", "学校A", None),
    ("prince_kanto1_2026_matches.csv", "プリンス", "ホーム", "ホーム学校", None, "アウェイ", "アウェイ学校", None),
]


def scan_tournament(reg: SchoolRegistry, rows: list[dict]) -> None:
    for r in rows:
        season = int(r["年度"])
        for raw_col, norm_col in (("チームA", "チームA_正規化"), ("チームB", "チームB_正規化")):
            raw, key = r[raw_col], r[norm_col]
            if not key:
                continue
            reg.touch_school(key, season, in_tournament=True)
            reg.touch_name(raw, key, season, feed="大会", row=r)


def scan_league_raw(reg: SchoolRegistry) -> None:
    for fname, feed, hraw, hsch, _hsq, araw, asch, _asq in LEAGUE_RAW_FILES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            y = (r.get("年度") or "").strip()
            if not re.fullmatch(r"-?\d+", y):
                continue
            season = int(y)
            for rawcol, schcol in ((hraw, hsch), (araw, asch)):
                raw, key = r.get(rawcol, ""), r.get(schcol, "")
                if not key:
                    continue
                reg.touch_school(key, season, in_league=True)
                reg.touch_name(raw, key, season, feed=feed, row=r)


def scan_aliases(reg: SchoolRegistry) -> list[str]:
    aliases = json.loads((ROOT / "scout/school_aliases.json").read_text(encoding="utf-8"))
    skipped = []
    for k in aliases.get("exact_map", {}):
        resolved = build_outputs.normalize(k)
        if resolved in reg.seen:
            reg.touch_name(k, resolved, reg.seen[resolved]["first_season"])
        else:
            skipped.append(k)
    return skipped


def compute_ambiguous(reg: SchoolRegistry) -> tuple[set[str], dict[str, list[str]]]:
    """同じ書き方が2つ以上の学校を指すケースを集める。

    2026-09-30 のコーディネーター判断：段階1では統合しない（寄せ方を変えない）。
    school_names.csv には登録せず、schools.csv の note に「別IDかもしれない」と書き、
    notes/dataset-known-issues.md に出典つきで残す。統合は段階1の外（別作業）。
    """
    ambiguous_names = sorted({name for name, _, _ in reg.conflicts})
    partner_map: dict[str, set[str]] = defaultdict(set)
    for name in ambiguous_names:
        keys = list(reg.name_examples.get(name, {}).keys())
        for i, k1 in enumerate(keys):
            for k2 in keys[i + 1:]:
                partner_map[k1].add(k2)
                partner_map[k2].add(k1)
    return set(ambiguous_names), {k: sorted(v) for k, v in partner_map.items()}


def assign_school_ids(reg: SchoolRegistry, existing_rows: list[dict]) -> dict[str, str]:
    existing_map = {r["legacy_key"]: r["school_id"] for r in existing_rows if r.get("legacy_key")}
    used_nums = [int(mm[1]) for r in existing_rows if (mm := re.fullmatch(r"S(\d+)", r["school_id"] or ""))]
    next_num = (max(used_nums) + 1) if used_nums else 1
    keys_sorted = sorted(reg.seen.keys(), key=lambda k: (reg.seen[k]["first_season"], k))
    id_of: dict[str, str] = {}
    for k in keys_sorted:
        if k in existing_map:
            id_of[k] = existing_map[k]
        else:
            id_of[k] = f"S{next_num:04d}"
            next_num += 1
    return id_of


def build_schools(reg: SchoolRegistry, id_of: dict[str, str], member_areas: dict,
                   partner_map: dict[str, list[str]]) -> tuple[list[dict], dict]:
    rows = []
    tally = {"member_areas": 0, "unknown_tournament": 0, "unknown_league": 0, "club": 0, "ambiguous_pair": 0}
    for key, info in reg.seen.items():
        sid = id_of[key]
        if key in member_areas:
            ma = member_areas[key]
            kind, district, city, note = ma.get("kind", ""), ma.get("area", ""), ma.get("city", ""), ""
            tally["member_areas"] += 1
        elif info["in_tournament"]:
            kind, district, city, note = "不明", "", "", "区分未確認"
            tally["unknown_tournament"] += 1
        elif common.CLUB_HINT_RE.search(key):
            kind, district, city, note = "クラブ", "", "", ""
            tally["club"] += 1
        else:
            kind, district, city, note = "不明", "", "", "区分未確認"
            tally["unknown_league"] += 1
        partners = partner_map.get(key)
        if partners:
            note = f"移行時点では別ID。{'、'.join(partners)}と同じ学校の可能性（修正は移行後）"
            tally["ambiguous_pair"] += 1
        rows.append({
            "school_id": sid, "name": key, "official_name": "", "kind": kind,
            "district": district, "city": city, "legacy_key": key, "note": note,
        })
    rows.sort(key=lambda r: r["school_id"])
    return rows, tally


def build_school_names(reg: SchoolRegistry, id_of: dict[str, str], ambiguous_names: set[str]) -> list[dict]:
    rows = []
    for name, info in reg.names.items():
        if name in ambiguous_names:
            continue  # 同じ書き方が2つの学校を指す（コーディネーター判断・2026-09-30）。登録しない
        key = info["school_key"]
        if key not in id_of:
            continue
        rows.append({
            "name": name, "school_id": id_of[key], "kind": "表記",
            "first_season": info["first"], "last_season": info["last"],
        })
    rows.sort(key=lambda r: r["name"])
    return rows


KNOWN_CAUSES = {
    "専大附属": "星取表は「専大附属」のまま、goalnote は正規化して「専修大附」。同じ専修大学附属高校。",
    "専大附属A": "星取表は「専大附属」+区分A、goalnote は「専修大附」+区分A に分割。同じ専修大学附属高校。",
    "杉並FC": "星取表は末尾『C』をクラブチーム区分と誤認して「杉並F」+区分C に分割。goalnote/tleague は「杉並FC」のまま。",
    "大森FC": "星取表は末尾『C』を区分と誤認して「大森F」+区分C に分割。tleague_matches は「大森FC」のまま。",
    "國學院久我山C": "tleague_archive_matches.csv は2018年度、括弧なしの末尾『C』を区分と分割せず学校名に含めたまま記録（同ファイルの「（C）」表記は正しく分割）。他ファイルは「国学院久我山」+区分Cに分割。",
    "東海大高輪台B": "tleague_archive_matches.csv は2018年度、括弧なしの末尾『B』を区分と分割せず学校名に含めたまま記録。他ファイルは「東海大高輪台」+区分Bに分割。",
    "日体荏原": "tleague_archive_matches.csv（2021年度）は「日体荏原」、他ファイル（district_matches・tleague_matches）は「日体大荏原」。同じ日本体育大学荏原高校の略記ゆれ。",
    "明大中野八王子": "星取表は「明大中野八王子」、district_matches/tleague_matches は「明大八王子」。同じ明治大学付属中野八王子高校の略記ゆれ。",
    "町田Y・B": "星取表は「町田Y・」（中黒つき）+区分B、tleague_matches は「町田Y」（中黒なし）+区分Bに分割。同じチームの表記ゆれ。",
    "日本学園": "改称: 日本学園 → 明大世田谷（同一校）。school_aliases.json の exact_map で大会側は「明大世田谷」に寄せているが、リーグ側の星取表・tleague_archive は寄せる前の「日本学園」のまま raw=school として記録している（ユーザー確認済みの改称。2026-09-30）。",
}


# PDF の表の読み取りで、隣の枠の校名が1つにくっついてしまった「学校」。検査4・5（トーナメントの
# 試合数・重複チーム）が実際に引っかけた行を1つずつ確かめて特定した（2026-09-30）。出典はいずれも
# out/matches.csv の時点で既にこの形（build_outputs.py の読み取りの問題であり、段階1の変換では
# 直さない）。school_id は schools.csv の ID 持ち越し（rule 1）で再実行しても変わらないので、
# school_id で直接指定する
BRACKET_ANOMALY_SCHOOL_IDS = {
    "S0657": "制御文字（PDF読み取りの文字化け）。2005年度新人戦第7地区の枠に繰り返し出る。",
    "S0499": "空欄が legacy_key になった枠（2005年度新人戦第8地区）。学校名が読み取れなかった枠。",
    "S2006": "隣の2校（日体大荏原・都板橋有徳）の名前が1つにくっついた読み取り誤り（2019年度）。",
    "S2000": "隣の2校（城北・二松学舎）の名前が1つにくっついた読み取り誤り（2019年度）。",
    "S1999": "隣の2校（北園・武蔵野）の名前が1つにくっついた読み取り誤り（2019年度）。",
    "S2060": "隣の2校（攻玉社・都小山台）の名前が1つにくっついた読み取り誤り（2021年度）。",
    "S2063": "隣の2校（暁星・都上野）の名前が1つにくっついた読み取り誤り（2021年度）。",
    "S2064": "隣の2校（朋優学院・都飛鳥）の名前が1つにくっついた読み取り誤り（2021年度）。",
    "S2075": "隣の2校（青稜・都王子総合）の名前が1つにくっついた読み取り誤り（2021年度）。",
}


def find_bracket_anomaly_school_ids(schools_rows: list[dict]) -> dict[str, tuple[str, str]]:
    by_id = {r["school_id"]: r["legacy_key"] for r in schools_rows}
    out = {}
    for sid, cause in BRACKET_ANOMALY_SCHOOL_IDS.items():
        if sid in by_id:
            out[sid] = (by_id[sid], cause)
    return out


def write_known_issues_doc(reg: SchoolRegistry, ambiguous_names: set[str], partner_map: dict[str, list[str]],
                            nihongakuen_rows: list[dict], bracket_anomalies: dict[str, tuple[str, str]]) -> int:
    path = ROOT / "notes/dataset-known-issues.md"
    lines = [
        "# データ移行で見つかった既知の問題（school_names.csv 未登録の名寄せ）",
        "",
        "`uv run python -m dataset.export` の実行のたびに自動生成される。手で編集しない。",
        "",
        "## 名寄せの競合（school_names.csv には登録しない）",
        "",
        "同じ書き方が、出典（feed）によって異なる学校（legacy_key）を指す。SCHEMA.md の検査6の対象だが、"
        "段階1では legacy_key を統合しない（`notes/dataset-migration-phase1.md` のコーディネーター判断・2026-09-30）。"
        "Vault の `school_names.csv` には**登録しない**（登録すると1つの書き方が2つの学校を指すことになるため）。"
        "各 legacy_key の `schools.csv` の `note` に「移行時点では別ID」と記録してある。"
        "統合（名寄せ）は段階1の外、別作業で行う。",
        "",
        "| 生の書き方 | 出典→学校（legacy_key） | 参考行（年度） | 原因 |",
        "|---|---|---|---|",
    ]
    for name in sorted(ambiguous_names):
        examples = reg.name_examples.get(name, {})
        mapping = "; ".join(f"{ex['feed']}→{key}" for key, ex in sorted(examples.items()))
        years = sorted({str(ex["row"].get("年度", "")) for ex in examples.values() if ex.get("row")})
        cause = KNOWN_CAUSES.get(name, "出典間で校名の分割・略記が食い違っている（詳細未調査）。")
        lines.append(f"| {name} | {mapping} | {'、'.join(years)} | {cause} |")
    lines += [
        "",
        "## 改称・確認済みの同一校（参考。上の表の「日本学園」行と対応）",
        "",
        "- **日本学園 → 明大世田谷**：ユーザー確認済みの改称（2026-09-30）。`school_aliases.json` の "
        "`exact_map` で大会側（トーナメント）は正規化時に「明大世田谷」へ寄せているが、リーグ側の生データ"
        "（星取表・tleague_archive_matches.csv の一部）は改称前の表記「日本学園」のまま school 名として"
        "残っている。段階1では legacy_key を統合しない。",
        "",
    ]
    if nihongakuen_rows:
        lines += [
            "## district_matches.csv の「日本学園B」→「明大世田谷」分割について",
            "",
            "2026年度・第6地区リーグ2部Bで、アウェイ「日本学園B」の分割結果（アウェイ学校）が「明大世田谷」に"
            "なっている行が" + str(len(nihongakuen_rows)) + "件ある。上記の改称を踏まえると、"
            "これは誤りではなく**正しい分割**（日本学園＝明大世田谷の旧名なので、B チームの学校名も"
            "明大世田谷でよい）。ユーザー確認済み（2026-09-30）。参考までに該当行を残す。",
            "",
            "| 年度 | 日付 | ホーム | アウェイ（生） | アウェイ学校（分割後） |",
            "|---|---|---|---|---|",
        ]
        for r in nihongakuen_rows:
            lines.append(f"| {r.get('年度')} | {r.get('日付')} | {r.get('ホーム')} | {r.get('アウェイ')} | {r.get('アウェイ学校')} |")
        lines.append("")
    if bracket_anomalies:
        lines += [
            "## トーナメントの試合数・重複チームの検査で見つかった読み取り誤り（検査4・5では除外）",
            "",
            "PDF の表で隣の枠の校名が1つにくっついた、または文字化けした「学校」。"
            "検査4（試合数 <= チーム数-1）・検査5（同じ回戦に同じチームが2度出ていないか）が"
            "実際に引っかけた行を1つずつ確認して特定した。`out/matches.csv` の時点で既にこの形になっている"
            "（`build_outputs.py`／PDF読み取りの問題であり、段階1の変換では直さない）。"
            "`dataset.check` は school_id を指定してこのリストを除外している。",
            "",
            "| school_id | legacy_key | 原因 |",
            "|---|---|---|",
        ]
        for sid, (key, cause) in sorted(bracket_anomalies.items()):
            lines.append(f"| {sid} | {key} | {cause} |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(ambiguous_names)


# ---------------------------------------------------------------------------
# チーム
# ---------------------------------------------------------------------------


def scan_teams(old_matches, dropped_rows, league_kept, league_dropped, scheduled_raw, standings_raw=()):
    seen: dict[tuple, dict] = {}

    def touch(key, squad, season):
        if not key:
            return
        squad = squad or "A"
        t = seen.setdefault((key, squad), {"first": season, "last": season})
        t["first"] = min(t["first"], season)
        t["last"] = max(t["last"], season)

    for r in old_matches + dropped_rows:
        season = int(r["年度"])
        touch(r["チームA_正規化"], "A", season)
        touch(r["チームB_正規化"], "A", season)
    for r in league_kept + league_dropped:
        season = int(r["年度"])
        touch(r["ホーム学校"], r["ホーム区分"] or "A", season)
        touch(r["アウェイ学校"], r["アウェイ区分"] or "A", season)
    for hk, hs, ak, as_, season in scheduled_raw:
        touch(hk, hs, season)
        touch(ak, as_, season)
    for key, squad, season in standings_raw:
        touch(key, squad, season)
    return seen


def build_teams(teams_seen: dict[tuple, dict], id_of: dict[str, str]) -> tuple[list[dict], dict]:
    rows = []
    team_id_of = {}
    for (key, squad), info in teams_seen.items():
        if key not in id_of:
            continue
        sid = id_of[key]
        tid = f"{sid}-{squad}"
        team_id_of[(key, squad)] = tid
        rows.append({
            "team_id": tid, "school_id": sid, "squad": squad,
            "first_season": info["first"], "last_season": info["last"],
        })
    rows.sort(key=lambda r: r["team_id"])
    return rows, team_id_of


# ---------------------------------------------------------------------------
# 大会・リーグの部
# ---------------------------------------------------------------------------


def build_competitions(old_matches: list[dict]) -> dict[str, dict]:
    comps: dict[str, dict] = {}
    for r in old_matches:
        season, series, old_stage = int(r["年度"]), r["大会"], r["段階"]
        edition, _rest, new_stage, level = common.split_stage(series, old_stage)
        comp_id = f"{season}-{series}-{new_stage}"
        comps.setdefault(comp_id, {
            "comp_id": comp_id, "season": season, "series": series, "stage": new_stage,
            "edition": edition, "level": level, "format": "トーナメント", "district": "",
        })
    return comps


def league_comp_id(season: int, league_name: str, div: str) -> tuple[str, str, str]:
    is_t = bool(re.fullmatch(r"T[1-5]", league_name))
    series = "Tリーグ" if is_t else league_name
    stage = league_name if is_t else div
    return f"{season}-{series}-{stage}", series, stage


def ensure_league_comp(comps: dict[str, dict], season: int, league_name: str, div: str) -> str:
    comp_id, series, stage = league_comp_id(season, league_name, div)
    comps.setdefault(comp_id, {
        "comp_id": comp_id, "season": season, "series": series, "stage": stage,
        "edition": "", "level": "リーグ", "format": "リーグ", "district": "",
    })
    return comp_id


# ---------------------------------------------------------------------------
# 出典
# ---------------------------------------------------------------------------


class SourceRegistry:
    def __init__(self, existing_rows: list[dict]) -> None:
        self.by_url: dict[str, dict] = {}
        for r in existing_rows:
            self.by_url[r["url"]] = dict(r)
        used_nums = [int(mm[1]) for r in existing_rows if (mm := re.fullmatch(r"R(\d+)", r["source_id"] or ""))]
        self.next_num = (max(used_nums) + 1) if used_nums else 1

    def get_or_create(self, url: str, kind: str, feed: str, title: str = "", archive_url: str = "", note: str = "") -> str:
        if not url:
            return ""
        if url in self.by_url:
            return self.by_url[url]["source_id"]
        sid = f"R{self.next_num:04d}"
        self.next_num += 1
        self.by_url[url] = {
            "source_id": sid, "kind": kind, "feed": feed, "url": url,
            "archive_url": archive_url, "title": title, "sha256": "", "note": note,
        }
        return sid

    def rows(self) -> list[dict]:
        return sorted(self.by_url.values(), key=lambda r: r["source_id"])


def fill_sha256(sources: SourceRegistry, url_to_stem: dict[str, str]) -> None:
    for url, row in sources.by_url.items():
        if row.get("sha256"):
            continue
        stem = url_to_stem.get(url)
        if not stem:
            continue
        for d in ("pdfs", "pdfs/archive"):
            p = ROOT / d / f"{stem}.pdf"
            if p.exists():
                row["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                break


# ---------------------------------------------------------------------------
# 試合（大会）
# ---------------------------------------------------------------------------

STATUS_OLD_TO_NEW = {
    "終了": "済", "スコアのみ記載（赤線未反映）": "済", "赤線が両側（スコアで判定）": "済",
    "スコア記載なし": "勝者のみ",
    "不戦勝・棄権": "不戦",
    "未実施": "結果不明", "勝者不明": "結果不明",
}

DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def md_to_iso(season: int, m: int, d: int) -> str:
    year = season + 1 if m < 4 else season
    return f"{year:04d}-{m:02d}-{d:02d}"


def build_tournament_matches(rows, team_id_of, src_reg):
    matches, msrc = [], []
    key_to_matchid: dict[tuple, tuple] = {}
    id_counts: dict[str, int] = {}
    for r in rows:
        season, series, old_stage = int(r["年度"]), r["大会"], r["段階"]
        _, _, new_stage, _ = common.split_stage(series, old_stage)
        comp_id = f"{season}-{series}-{new_stage}"
        area = r["地区・支部"]
        old_block = r["ブロック"]
        block = old_block[1:] if old_block.startswith("→") else old_block
        rnd = r["ラウンド"]
        date_text = r["日付"]
        dm = DATE_RE.match(date_text.strip()) if date_text else None
        date = md_to_iso(season, int(dm[1]), int(dm[2])) if dm else ""
        raw_a, raw_b = r["チームA"], r["チームB"]
        key_a, key_b = r["チームA_正規化"], r["チームB_正規化"]
        team_a = team_id_of.get((key_a, "A"), "")
        team_b = team_id_of.get((key_b, "A"), "")
        note = r["備考"]
        winner_raw = r["勝者"]
        winner = team_a if (winner_raw and winner_raw == raw_a) else (team_b if (winner_raw and winner_raw == raw_b) else "")
        winner_basis = ""
        if winner:
            if "目視で訂正" in note:
                winner_basis = "訂正"
            elif "結果は高校サッカードットコム" in note:
                winner_basis = "外部"
            elif r["状態"] == "スコア記載なし":
                winner_basis = "赤線"
            elif r["状態"] in ("スコアのみ記載（赤線未反映）", "赤線が両側（スコアで判定）"):
                winner_basis = "スコア"
            else:
                winner_basis = "赤線"
        url = r["出典PDF"]
        source_id = src_reg.get_or_create(url, common.TOURNAMENT_SOURCE_KIND, "高体連PDF", title=r["PDFタイトル"])
        # チーム名が空欄（PDF 上の未確定枠・読み取れなかった枠）のときは match_id が team_id だけで
        # 決まらないので、生の校名を代わりに使う。それでも重なる場合（生の校名も空・同じ）は
        # #2・#3... を付けて必ず一意にする（検査1：主キーの重複）
        ta_key, tb_key = (team_a or f"∅{raw_a}"), (team_b or f"∅{raw_b}")
        ta, tb = sorted([ta_key, tb_key])
        base_id = f"{comp_id}|{area}/{block}|{rnd}|{ta}|{tb}"
        id_counts[base_id] = id_counts.get(base_id, 0) + 1
        match_id = base_id if id_counts[base_id] == 1 else f"{base_id}#{id_counts[base_id]}"
        matches.append({
            "match_id": match_id, "comp_id": comp_id, "area": area, "block": block,
            "page": r["ページ"], "round": rnd, "match_no": r["試合番号"], "date": date, "date_text": date_text,
            "team_a": team_a, "team_b": team_b, "raw_a": raw_a, "raw_b": raw_b,
            "score_a": r["得点A"], "score_b": r["得点B"], "pk_a": r["PK_A"], "pk_b": r["PK_B"],
            "extra_time": "1" if "(延長)" in r["スコア"] else "0", "halves": r["前後半"],
            "status": STATUS_OLD_TO_NEW.get(r["状態"], ""),
            "winner": winner, "winner_basis": winner_basis, "source_id": source_id, "note": note,
        })
        msrc.append({
            "match_id": match_id, "source_id": source_id, "seq": 1, "role": "主",
            "raw_a": raw_a, "raw_b": raw_b, "flipped": 0, "date_text": date_text, "round": rnd,
            "src_row": "", "src_seq": "",  # 大会（トーナメント）には該当しない
        })
        dkey = (r["年度"], r["大会"], r["段階"], r["ラウンド"], frozenset((key_a, key_b)))
        key_to_matchid[dkey] = (match_id, key_a, key_b)
        if "結果は高校サッカードットコム" in note:
            koko_url = f"{common.KOKO_URL}#{comp_id}"
            koko_sid = src_reg.get_or_create(koko_url, "Webページ", common.KOKO_FEED, title="高校サッカードットコム")
            msrc.append({
                "match_id": match_id, "source_id": koko_sid, "seq": 1, "role": "補完",
                "raw_a": raw_a, "raw_b": raw_b, "flipped": 0, "date_text": "", "round": "",
                "src_row": "", "src_seq": "",
            })
    return matches, msrc, key_to_matchid


def attach_dropped_duplicates(dropped_rows, key_to_matchid, src_reg):
    extra_msrc, unmatched = [], []
    seq_counter: dict[tuple, int] = {}
    for r in dropped_rows:
        key_a, key_b = r["チームA_正規化"], r["チームB_正規化"]
        dkey = (r["年度"], r["大会"], r["段階"], r["ラウンド"], frozenset((key_a, key_b)))
        hit = key_to_matchid.get(dkey)
        if hit is None:
            unmatched.append(r)
            continue
        match_id, surv_a, _surv_b = hit
        flipped = 1 if (key_a != surv_a) else 0
        url = r["出典PDF"]
        source_id = src_reg.get_or_create(url, common.TOURNAMENT_SOURCE_KIND, "高体連PDF", title=r["PDFタイトル"])
        seq_counter[(match_id, source_id)] = seq_counter.get((match_id, source_id), 1) + 1
        extra_msrc.append({
            "match_id": match_id, "source_id": source_id, "seq": seq_counter[(match_id, source_id)], "role": "重複",
            "raw_a": r["チームA"], "raw_b": r["チームB"], "flipped": flipped,
            "date_text": r["日付"], "round": r["ラウンド"],
            "src_row": "", "src_seq": "",
        })
    return extra_msrc, unmatched


# ---------------------------------------------------------------------------
# 試合（リーグ）
# ---------------------------------------------------------------------------


def build_league_matches(kept, comps, team_id_of, src_reg):
    matches, msrc = [], []
    n_counter: dict[tuple, int] = {}
    for r in kept:
        season = int(r["年度"])
        comp_id = ensure_league_comp(comps, season, r["リーグ"], r["区分"])
        block = r["区分"]
        area = ""
        hk, hs = r["ホーム学校"], (r["ホーム区分"] or "A")
        ak, as_ = r["アウェイ学校"], (r["アウェイ区分"] or "A")
        team_a = team_id_of.get((hk, hs), "")
        team_b = team_id_of.get((ak, as_), "")
        date_text = r["日付"]
        date = date_text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text or "") else ""
        pairkey = (comp_id, area, block, team_a, team_b)
        n_counter[pairkey] = n_counter.get(pairkey, 0) + 1
        n = n_counter[pairkey]
        match_id = f"{comp_id}|{area}/{block}|{team_a}>{team_b}|{n}"
        gh, ga = r["得点H"], r["得点A"]
        winner = team_a if gh > ga else team_b if ga > gh else ""
        source_id = src_reg.get_or_create(r["出典"], common.source_kind_of_url(r["出典"]), common.FEED_OF_KIND[r["出どころ"]])
        matches.append({
            "match_id": match_id, "comp_id": comp_id, "area": area, "block": block,
            "page": "", "round": r["節"], "match_no": "", "date": date, "date_text": date_text,
            "team_a": team_a, "team_b": team_b, "raw_a": r["生ホーム"], "raw_b": r["生アウェイ"],
            "score_a": gh, "score_b": ga, "pk_a": "", "pk_b": "",
            "extra_time": "0", "halves": "", "status": "済",
            "winner": winner, "winner_basis": "リーグ" if winner else "", "source_id": source_id, "note": "",
        })
        msrc.append({
            "match_id": match_id, "source_id": source_id, "seq": 1, "role": "主",
            "raw_a": r["生ホーム"], "raw_b": r["生アウェイ"], "flipped": 0,
            "date_text": date_text, "round": r["節"],
            "src_row": r["src_row"], "src_seq": r["src_seq"],
        })
    return matches, msrc, n_counter


SCHEDULED_SOURCES = [
    ("district_matches.csv", "goalnote", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分", "部", "節"),
    ("tleague_matches.csv", "Tリーグ公式", "ホーム", "ホーム学校", "ホーム区分", "アウェイ", "アウェイ学校", "アウェイ区分", "ブロック", "節"),
    ("prince_kanto1_2026_matches.csv", "プリンス", "ホーム", "ホーム学校", None, "アウェイ", "アウェイ学校", None, None, None),
]


def build_scheduled_matches(comps, team_id_of, src_reg, n_counter):
    matches, msrc, raw_touch = [], [], []
    for fname, feed, hraw, hsch, hsq, araw, asch, asq, divcol, seccol in SCHEDULED_SOURCES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            if r.get("実施") != "未":
                continue
            season = int(r["年度"])
            league_name = r["リーグ"]
            div = re.sub(r"ブロック$", "", (r.get(divcol) or "").strip()) if divcol else ""
            hk, hs = r.get(hsch, ""), ((r.get(hsq) or "A") if hsq else "A")
            ak, as_ = r.get(asch, ""), ((r.get(asq) or "A") if asq else "A")
            if not hk or not ak or hk == ak:
                continue
            comp_id = ensure_league_comp(comps, season, league_name, div)
            team_a = team_id_of.get((hk, hs), "")
            team_b = team_id_of.get((ak, as_), "")
            if not team_a or not team_b:
                continue
            raw_touch.append((hk, hs, ak, as_, season))
            date_text = (r.get("日付") or "").strip()[:10]
            date = date_text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text or "") else ""
            pairkey = (comp_id, "", div, team_a, team_b)
            n_counter[pairkey] = n_counter.get(pairkey, 0) + 1
            n = n_counter[pairkey]
            match_id = f"{comp_id}|/{div}|{team_a}>{team_b}|{n}"
            round_ = r.get(seccol, "") if seccol else ""
            source_id = src_reg.get_or_create(r["出典"], common.source_kind_of_url(r["出典"]), feed)
            raw_h, raw_a_ = r.get(hraw, hk), r.get(araw, ak)
            matches.append({
                "match_id": match_id, "comp_id": comp_id, "area": "", "block": div,
                "page": "", "round": round_, "match_no": "", "date": date, "date_text": date_text,
                "team_a": team_a, "team_b": team_b, "raw_a": raw_h, "raw_b": raw_a_,
                "score_a": "", "score_b": "", "pk_a": "", "pk_b": "",
                "extra_time": "0", "halves": "", "status": "予定",
                "winner": "", "winner_basis": "", "source_id": source_id, "note": "",
            })
            msrc.append({
                "match_id": match_id, "source_id": source_id, "seq": 1, "role": "主",
                "raw_a": raw_h, "raw_b": raw_a_, "flipped": 0, "date_text": date_text, "round": round_,
                "src_row": "", "src_seq": "",  # 予定（未実施）行は load_all()/rating の対象外
            })
    return matches, msrc, raw_touch


def attach_league_dropped(dropped_rows, kept_index, src_reg):
    """load_all_enriched() の落ちた行を、同じ key() の生き残り試合の match_sources（role=重複）にする。"""
    extra_msrc, unmatched = [], []
    seq_counter: dict[tuple, int] = {}

    def key(r):
        pair = sorted([(r["ホーム学校"], r["得点H"]), (r["アウェイ学校"], r["得点A"])])
        return (r["年度"], *[x for p in pair for x in p])

    for r in dropped_rows:
        hit = kept_index.get(key(r))
        if not hit:
            unmatched.append(r)
            continue
        match_id, surv_home = hit
        flipped = 1 if r["ホーム学校"] != surv_home else 0
        source_id = src_reg.get_or_create(r["出典"], common.source_kind_of_url(r["出典"]), common.FEED_OF_KIND[r["出どころ"]])
        seq_counter[(match_id, source_id)] = seq_counter.get((match_id, source_id), 1) + 1
        extra_msrc.append({
            "match_id": match_id, "source_id": source_id, "seq": seq_counter[(match_id, source_id)], "role": "重複",
            "raw_a": r["生ホーム"], "raw_b": r["生アウェイ"], "flipped": flipped,
            "date_text": r["日付"], "round": r.get("節", ""),
            "src_row": r["src_row"], "src_seq": r["src_seq"],
        })
    return extra_msrc, unmatched


# ---------------------------------------------------------------------------
# 訂正
# ---------------------------------------------------------------------------


def build_corrections(old_matches, stem_to_url):
    field_map = {"score1": "score_a", "score2": "score_b", "pk1": "pk_a", "pk2": "pk_b", "notes": "note"}
    by_url_teams: dict[tuple, list[dict]] = {}
    for r in old_matches:
        by_url_teams.setdefault((r["出典PDF"], r["チームA"], r["チームB"]), []).append(r)

    rows = []
    unmatched = []
    for c in common.read_csv(ROOT / "corrections.csv"):
        url = stem_to_url.get(c["file"])
        matches = by_url_teams.get((url, c["team1"], c["team2"]), []) if url else []
        if not matches:
            unmatched.append(c)
            continue
        for r in matches:
            field = c["field"]
            if field == "winner_slot":
                new_field = "winner"
                key_a = r["チームA_正規化"]
                value = r["_team_a_id"] if c["value"] == "1" else r["_team_b_id"]
            else:
                new_field = field_map.get(field, field)
                value = c["value"]
            rows.append({
                "match_id": r["_match_id"], "field": new_field, "value": value,
                "reason": c["reason"], "source_id": "", "date": "",
            })
    rows.sort(key=lambda r: (r["match_id"], r["field"]))
    return rows, unmatched


# ---------------------------------------------------------------------------
# 順位表
# ---------------------------------------------------------------------------

STANDINGS_SOURCES = [
    # (ファイル, リーグ名の列, comp_id 用の区分の列, 区分（チーム）の列, block の列)
    # block は matches.csv の block と同じ考え方で決める：goalnote は「部」、Tリーグは「ブロック」
    ("district_standings.csv", "リーグ", "部", "区分", "部"),
    ("tleague_standings.csv", "リーグ", None, "区分", "ブロック"),
    ("tleague_history_standings.csv", "リーグ", None, None, None),
    ("prince_kanto1_2026_standings.csv", "リーグ", None, None, None),
]


def scan_standings_raw(reg: SchoolRegistry) -> None:
    """順位表だけに出てくる学校（実際の試合行が見つからない・0試合のチーム等）も学校として登録する。

    「チーム」列が出典の生の書き方（原文）、「学校」列がその行なりの分割結果。試合の生データと
    同じ考え方（raw -> 分割結果を legacy_key とする）で touch する（2026-09-30、T5 で不足が見つかり追加）。
    """
    for fname, _leaguecol, _divcol, squadcol, _blockcol in STANDINGS_SOURCES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            y = (r.get("年度") or "").strip()
            if not re.fullmatch(r"-?\d+", y):
                continue
            season = int(y)
            key = r.get("学校", "")
            raw = r.get("チーム", "")
            if not key:
                continue
            reg.touch_school(key, season, in_league=True)
            reg.touch_name(raw, key, season)


def build_standings(team_id_of, comps, src_reg):
    rows = []
    unresolved = []
    for fname, leaguecol, divcol, squadcol, blockcol in STANDINGS_SOURCES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            season = int(r["年度"])
            league_name = r[leaguecol]
            div = (r.get(divcol) or "") if divcol else ""
            comp_id = ensure_league_comp(comps, season, league_name, div)
            block = (r.get(blockcol) or "") if blockcol else ""
            block = re.sub(r"ブロック$", "", block.strip()) if block else ""
            school = r["学校"]
            squad = (r.get(squadcol) or "A") if squadcol else "A"
            team_id = team_id_of.get((school, squad), "")
            if not team_id:
                unresolved.append((fname, school, squad))
                continue
            src_text = r["出典"]
            basis = "試合から計算" if "試合から計算" in src_text else "公式"
            source_id = src_reg.get_or_create(src_text, common.source_kind_of_url(src_text), common.FEED_OF_KIND.get(
                {"district_standings.csv": "goalnote", "tleague_standings.csv": "Tリーグ公式",
                 "tleague_history_standings.csv": "Tリーグ過去", "prince_kanto1_2026_standings.csv": "プリンス"}[fname], "Webページ"))
            gf, ga = r.get("得点", ""), r.get("失点", "")
            rows.append({
                "comp_id": comp_id, "block": block, "team_id": team_id,
                "rank": r["順位"], "played": r["試合"], "won": r["勝"],
                "drawn": r["分"], "lost": r["敗"], "goals_for": gf, "goals_against": ga,
                "points": r["勝点"], "basis": basis, "as_of": "", "source_id": source_id,
            })
    rows.sort(key=lambda r: (r["comp_id"], r["block"], r["team_id"]))
    return rows, unresolved


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------


def stem_url_maps():
    stem_to_url, url_to_stem = {}, {}
    for p in sorted((ROOT / "out/json").glob("*.json")):
        meta = build_outputs.file_meta(p.stem)
        stem_to_url[p.stem] = meta["url"]
        url_to_stem[meta["url"]] = p.stem
    return stem_to_url, url_to_stem


def run(verbose: bool = True) -> dict:
    out_dir = paths.dataset_dir()

    old_matches = common.read_csv(ROOT / "out/matches.csv")
    dropped_rows = common.read_csv(ROOT / "out/dropped_duplicates.csv")
    stem_to_url, url_to_stem = stem_url_maps()
    member_areas = json.loads((ROOT / "out/scout/member_areas.json").read_text(encoding="utf-8"))

    league_kept, league_dropped = league_source.load_all_enriched()

    # --- 学校・校名 --------------------------------------------------------
    reg = SchoolRegistry()
    scan_tournament(reg, old_matches)
    scan_tournament(reg, dropped_rows)
    scan_league_raw(reg)
    scan_standings_raw(reg)
    skipped_aliases = scan_aliases(reg)

    # 同じ書き方が2つの学校を指すケース：段階1では統合しない（コーディネーター判断・2026-09-30）。
    # school_names.csv には登録せず、schools.csv に note を残し、known-issues.md に出典つきで書き出す。
    ambiguous_names, partner_map = compute_ambiguous(reg)
    nihongakuen_rows = [
        r for r in common.read_csv(ROOT / "data/leagues/district_matches.csv")
        if r.get("年度") == "2026" and (r.get("ホーム") == "日本学園B" or r.get("アウェイ") == "日本学園B")
    ]
    existing_schools = common.read_csv(out_dir / "schools.csv")
    id_of = assign_school_ids(reg, existing_schools)
    schools, kind_tally = build_schools(reg, id_of, member_areas, partner_map)
    school_names = build_school_names(reg, id_of, ambiguous_names)

    bracket_anomalies = find_bracket_anomaly_school_ids(schools)
    known_issues_count = write_known_issues_doc(reg, ambiguous_names, partner_map, nihongakuen_rows, bracket_anomalies)

    # --- チーム --------------------------------------------------------
    # 予定（未実施）のリーグ戦もチームの初出・最終に反映させるため、先に生の未実施行を集める
    scheduled_touch: list[tuple] = []
    for fname, _feed, _hraw, hsch, hsq, _araw, asch, asq, _divcol, _seccol in SCHEDULED_SOURCES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            if r.get("実施") != "未":
                continue
            y = (r.get("年度") or "").strip()
            if not re.fullmatch(r"-?\d+", y):
                continue
            season = int(y)
            hk, hs = r.get(hsch, ""), ((r.get(hsq) or "A") if hsq else "A")
            ak, as_ = r.get(asch, ""), ((r.get(asq) or "A") if asq else "A")
            if hk and ak and hk != ak:
                scheduled_touch.append((hk, hs, ak, as_, season))

    # 順位表だけに出てくるチーム（0試合の新規参加・実際の試合行が見つからない等）も teams.csv に持つ
    standings_touch: list[tuple] = []
    for fname, _leaguecol, _divcol, squadcol, _blockcol in STANDINGS_SOURCES:
        for r in common.read_csv(ROOT / "data/leagues" / fname):
            y = (r.get("年度") or "").strip()
            if not re.fullmatch(r"-?\d+", y):
                continue
            key = r.get("学校", "")
            if not key:
                continue
            squad = (r.get(squadcol) or "A") if squadcol else "A"
            standings_touch.append((key, squad, int(y)))

    teams_seen = scan_teams(old_matches, dropped_rows, league_kept, league_dropped, scheduled_touch, standings_touch)
    teams, team_id_of = build_teams(teams_seen, id_of)

    # --- 出典レジストリ --------------------------------------------------
    existing_sources = common.read_csv(out_dir / "sources.csv")
    src_reg = SourceRegistry(existing_sources)

    # --- 大会・試合（大会） -------------------------------------------
    comps = build_competitions(old_matches)
    t_matches, t_msrc, key_to_matchid = build_tournament_matches(old_matches, team_id_of, src_reg)

    # 訂正の突き合わせ用に、each old_matches 行へ新 match_id / team_id を埋め込む
    for r, m in zip(old_matches, t_matches):
        r["_match_id"] = m["match_id"]
        r["_team_a_id"] = m["team_a"]
        r["_team_b_id"] = m["team_b"]

    dup_msrc, dup_unmatched = attach_dropped_duplicates(dropped_rows, key_to_matchid, src_reg)

    # --- 試合（リーグ） --------------------------------------------------
    l_matches, l_msrc, n_counter = build_league_matches(league_kept, comps, team_id_of, src_reg)
    sched_matches, sched_msrc, _ = build_scheduled_matches(comps, team_id_of, src_reg, n_counter)

    def kept_key(r):
        pair = sorted([(r["ホーム学校"], r["得点H"]), (r["アウェイ学校"], r["得点A"])])
        return (r["年度"], *[x for p in pair for x in p])

    kept_index = {}
    for r, m in zip(league_kept, l_matches):
        kept_index.setdefault(kept_key(r), (m["match_id"], r["ホーム学校"]))
    ldup_msrc, ldup_unmatched = attach_league_dropped(league_dropped, kept_index, src_reg)

    # --- 訂正 --------------------------------------------------------
    corrections, corr_unmatched = build_corrections(old_matches, stem_to_url)
    if corr_unmatched:
        raise StopForReview(f"訂正が試合に対応しません: {[ (c['file'], c['team1'], c['team2']) for c in corr_unmatched ]}")

    # --- 順位表 --------------------------------------------------------
    standings, standings_unresolved = build_standings(team_id_of, comps, src_reg)

    # --- sha256 --------------------------------------------------------
    fill_sha256(src_reg, url_to_stem)

    all_matches = t_matches + l_matches + sched_matches
    all_matches.sort(key=lambda r: r["match_id"])
    all_msrc = t_msrc + dup_msrc + l_msrc + ldup_msrc + sched_msrc
    all_msrc.sort(key=lambda r: (r["match_id"], r["source_id"], r["seq"]))
    comps_rows = sorted(comps.values(), key=lambda r: r["comp_id"])
    sources_rows = src_reg.rows()

    tables = {
        "schools.csv": (
            ["school_id", "name", "official_name", "kind", "district", "city", "legacy_key", "note"], schools),
        "school_names.csv": (
            ["name", "school_id", "kind", "first_season", "last_season"], school_names),
        "teams.csv": (
            ["team_id", "school_id", "squad", "first_season", "last_season"], teams),
        "competitions.csv": (
            ["comp_id", "season", "series", "stage", "edition", "level", "format", "district"], comps_rows),
        "matches.csv": (
            ["match_id", "comp_id", "area", "block", "page", "round", "match_no", "date", "date_text",
             "team_a", "team_b", "raw_a", "raw_b", "score_a", "score_b", "pk_a", "pk_b", "extra_time",
             "halves", "status", "winner", "winner_basis", "source_id", "note"], all_matches),
        "standings.csv": (
            ["comp_id", "block", "team_id", "rank", "played", "won", "drawn", "lost",
             "goals_for", "goals_against", "points", "basis", "as_of", "source_id"], standings),
        "sources.csv": (
            ["source_id", "kind", "feed", "url", "archive_url", "title", "sha256", "note"], sources_rows),
        "match_sources.csv": (
            ["match_id", "source_id", "seq", "role", "raw_a", "raw_b", "flipped", "date_text", "round",
             "src_row", "src_seq"], all_msrc),
        "corrections.csv": (
            ["match_id", "field", "value", "reason", "source_id", "date"], corrections),
    }

    for fname, (cols, rows) in tables.items():
        common.write_csv(out_dir / fname, cols, rows)

    report = {
        "counts": {k: len(v[1]) for k, v in tables.items()},
        "kind_tally": kind_tally,
        "skipped_aliases": skipped_aliases,
        "dup_unmatched_tournament": dup_unmatched,
        "dup_unmatched_league": ldup_unmatched,
        "standings_unresolved": standings_unresolved,
        "ambiguous_names": sorted(ambiguous_names),
        "ambiguous_schools_noted": kind_tally.get("ambiguous_pair", 0),
        "known_issues_count": known_issues_count,
        "bracket_anomaly_school_ids": sorted(bracket_anomalies.keys()),
    }
    if verbose:
        for k, v in report["counts"].items():
            print(f"{k}: {v}")
    return report


if __name__ == "__main__":
    run()
