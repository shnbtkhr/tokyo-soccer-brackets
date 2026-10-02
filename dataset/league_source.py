"""leagues.load_all() と同じ選別を、出典・節・生表記・並び順つきで複製する。

leagues.py 自体は変えない。`_num`（内部ヘルパー）を再利用し、
`_mk`・`key`・選別ループだけを、あとで出典や生表記・並び順を辿れるように余分なフィールドを
残す形で複製する。選別の結果（残った行の集合）は leagues.load_all() と一致するはずで、
それは tests/test_dataset_roundtrip.py の T3 が確かめる。

`_rows` は leagues.py からは再利用しない（独自に持つ）。段階2で leagues.py の `_rows` が
`dataset.source.path()` 経由（既定では Vault から実体化した out/legacy/ 配下）を読むようになった
ため、書く側である本モジュール（dataset.export が使う）は常に本物の data/leagues/ を読む必要が
ある。読む側の切り替えに巻き込まれると、export が自分の作った実体化ファイルを読み返す循環になり、
T3・T6 が壊れる（2026-10-01、段階2 switch で実際に発生）。

並び順を復元するために2つの整数を残す（dataset.export が match_sources.csv の
src_row・src_seq 列に書く。2026-09-30、コーディネーターの指示で SCHEMA.md に追加）：

- src_row: その行の、出典ファイルの中での1始まりの行番号（実施="未"の行も含めて数える。
  rating.league_games() が csv.DictReader でファイルをそのまま読む順そのものなので、
  T4（rating の往復）はこれで並べ直せば再現できる）
- src_seq: load_all() が最終の (年度,リーグ,日付) 並べ替えを行う直前の候補列 `order` の中での
  1始まりの位置。`order` は「日付の有無」→「出どころ名」→（同じ出どころの中では）元の並びの順に
  安定ソートしたもの。T3（load_all() の往復）で、(年度,リーグ,日付) が同じ行のタイブレークに使う
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from leagues import _num

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DIR = ROOT / "data/leagues"


def _rows(name: str) -> list[dict]:
    p = _DIR / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _mk2(year, league, div, date, h, hd, a, ad, gh, ga, src, kind, sec="", raw_h="", raw_a_="", src_row=0) -> dict | None:
    ghn, gan = _num(gh), _num(ga)
    if ghn is None or gan is None or not h or not a or h == a:
        return None
    div = re.sub(r"ブロック$", "", str(div or "").strip())
    return {
        "年度": str(year), "リーグ": league, "区分": div, "日付": (date or "").strip()[:10],
        "ホーム学校": h, "ホーム区分": (hd or "").strip(), "アウェイ学校": a, "アウェイ区分": (ad or "").strip(),
        "得点H": ghn, "得点A": gan, "出典": src, "出どころ": kind,
        "節": str(sec or "").strip(),
        "生ホーム": raw_h or h, "生アウェイ": raw_a_ or a,
        "src_row": src_row, "src_seq": 0,  # src_seq は load_all_enriched() の最後に埋める
    }


def _rows_enum(fname: str) -> list[tuple[int, dict]]:
    """(1始まりの行番号, 行) のリスト。実施="未" の行も番号に数える（ファイルそのものの行番号のため）。"""
    return list(enumerate(_rows(fname), start=1))


def load_all_enriched(canon=None) -> tuple[list[dict], list[dict]]:
    """(残った行, 落ちた行)。フィールドは load_all() と同じ + 節・生ホーム・生アウェイ・src_row・src_seq。

    canon: 学校の legacy_key -> まとめ先の legacy_key を返す関数（名寄せ後の重なり整理用。
    行の中身は書き換えず、重なりを数える鍵だけに使う。None なら学校名そのまま）。"""
    _c = canon or (lambda k: k)
    groups: dict[str, list[dict]] = defaultdict(list)

    def add(kind: str, rows: list[dict]) -> None:
        for r in rows:
            if r:
                groups[kind].append(r)

    add("星取表", [_mk2(r["年度"], r["リーグ"], r["区分"], "", r["ホーム学校"], r["ホーム区分"],
                     r["アウェイ学校"], r["アウェイ区分"], r["得点H"], r["得点A"], r["出典"], "星取表",
                     raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                 for i, r in _rows_enum("district_stars_matches.csv")])
    add("goalnote", [_mk2(r["年度"], r["リーグ"], r["部"], r["日付"], r["ホーム学校"], r["ホーム区分"],
                         r["アウェイ学校"], r["アウェイ区分"], r["ホーム得点"], r["アウェイ得点"], r["出典"], "goalnote",
                         sec=r.get("節"), raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                     for i, r in _rows_enum("district_matches.csv") if r.get("実施") == "済"])
    add("Tリーグ公式", [_mk2(r["年度"], r["リーグ"], r.get("ブロック", ""), r["日付"], r["ホーム学校"], r.get("ホーム区分", ""),
                        r["アウェイ学校"], r.get("アウェイ区分", ""), r["ホーム得点"], r["アウェイ得点"], r["出典"], "Tリーグ公式",
                        sec=r.get("節"), raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                    for i, r in _rows_enum("tleague_matches.csv") if r.get("実施") == "済"])
    add("Tリーグ過去", [_mk2(r["年度"], "Tリーグ", r["リーグ"], r["日付"], r["学校H"], "", r["学校A"], "",
                        r["得点H"], r["得点A"], r["出典"], "Tリーグ過去", raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                    for i, r in _rows_enum("tleague_archive_matches.csv")])
    add("Tリーグ過去", [_mk2(r["年度"], "Tリーグ", r["リーグ"], r["日時"], r["学校H"], "", r["学校A"], "",
                        r["得点H"], r["得点A"], r["出典"], "Tリーグ過去", raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                    for i, r in _rows_enum("tleague_history_matches.csv")])
    add("プリンス", [_mk2(r["年度"], r["リーグ"], "", r["日付"], r["ホーム学校"], "", r["アウェイ学校"], "",
                     r["ホーム得点"], r["アウェイ得点"], r["出典"], "プリンス", raw_h=r["ホーム"], raw_a_=r["アウェイ"], src_row=i)
                 for i, r in _rows_enum("prince_kanto1_2026_matches.csv") if r.get("実施") == "済"])

    def key(r: dict) -> tuple:
        pair = sorted([(_c(r["ホーム学校"]), r["得点H"]), (_c(r["アウェイ学校"]), r["得点A"])])
        return (r["年度"], *[x for p in pair for x in p])

    counts: dict[tuple, Counter] = defaultdict(Counter)
    for kind, rows in groups.items():
        for r in rows:
            counts[key(r)][kind] += 1
    order = sorted((r for rows in groups.values() for r in rows),
                   key=lambda r: (not r["日付"], r["出どころ"]))
    for i, r in enumerate(order, start=1):
        r["src_seq"] = i
    used: Counter = Counter()
    kept, dropped = [], []
    for r in order:
        k = key(r)
        if used[k] < max(counts[k].values()):
            used[k] += 1
            kept.append(r)
        else:
            dropped.append(r)
    kept.sort(key=lambda r: (r["年度"], r["リーグ"], r["日付"]))
    return kept, dropped
