"""書き出し先（Vault の Datasets/tokyo-hs-soccer/）。

環境変数 SOCCER_DATASET_DIR があればそれを使う。無ければ既定のパス。
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DIR = r"C:\Users\shnbt\dev\obsidian-vault\Datasets\tokyo-hs-soccer"

TABLES = [
    "schools.csv",
    "school_names.csv",
    "teams.csv",
    "competitions.csv",
    "matches.csv",
    "standings.csv",
    "sources.csv",
    "match_sources.csv",
    "corrections.csv",
    "school_merges.csv",
]


def dataset_dir() -> Path:
    return Path(os.environ.get("SOCCER_DATASET_DIR", DEFAULT_DIR))
