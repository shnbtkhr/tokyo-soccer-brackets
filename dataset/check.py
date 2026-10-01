"""SCHEMA.md の「検査」6項目。

  uv run python -m dataset.check

どれか1つでも引っかかれば終了コード1。結果は標準出力に日本語で書く。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset import common, paths  # noqa: E402

KNOWN_ISSUES_PATH = ROOT / "notes/dataset-known-issues.md"


def known_issue_names(path: Path | None = None) -> set[str]:
    """notes/dataset-known-issues.md の「名寄せの競合」表から、除外してよい生の書き方を読む。

    dataset.export.write_known_issues_doc() が書く表の1列目（`| 生の書き方 | ... |`）をそのまま拾う。
    """
    p = path or KNOWN_ISSUES_PATH
    if not p.exists():
        return set()
    names = set()
    in_table = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("| 生の書き方 "):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if line.startswith("|---"):
                continue
            cell = line.split("|")[1].strip()
            if cell:
                names.add(cell)
    return names


def known_bracket_anomaly_school_ids(path: Path | None = None) -> set[str]:
    """notes/dataset-known-issues.md の「検査4・5では除外」表から、除外してよい school_id を読む。"""
    p = path or KNOWN_ISSUES_PATH
    if not p.exists():
        return set()
    ids = set()
    in_table = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("| school_id "):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if line.startswith("|---"):
                continue
            cell = line.split("|")[1].strip()
            if cell:
                ids.add(cell)
    return ids


def is_name_registered(name: str, school_names_index: set[str], exempt: set[str] | None = None) -> bool:
    """あとから取り込みが「この生の書き方は既知か」を確かめるのに呼ぶ関数（SCHEMA.md 検査6の実装本体）。

    `Sources/` からの新規取り込み時、ここが False を返したら取り込みを止めて人に確かめる
    （school_names.csv に無い書き方が黙って新しい学校になるのを防ぐため）。
    """
    if name in school_names_index:
        return True
    if exempt and name in exempt:
        return True
    return False


def check_unique_keys(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    pk = {
        "schools.csv": ["school_id"],
        "school_names.csv": ["name"],
        "teams.csv": ["team_id"],
        "competitions.csv": ["comp_id"],
        "matches.csv": ["match_id"],
        "standings.csv": ["comp_id", "block", "team_id"],
        "sources.csv": ["source_id"],
        "match_sources.csv": ["match_id", "source_id", "seq"],
        "corrections.csv": [],  # 明示の主キーなし（同一 match_id に複数の訂正がありうる）
    }
    for name, cols in pk.items():
        if not cols:
            continue
        seen = set()
        for r in tables[name]:
            key = tuple(r[c] for c in cols)
            if key in seen:
                problems.append(f"{name}: 主キー重複 {dict(zip(cols, key))}")
            seen.add(key)
    return problems


def check_references(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    team_ids = {r["team_id"] for r in tables["teams.csv"]}
    school_ids = {r["school_id"] for r in tables["schools.csv"]}
    comp_ids = {r["comp_id"] for r in tables["competitions.csv"]}
    source_ids = {r["source_id"] for r in tables["sources.csv"]}

    for r in tables["teams.csv"]:
        if r["school_id"] not in school_ids:
            problems.append(f"teams.csv: school_id {r['school_id']} が schools.csv に無い")
    for r in tables["school_names.csv"]:
        if r["school_id"] not in school_ids:
            problems.append(f"school_names.csv: school_id {r['school_id']} が schools.csv に無い（name={r['name']}）")
    for r in tables["matches.csv"]:
        if r["comp_id"] not in comp_ids:
            problems.append(f"matches.csv: comp_id {r['comp_id']} が competitions.csv に無い")
        for side in ("team_a", "team_b"):
            if r[side] and r[side] not in team_ids:
                problems.append(f"matches.csv: {side}={r[side]} が teams.csv に無い（match_id={r['match_id']}）")
        if r["source_id"] and r["source_id"] not in source_ids:
            problems.append(f"matches.csv: source_id {r['source_id']} が sources.csv に無い（match_id={r['match_id']}）")
        if r["winner"] and r["winner"] not in (r["team_a"], r["team_b"]):
            problems.append(f"matches.csv: winner={r['winner']} が team_a/team_b のどちらでもない（match_id={r['match_id']}）")
    for r in tables["standings.csv"]:
        if r["comp_id"] not in comp_ids:
            problems.append(f"standings.csv: comp_id {r['comp_id']} が competitions.csv に無い")
        if r["team_id"] not in team_ids:
            problems.append(f"standings.csv: team_id {r['team_id']} が teams.csv に無い")
        if r["source_id"] and r["source_id"] not in source_ids:
            problems.append(f"standings.csv: source_id {r['source_id']} が sources.csv に無い")
    for r in tables["match_sources.csv"]:
        if r["source_id"] not in source_ids:
            problems.append(f"match_sources.csv: source_id {r['source_id']} が sources.csv に無い（match_id={r['match_id']}）")
    return problems


def check_status_score_winner(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    for r in tables["matches.csv"]:
        if r["status"] != "済":
            continue
        if r["score_a"] == "" or r["score_b"] == "":
            problems.append(f"matches.csv: status=済 なのにスコアが無い（match_id={r['match_id']}）")
            continue
        sa, sb = int(r["score_a"]), int(r["score_b"])
        pa, pb = r["pk_a"], r["pk_b"]
        if not r["winner"]:
            continue
        # winner_basis=赤線 は PDF の勝ち上がり線を正とする（旧システムの status_of() も同じ扱い）。
        # 赤線とスコア・PK が食い違う実例が1件ある（2015年度・南9・1回戦）。読み取りの ズレであって
        # 移行の誤りではないため、赤線が根拠の行はこの検査の対象にしない
        if r["winner_basis"] == "赤線":
            continue
        if sa != sb:
            expected = r["team_a"] if sa > sb else r["team_b"]
            if r["winner"] != expected:
                problems.append(f"matches.csv: winner がスコアと矛盾（match_id={r['match_id']}）")
        elif pa != "" and pb != "":
            expected = r["team_a"] if int(pa) > int(pb) else r["team_b"] if int(pb) > int(pa) else ""
            if expected and r["winner"] != expected:
                problems.append(f"matches.csv: winner が PK と矛盾（match_id={r['match_id']}）")
    return problems


def _school_of_team(team_id: str) -> str:
    return team_id.rsplit("-", 1)[0] if team_id else ""


def check_tournament_bracket_size(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    comps = {r["comp_id"]: r for r in tables["competitions.csv"]}
    exempt = known_bracket_anomaly_school_ids()
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in tables["matches.csv"]:
        comp = comps.get(r["comp_id"])
        if not comp or comp["format"] != "トーナメント":
            continue
        if _school_of_team(r["team_a"]) in exempt or _school_of_team(r["team_b"]) in exempt:
            continue  # PDF の読み取りで名前がくっついた「学校」。known-issues.md に記録済み
        # 空欄（未確定枠）・結果不明（行われたかどうかも記録に無い枠。PDF の読み取り誤りで
        # 生じた文字化けの「学校」が多い）は、実在するチーム・試合として数えない
        # 3位決定戦は、準決勝で負けた2チーム（どちらも既に数えたチーム）どうしの追加の1試合なので、
        # 「試合数 ＝ チーム数－1」の勝ち上がり戦の数には含めない（新しいチームを増やさない試合のため）
        if r["team_a"] and r["team_b"] and r["status"] != "結果不明" and r["round"] != "3位決定戦":
            # 「1つの表」は comp_id・地区支部・ページ・ブロックで決まる（page は同じ PDF の
            # 別ページの表を区別するための列。SCHEMA.md の page の説明）
            groups[(r["comp_id"], r["area"], r["page"], r["block"])].append(r)
    for key, rows in groups.items():
        teams = {t for r in rows for t in (r["team_a"], r["team_b"]) if t}
        if not teams:
            continue
        if len(rows) > len(teams) - 1:
            problems.append(f"matches.csv: {key} の試合数 {len(rows)} が出場チーム数 {len(teams)} - 1 を超えている")
    return problems


def check_no_duplicate_team_in_round(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    comps = {r["comp_id"]: r for r in tables["competitions.csv"]}
    exempt = known_bracket_anomaly_school_ids()
    groups: dict[tuple, list[str]] = defaultdict(list)
    for r in tables["matches.csv"]:
        comp = comps.get(r["comp_id"])
        if not comp or comp["format"] != "トーナメント":
            continue
        if r["status"] == "結果不明":  # 行われたかどうかも記録に無い枠（文字化けの「学校」が多い）
            continue
        if _school_of_team(r["team_a"]) in exempt or _school_of_team(r["team_b"]) in exempt:
            continue  # PDF の読み取りで名前がくっついた「学校」。known-issues.md に記録済み
        key = (r["comp_id"], r["area"], r["page"], r["round"])
        for t in (r["team_a"], r["team_b"]):
            if t:
                groups[key].append(t)
    for key, teams in groups.items():
        seen = set()
        for t in teams:
            if t in seen:
                problems.append(f"matches.csv: {key} に同じチーム {t} が2度出ている")
            seen.add(t)
    return problems


def check_known_names(tables: dict[str, list[dict]]) -> list[str]:
    problems = []
    school_names_index = {r["name"] for r in tables["school_names.csv"]}
    exempt = known_issue_names()
    seen_bad = set()
    for r in tables["match_sources.csv"]:
        for name in (r["raw_a"], r["raw_b"]):
            if not name or name in seen_bad:
                continue
            if not is_name_registered(name, school_names_index, exempt):
                problems.append(f"match_sources.csv: 「{name}」が school_names.csv にも既知の問題一覧にも無い")
                seen_bad.add(name)
    return problems


CHECKS = [
    ("1. 主キーの重複", check_unique_keys),
    ("2. 参照先の実在", check_references),
    ("3. status=済 のスコア・勝者の整合", check_status_score_winner),
    ("4. トーナメントの試合数 <= チーム数-1", check_tournament_bracket_size),
    ("5. 同じ大会・回戦に同じチームが2度出ていないか", check_no_duplicate_team_in_round),
    ("6. school_names.csv に無い書き方が無いか（既知の問題は除く）", check_known_names),
]


def run(base: Path | None = None, verbose: bool = True) -> list[str]:
    d = base or paths.dataset_dir()
    tables = {name: common.read_csv(d / name) for name in [
        "schools.csv", "school_names.csv", "teams.csv", "competitions.csv",
        "matches.csv", "standings.csv", "sources.csv", "match_sources.csv", "corrections.csv",
    ]}
    all_problems = []
    for label, fn in CHECKS:
        problems = fn(tables)
        if verbose:
            print(f"{label}: {'OK' if not problems else f'{len(problems)}件'}")
            for p in problems[:20]:
                print(f"  - {p}")
        all_problems.extend(problems)
    return all_problems


def main() -> int:
    problems = run()
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
