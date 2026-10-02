"""読み込み先を決める関数を1つだけ置く（段階2）。

環境変数 SOCCER_SOURCE が "legacy" ならリポジトリの旧来の場所（out/・data/ 等）をそのまま使う。
それ以外（既定）なら、Vault の9表から実体化した out/legacy/ 配下を使う
（dataset.materialize が書き出す。uv run python -m dataset.materialize）。

  source.path("out/matches.csv")
    -> SOCCER_SOURCE=legacy: ROOT/out/matches.csv
    -> 既定:                 ROOT/out/legacy/out/matches.csv
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_OUT_DIR = ROOT / "out/legacy"


def is_legacy_mode() -> bool:
    return os.environ.get("SOCCER_SOURCE") == "legacy"


def path(rel: str) -> Path:
    """旧データのファイルパス。rel はリポジトリルートからの相対パス（例: "out/matches.csv"）。"""
    if is_legacy_mode():
        return ROOT / rel
    return LEGACY_OUT_DIR / rel
