"""2次予選のトーナメント表 PDF に、勝敗予想の勝ち上がりを赤線で描き込む。

公式PDF（pdfs/sen26_2j.pdf）の線の座標をそのまま使い、
「強さの点数で見込みの高いほうが勝つ」とたどった経路を赤で太く上書きする。
出力は PDF（そのまま配布用）と、ページを切り出した PNG（サイトに載せる用）。

出力:
  out/site/assets/sen26_2j_pred.pdf
  out/site/assets/sen26_2j_pred_b{1..4}.png   ブロックごとの切り出し
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from analyze_team import compute_elo, load_matches, normalize, win_prob

ROOT = Path(__file__).parent
BASE = 1500.0
RED = (0.85, 0.08, 0.12)


def winner_of(a: str, b: str, elo: dict) -> str:
    """見込みの高いほうを勝者とする。同点なら点数の高いほう。"""
    pa = win_prob(elo.get(a, BASE), elo.get(b, BASE))
    return a if pa >= 0.5 else b


def main() -> int:
    rows = load_matches()
    elo, _, _ = compute_elo(rows)
    data = json.loads((ROOT / "out/json/sen26_2j.json").read_text(encoding="utf-8"))
    page0 = data["pages"][0]
    ms = {m["id"]: m for m in page0["matches"]}

    # 各試合の予想勝者を下から決める
    pred: dict[int, str] = {}

    def resolve(mid: int) -> str:
        if mid in pred:
            return pred[mid]
        m = ms[mid]
        sides = []
        for s in ("slot1", "slot2"):
            v = m.get(s) or {}
            if v.get("leaf"):
                sides.append(normalize(v["leaf"]))
            elif v.get("from") in ms:
                sides.append(resolve(v["from"]))
        if not sides:
            pred[mid] = ""
        elif len(sides) == 1:
            pred[mid] = sides[0]
        else:
            pred[mid] = winner_of(sides[0], sides[1], elo)
        return pred[mid]

    roots = sorted([m for m in ms.values() if m.get("parent") is None], key=lambda m: m["id"])
    for r in roots:
        resolve(r["id"])

    # 葉（チーム名）の位置。縦線をチーム名のところまで伸ばすのに使う
    leaf_pt = {(lf["match"], lf["slot"]): lf["point"] for lf in page0.get("leaves", [])}

    doc = pymupdf.open(ROOT / "pdfs/sen26_2j.pdf")
    page = doc[0]
    drawn = 0
    for m in page0["matches"]:
        w = pred.get(m["id"])
        if not w:
            continue
        o, c, a0, a1 = m["bar"]
        # 勝ち上がる側の枝（j から、勝者が来た側の端まで）を赤でなぞる
        sides = []
        for s in ("slot1", "slot2"):
            v = m.get(s) or {}
            if v.get("leaf"):
                sides.append(normalize(v["leaf"]))
            elif v.get("from") in ms:
                sides.append(pred.get(v["from"], ""))
            else:
                sides.append("")
        if w not in sides:
            continue
        idx = sides.index(w)
        end = a0 if idx == 0 else a1
        j = m["j"]
        # 横棒（試合の線）：合流点から、勝者が来た側の端まで
        p1 = pymupdf.Point(j, c) if o == "h" else pymupdf.Point(c, j)
        p2 = pymupdf.Point(end, c) if o == "h" else pymupdf.Point(c, end)
        page.draw_line(p1, p2, color=RED, width=1.6, overlay=True)
        drawn += 1

        # 縦線（勝ち上がりの線）：勝者が来た側の端から、下の試合の横棒／チーム名まで下ろす。
        # ここを描かないと赤が横棒だけになり、どこから上がってきたのかが読めない
        src = m.get("slot1" if idx == 0 else "slot2") or {}
        far = None
        if src.get("from") in ms:
            child = ms[src["from"]]
            far = child["bar"][1]  # 子の横棒の位置（BT なので下側）
        else:
            pt = leaf_pt.get((m["id"], idx + 1))
            if pt:
                far = pt[1] if o == "h" else pt[0]
        if far is not None:
            q1 = pymupdf.Point(end, c) if o == "h" else pymupdf.Point(c, end)
            q2 = pymupdf.Point(end, far) if o == "h" else pymupdf.Point(far, end)
            page.draw_line(q1, q2, color=RED, width=1.6, overlay=True)
            drawn += 1

    out_dir = ROOT / "out/site/assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_out = out_dir / "sen26_2j_pred.pdf"
    doc.save(pdf_out)
    pix = page.get_pixmap(dpi=200)
    png_out = out_dir / "sen26_2j_pred.png"
    pix.save(png_out)
    print(f"赤線 {drawn}本  {pdf_out.name} ({pdf_out.stat().st_size // 1024} KB)  {png_out.name} ({png_out.stat().st_size // 1024} KB)")
    print("予想の4ブロック優勝:", "、".join(pred[r["id"]] for r in roots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
