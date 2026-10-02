"""段階2の合格判定：SOCCER_SOURCE=legacy（旧ファイル）と既定（Vault実体化）で組み立て一式を回し、出力を比べる。

  uv run python -m scripts.compare_build          # rating_backtest.py を含めてフル実行
  uv run python -m scripts.compare_build --skip-backtest   # rating_backtest.py を省く（遅いため）

notes/dataset-migration-phase2.md の「合格の確かめ方」のとおり:
  1. SOCCER_SOURCE=legacy で一式を回し、out/_cmp/legacy/ に控える
  2. 既定で一式を回し、out/_cmp/dataset/ に控える
  3. 比べて、違いがあれば一覧を出して終了コード1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PIPELINE_FULL = [
    ["rating_backtest.py"],
    ["analyze_team.py"],
    ["league_coverage.py"],
    ["build_squad.py"],
    ["build_upsets.py"],
    ["build_index.py"],
    ["build_seeds.py"],
    ["build_second.py"],
    ["draw_second.py"],
    ["build_generations.py"],
    ["build_years.py"],
    ["build_history.py"],
    ["build_site.py", "--links", "local"],
]

# 比較対象のファイル（相対パス）。draw_second.py の PDF/PNG は比較対象外（notes/dataset-migration-phase2.md の指定どおり）。
JSON_FILES = [
    "out/scout/backtest.json",
    "out/scout/musashigaoka_sen2026.json",
    "out/scout/coverage.json",
    "out/scout/squad_2026.json",
    "out/scout/upsets_2026.json",
    "out/scout/index_2026.json",
    "out/scout/seeds_2026.json",
    "out/scout/second_2026.json",
    "out/scout/generations.json",
    "out/scout/years.json",
    "out/scout/history_musashigaoka.json",
]
MD_FILES = ["notes/rating_backtest.md"]
HTML_GLOB = "out/site/*.html"

CMP_DIR = ROOT / "out/_cmp"


def run_pipeline(env_extra: dict, steps: list[list[str]]) -> None:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    # PYTHONHASHSEED は固定しない（意図的）。build_index.py の common_opponents() が
    # set() の反復順でタイブレークしていたため legacy 同士の2回実行でも結果が変わる不具合が
    # あったが、ソース側（決定的な第2キーを足す）で直した。ここで固定してしまうと、別の
    # hash 依存の非決定性が残っていても比較が覆い隠してしまうため、素の状態で比べる
    # （2026-10-01、コーディネーター指示）。
    env.update(env_extra)
    for args in steps:
        cmd = ["uv", "run", "python", *args]
        print(f"  $ {' '.join(cmd)}  (SOCCER_SOURCE={env.get('SOCCER_SOURCE', '(既定)')})")
        subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def snapshot(dest: Path) -> list[str]:
    """比較対象ファイルを dest 配下にコピーする。コピーした相対パスの一覧を返す。"""
    copied = []
    for rel in JSON_FILES + MD_FILES:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    for p in sorted((ROOT / "out/site").glob("*.html")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        copied.append(rel)
    return copied


CONST_D_RE = re.compile(r"const D\s*=\s*(\{.*?\});", re.DOTALL)


def extract_embedded_json(html_text: str) -> dict | None:
    m = CONST_D_RE.search(html_text)
    if not m:
        return None
    return json.loads(m.group(1))


def compare_json(rel: str, legacy_dir: Path, dataset_dir: Path, excluded: list[str]) -> str | None:
    a = legacy_dir / rel
    b = dataset_dir / rel
    if not a.exists() and not b.exists():
        return None
    if a.exists() != b.exists():
        return f"{rel}: 片方にしか無い（legacy={a.exists()} dataset={b.exists()}）"
    ja = json.loads(a.read_text(encoding="utf-8"))
    jb = json.loads(b.read_text(encoding="utf-8"))
    if ja == jb:
        return None
    return f"{rel}: JSON の内容が違う\n{diff_summary(ja, jb)}"


def compare_md(rel: str, legacy_dir: Path, dataset_dir: Path) -> str | None:
    a = legacy_dir / rel
    b = dataset_dir / rel
    if not a.exists() and not b.exists():
        return None
    if a.exists() != b.exists():
        return f"{rel}: 片方にしか無い"
    ta, tb = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
    if ta == tb:
        return None
    return f"{rel}: テキストが違う（{len(ta)}字 vs {len(tb)}字）"


def compare_html(rel: str, legacy_dir: Path, dataset_dir: Path) -> str | None:
    a = legacy_dir / rel
    b = dataset_dir / rel
    if not a.exists() and not b.exists():
        return None
    if a.exists() != b.exists():
        return f"{rel}: 片方にしか無い"
    da = extract_embedded_json(a.read_text(encoding="utf-8"))
    db = extract_embedded_json(b.read_text(encoding="utf-8"))
    if da is None and db is None:
        return None  # const D を持たないページ（埋め込みデータなし）
    if da == db:
        return None
    return f"{rel}: 埋め込みデータ（const D）が違う\n{diff_summary(da, db)}"


def diff_summary(a, b, path: str = "$", limit: int = 8) -> str:
    """ネストした構造の最初の数件の違いを人間向けに書き出す。"""
    out = []

    def walk(x, y, p):
        if len(out) >= limit:
            return
        if x == y:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            keys = sorted(set(x) | set(y))
            for k in keys:
                if len(out) >= limit:
                    return
                walk(x.get(k, "<無し>"), y.get(k, "<無し>"), f"{p}.{k}")
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (xi, yi) in enumerate(zip(x, y)):
                if len(out) >= limit:
                    return
                walk(xi, yi, f"{p}[{i}]")
        else:
            out.append(f"  {p}: {x!r}  !=  {y!r}")

    walk(a, b, path)
    if not out and a != b:
        out.append(f"  {path}: (構造が違う。legacy型={type(a).__name__} dataset型={type(b).__name__})")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-backtest", action="store_true", help="rating_backtest.py を省く（1回目で一致を確認済みのとき）")
    args = ap.parse_args()

    steps = PIPELINE_FULL[1:] if args.skip_backtest else PIPELINE_FULL

    legacy_dir = CMP_DIR / "legacy"
    dataset_dir = CMP_DIR / "dataset"

    print("[1/4] SOCCER_SOURCE=legacy で一式を実行")
    run_pipeline({"SOCCER_SOURCE": "legacy"}, steps)
    print("[2/4] 出力を out/_cmp/legacy/ に控える")
    legacy_files = snapshot(legacy_dir)

    print("[3/4] 既定（Vault 実体化）で一式を実行")
    run_pipeline({"SOCCER_SOURCE": ""}, steps)
    print("[4/4] 出力を out/_cmp/dataset/ に控える")
    dataset_files = snapshot(dataset_dir)

    all_rel = sorted(set(legacy_files) | set(dataset_files))
    diffs = []
    identical = []
    for rel in all_rel:
        if rel in MD_FILES:
            d = compare_md(rel, legacy_dir, dataset_dir)
        elif rel.endswith(".html"):
            d = compare_html(rel, legacy_dir, dataset_dir)
        else:
            d = compare_json(rel, legacy_dir, dataset_dir, [])
        if d:
            diffs.append(d)
        else:
            identical.append(rel)

    print(f"\n比較したファイル: {len(all_rel)}  一致: {len(identical)}  違いあり: {len(diffs)}")
    for rel in identical:
        print(f"  OK   {rel}")
    for d in diffs:
        print(f"  DIFF {d}")

    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
