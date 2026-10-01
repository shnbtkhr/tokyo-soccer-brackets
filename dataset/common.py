"""9表で共有する定数・小さなユーティリティ。export.py と legacy.py の両方から使う。"""

from __future__ import annotations

import csv
import re
from pathlib import Path

# ---- 大会の段階マッピング（旧「段階」文字列 <-> 新 stage・level）------------------
# キー: (大会, 旧「段階」から edition を除いた残り) -> (新 stage, level)
STAGE_MAP_FORWARD = {
    ("総体", "支部予選"): ("支部予選", "1次"),
    ("総体", "一次トーナメント"): ("都1次トーナメント", "都大会"),
    ("総体", "二次トーナメント"): ("都2次トーナメント", "都大会"),
    ("選手権", "一次予選"): ("1次予選", "1次"),
    ("選手権", "二次予選"): ("2次予選", "都大会"),
    ("新人戦", "地区大会"): ("地区大会", "1次"),
    ("新人戦", "都大会"): ("都大会", "都大会"),
    ("関東", "東京都予選"): ("東京都予選", "都大会"),
}
# 逆引き: (大会, 新 stage) -> 旧「段階」の edition を除いた残り
STAGE_MAP_BACKWARD = {(s, new): old for (s, old), (new, _lvl) in STAGE_MAP_FORWARD.items()}

EDITION_RE = re.compile(r"^(第\d+回)\s*(.+)$")


def split_stage(series: str, old_stage: str) -> tuple[str, str, str, str]:
    """旧「段階」文字列 -> (edition, old_stage_no_edition, new_stage, level)。"""
    m = EDITION_RE.match(old_stage)
    edition, rest = (m[1], m[2]) if m else ("", old_stage)
    new_stage, level = STAGE_MAP_FORWARD.get((series, rest), (rest, ""))
    return edition, rest, new_stage, level


def join_stage(series: str, new_stage: str, edition: str) -> str:
    """新 stage・edition -> 旧「段階」文字列。"""
    rest = STAGE_MAP_BACKWARD.get((series, new_stage), new_stage)
    return f"{edition} {rest}" if edition else rest


FORMAT_OF = {"総体": "トーナメント", "選手権": "トーナメント", "新人戦": "トーナメント", "関東": "トーナメント"}

TOURNAMENT_SOURCE_KIND = "トーナメント表PDF"
KOKO_FEED = "高校サッカードットコム"
KOKO_URL = "https://koko-soccer.com/"

FEED_OF_KIND = {
    "星取表": "星取表",
    "goalnote": "goalnote",
    "Tリーグ公式": "Tリーグ公式",
    "Tリーグ過去": "Tリーグ過去",
    "プリンス": "プリンス",
}

CLUB_HINT_RE = re.compile(r"(FC|F\.C|SC|ヴェルディ)", re.IGNORECASE)


def source_kind_of_url(url: str) -> str:
    return TOURNAMENT_SOURCE_KIND if url.lower().endswith(".pdf") else "Webページ"


# ---- CSV 読み書き（UTF-8 BOM なし・LF・列名は呼び出し側が渡す） --------------------


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        wr.writeheader()
        for r in rows:
            wr.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
