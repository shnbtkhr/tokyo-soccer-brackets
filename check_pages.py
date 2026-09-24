"""公開する前に、出来上がった HTML を全ページまとめて点検する。

入口ページだけ見て出すと、ほかのページが壊れていても気づけない。ブラウザを起こさずに
済む範囲――埋め込んだデータの欠け・リンク切れ・古い数字――をここで潰し、
ブラウザでしか分からないこと（コンソールのエラー・描画の崩れ）は Playwright で別に見る。

  uv run python check_pages.py            # out/site を見る
  uv run python check_pages.py docs       # 公開フォルダを見る

見るもの:
  - ページの大きさと、埋め込んだデータ（const D）が読めるか
  - データの中の null・NaN・"undefined"（表示にそのまま出てしまう）
  - ページ内リンクの行き先がフォルダに在るか
  - ナビに挙げた行き先が全部そろっているか
  - 本文に直書きされた試合数が、いまのデータと合っているか
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = re.compile(r"const D = (\{.*?\});\n", re.S)
# 「公式戦◯◯試合」と直書きした収録数。データを足すたびに古くなるので突き合わせる
# （検証の結果として書いた「大会1,314試合で80.3%」のような数字は動かないので見ない）
HARDCODED = re.compile(r"公式戦[^。]{0,14}?([0-9][0-9,]{2,})\s*試合")


def find_bad(node, path: str = "D", out: list | None = None) -> list[str]:
    """表示に出ると困る値（null・NaN・"undefined"）を探す。"""
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            find_bad(v, f"{path}.{k}", out)
    elif isinstance(node, list):
        for i, v in enumerate(node[:200]):
            find_bad(v, f"{path}[{i}]", out)
    elif node is None:
        out.append(path)
    elif isinstance(node, float) and node != node:
        out.append(path + " (NaN)")
    elif isinstance(node, str) and node.strip() in ("undefined", "NaN", "[object Object]"):
        out.append(f"{path} = {node!r}")
    return out


def check(root: Path) -> int:
    files = sorted(root.glob("*.html"))
    if not files:
        print(f"{root} に HTML がありません")
        return 1
    ng = 0
    for f in files:
        html = f.read_text(encoding="utf-8")
        problems: list[str] = []

        m = DATA.search(html)
        data = None
        if m:
            try:
                data = json.loads(m[1])
            except json.JSONDecodeError as e:
                problems.append(f"埋め込みデータが読めない: {e}")
        # 歩みのページのようにサーバ側で組み立てるページには const D が無い（それでよい）

        notes: list[str] = []
        if data is not None:
            # null は「まだ決まっていない」「該当なし」の意味で使う場所があるので、ここでは
            # 数えるだけにして、表示に出てしまったかどうかは下の本文検査のほうで見る
            top = [b for b in find_bad(data) if b.count(".") <= 2]
            if top:
                notes.append(f"データが空の項目 {len(top)} 件: " + ", ".join(top[:4]))

        for tag in ("undefined", "NaN", "[object Object]"):
            # 本文に出てしまっているもの（スクリプトの中は数えない）
            body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
            n = body.count(tag)
            if n:
                problems.append(f"本文に {tag} が {n} 回")

        links = {h.split("#")[0] for h in re.findall(r'href="([^"]+)"', html)
                 if not h.startswith(("http", "#", "mailto:", "data:"))}
        missing = sorted(h for h in links if h and not (root / h).exists())
        if missing:
            problems.append("リンク切れ " + ", ".join(missing))

        if data is not None and "totalMatches" in data:
            for num in set(HARDCODED.findall(html)):
                v = int(num.replace(",", ""))
                if v not in (data.get("totalMatches"), data.get("ratedMatches")) and v > 999:
                    problems.append(f"本文の「{num} 試合」がデータの "
                                    f'{data.get("totalMatches")} / {data.get("ratedMatches")} と合わない')

        size = f.stat().st_size // 1024
        if size < 8:
            problems.append(f"ページが小さすぎる {size} KB")

        ng += bool(problems)
        lines = [f"  NG: {t}" for t in problems] + [f"  – {t}" for t in notes]
        print(f'{"NG" if problems else "ok"}  {f.name:28} {size:5} KB'
              + ("\n    " + "\n    ".join(lines) if lines else ""))

    print(f"\n{len(files)} ページ中 {ng} ページで指摘")
    print("※ コンソールのエラーと描画の崩れは、この点検では分からない。"
          "out/site を簡易サーバで配り、Playwright で全ページ開いて確かめる")
    return 1 if ng else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", nargs="?", default="out/site")
    args = ap.parse_args()
    return check(ROOT / args.dir)


if __name__ == "__main__":
    sys.exit(main())
