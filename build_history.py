"""1校の歩みのページを作る（既定は武蔵丘）。out/site/history-<slug>.html に書き出す。

トーナメント（選手権・総体・新人戦・関東の東京都予選）とリーグ戦（地区トップリーグ・
NSリーグ・Tリーグ・ユニティリーグ）を1本の年表にまとめる。見た目は scout/site/ の
共通部品をそのまま使うので、スカウティングの各ページと並べても違和感が出ない。

読み取れた試合だけを使う。古い年ほど結果の載った版が残っておらず、2004〜2010年度は
勝敗の分からない試合が混ざる（ページ内にその数を出す）。

  uv run python build_history.py                      # 武蔵丘
  uv run python build_history.py --team 昭和第一
  uv run python build_history.py --team 武蔵丘 --out docs/history-musashigaoka.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from analyze_team import active_in, compute_elo, load_matches
from build_outputs import normalize
from leagues import for_school, load_all

ROOT = Path(__file__).parent

# ページの呼び名は build_site.py の PAGE_NAME と同じ語にする。
# ここがずれると、同じページが2つの名前で呼ばれる
PAGE_NAMES = [
    ("index", "2026年度の記録"),
    ("musashigaoka", "武蔵丘の記録"),
    ("history-musashigaoka", "武蔵丘の歩み"),
    ("showa-daiichi", "1回戦 昭和第一戦"),
    ("gakushuin", "2回戦 学習院戦"),
    ("joto", "ブロック決勝 城東戦"),
    ("seeds", "2次予選 都大会"),
    ("book", "都内全校データベース"),
]
SLUG = {"武蔵丘": "musashigaoka", "昭和第一": "showa-daiichi", "学習院": "gakushuin",
        "板橋有徳": "itabashi-yutoku", "城東": "joto", "東村山": "higashimurayama"}
CUP_ORDER = ["選手権", "総体", "新人戦", "関東"]
ROUND_RANK = {"1回戦": 1, "2回戦": 2, "3回戦": 3, "ブロック決勝": 4, "準々決勝": 5, "準決勝": 6, "決勝": 7}


def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def parse_score(s: str) -> tuple[int, int] | None:
    m = re.match(r"(\d+)\s*-\s*(\d+)", s or "")
    return (int(m[1]), int(m[2])) if m else None


def tier_of(stage: str) -> int:
    """一次（支部・地区）なら 1、都大会なら 2。

    総体の都大会は「一次トーナメント」「二次トーナメント」と呼ぶので、「一次」の字だけで
    1次の段階と決めてはいけない（2015・2021年度の総体の都大会進出を落としていた。2026-09-29）。
    """
    if "トーナメント" in stage or "二次" in stage or "都予選" in stage or "東京都" in stage:
        return 2
    return 1


def cup_games(rows: list[dict], me: str) -> list[dict]:
    """トーナメントの試合を、自チームから見た形にする。"""
    out = []
    for r in rows:
        home = r["チームA_正規化"] == me
        if not home and r["チームB_正規化"] != me:
            continue
        sc = parse_score(r["スコア"])
        gf = ga = None
        if sc:
            gf, ga = (sc[0], sc[1]) if home else (sc[1], sc[0])
        out.append({
            # 年度は出どころによって数と文字が混ざるので、ここで文字にそろえる
            "年度": str(r["年度"]), "大会": r["大会"], "段階": r["段階"], "ラウンド": r["ラウンド"],
            "相手": (r["チームB_正規化"] if home else r["チームA_正規化"]) or "（不明）",
            "結果": "" if gf is None else "○" if gf > ga else "●" if gf < ga else "△",
            "得点": gf, "失点": ga, "日付": r["日付"], "リーグ戦": False, "出どころ": "トーナメント表",
        })
    return out


def sort_key(g: dict) -> tuple:
    """1年度のなかの並び。トーナメントを先に、そのあとリーグ戦。"""
    if g["リーグ戦"]:
        return (9, g["大会"], g["段階"], g["日付"])
    cup = CUP_ORDER.index(g["大会"]) if g["大会"] in CUP_ORDER else 8
    return (cup, "", "", f'{-tier_of(g["段階"])}{ROUND_RANK.get(g["ラウンド"], 0):02}')


def furthest(games: list[dict]) -> str:
    """その年度でいちばん奥まで進んだところを言葉にする。

    東京の予選は一次（支部・地区）を勝ち抜くと二次（都大会）に進む。まず一次／二次の
    別で比べ、同じなら勝ち上がった回戦の深さで比べる。リーグ戦は勝ち上がりが無いので見ない。
    """
    best, top = "", (-1, -1)
    for g in games:
        if g["リーグ戦"]:
            continue
        t = tier_of(g["段階"])
        v = (t, ROUND_RANK.get(g["ラウンド"], 0))
        if v > top:
            # 「決勝」は地区の決勝か都の決勝かで意味がまるで違うので、段階を必ず添える
            stage = re.sub(r"^第\s*\d+\s*回\s*", "", g["段階"])
            top, best = v, " ".join(x for x in (g["大会"], stage, g["ラウンド"]) if x)
    return (best + "進出") if best else ""


def collect(games: list[dict]) -> dict:
    """年度ごと・大会ごとにまとめる。"""
    years: dict[str, dict] = defaultdict(lambda: {"games": [], "win": 0, "lose": 0, "draw": 0, "unknown": 0})
    series: dict[str, dict] = defaultdict(lambda: {"win": 0, "lose": 0, "draw": 0, "unknown": 0, "n": 0,
                                                   "league": False})
    opponents, beat, drew, lost = Counter(), Counter(), Counter(), Counter()
    KEY = {"○": "win", "●": "lose", "△": "draw", "": "unknown"}

    for g in games:
        y, s = years[g["年度"]], series[g["大会"]]
        k = KEY[g["結果"]]
        y[k] += 1
        s[k] += 1
        s["n"] += 1
        s["league"] = g["リーグ戦"]
        y["games"].append(g)
        opp = g["相手"]
        if opp and opp != "（不明）":
            opponents[opp] += 1
            (beat if k == "win" else lost if k == "lose" else drew if k == "draw" else Counter())[opp] += 1

    for y in years.values():
        y["games"].sort(key=sort_key)
    played = [g for g in games if g["得点"] is not None]
    return {
        "years": dict(sorted(years.items())), "series": dict(series), "n": len(games),
        "opponents": opponents, "beat": beat, "drew": drew, "lost": lost,
        "best_win": max(played, key=lambda g: (g["得点"] - g["失点"], g["得点"]), default=None),
        "worst": min(played, key=lambda g: (g["得点"] - g["失点"], -g["失点"]), default=None),
    }


# --- データから言えることだけを文章にする -----------------------------------

def highlights(c: dict, elo_hist: dict, me: str) -> list[tuple[str, str]]:
    """本文に置く短い解説。すべてこのページの表と図から確かめられる範囲に限る。"""
    out: list[tuple[str, str]] = []
    years = c["years"]

    # 都大会（二次予選）に届いた年
    top = {y: list(dict.fromkeys(g["大会"] for g in v["games"] if not g["リーグ戦"] and tier_of(g["段階"]) == 2))
           for y, v in years.items()}
    top = {y: s for y, s in top.items() if s}
    if top:
        out.append(("都大会に届いた年",
                    "支部・地区の予選を抜けて都大会に進んだのは "
                    + "・".join(f'{y}年度（{"・".join(s)}）' for y, s in top.items())
                    + f"の{len(top)}回。東京は1次の予選が支部・地区ごとのトーナメントで、"
                    "そこを抜けた学校だけが都大会（総体の1次・2次トーナメント、選手権の2次予選、関東大会の東京都予選）に進む。"))

    # 所属リーグの上がり下がり
    div: dict[str, str] = {}
    for y, v in years.items():
        for g in v["games"]:
            # 順位決定戦は所属していた部ではないので、移り変わりの材料にしない
            if g["リーグ戦"] and g["段階"] and "順位決定" not in g["段階"]:
                div.setdefault(y, f'{g["大会"]}{g["段階"]}')
    if len(div) >= 2:
        runs: list[tuple[str, str, str]] = []
        for y, d in div.items():
            if runs and runs[-1][2] == d:
                runs[-1] = (runs[-1][0], y, d)
            else:
                runs.append((y, y, d))
        line = " → ".join(f'{a}{"〜" + b if b != a else ""}年度 {d}' for a, b, d in runs)
        out.append(("所属リーグの移り変わり",
                    line + "。星取表が残っている年だけなので、間の年が抜けているところがある。"))

    # 強さの点数の山と谷
    if len(elo_hist) >= 3:
        hi = max(elo_hist.items(), key=lambda x: x[1])
        lo = min(elo_hist.items(), key=lambda x: x[1])
        last = sorted(elo_hist.items())[-1]
        out.append(("点数がいちばん高かった年",
                    f'{hi[0]}年度の {round(hi[1])}。いちばん低かったのは {lo[0]}年度の {round(lo[1])} で、'
                    f'その差は {round(hi[1] - lo[1])}。直近は {last[0]}年度の {round(last[1])}。'
                    f'この点数はトーナメントとリーグ戦（重みは半分）から計算している。'))

    # 相性
    good = [(n, c["beat"][n], c["lost"][n]) for n in c["opponents"]
            if c["opponents"][n] >= 3 and c["beat"][n] > c["lost"][n]]
    bad = [(n, c["beat"][n], c["lost"][n]) for n in c["opponents"]
           if c["opponents"][n] >= 3 and c["lost"][n] > c["beat"][n]]
    good.sort(key=lambda x: (-(x[1] - x[2]), -x[1]))
    bad.sort(key=lambda x: (x[1] - x[2], -x[2]))
    if good or bad:
        parts = []
        if good:
            parts.append("勝ち越しているのは " + "、".join(f"{n}（{w}勝{lo}敗）" for n, w, lo in good[:3]))
        if bad:
            parts.append("負け越しているのは " + "、".join(f"{n}（{w}勝{lo}敗）" for n, w, lo in bad[:3]))
        out.append(("3回以上あたった相手との分", "。".join(parts) + "。"))

    # 前半と後半の勝率
    ys = sorted(years)
    if len(ys) >= 8:
        def rate(keys: list[str]) -> tuple[int, int, str]:
            w = sum(years[y]["win"] for y in keys)
            n = sum(years[y]["win"] + years[y]["draw"] + years[y]["lose"] for y in keys)
            return w, n, f"{w / n * 100:.0f}%" if n else "—"
        aw, an, ap = rate(ys[:5])
        bw, bn, bp = rate(ys[-5:])
        # 記録の無い年があるので、年度は範囲ではなく並べて書く
        out.append(("記録のある最初の5年度と直近の5年度",
                    f'{"・".join(ys[:5])}年度は {an} 試合で {aw} 勝（勝率 {ap}）、'
                    f'{"・".join(ys[-5:])}年度は {bn} 試合で {bw} 勝（勝率 {bp}）。'
                    f'ただし古い年はスコアの読めない試合があり、母数がそろっていない。'))
    return out


# --- 見た目 ---------------------------------------------------------------

EXTRA_CSS = """
/* 歩みのページだけで使う部品 */
.yr > summary { list-style: none; cursor: pointer; display: flex; align-items: baseline; justify-content: space-between; gap: var(--s3); flex-wrap: wrap; }
.yr > summary::-webkit-details-marker { display: none; }
.yr > summary .y { font-family: var(--f-num); font-weight: 700; font-size: var(--t2); line-height: 1; }
.yr > summary .r { display: flex; align-items: center; gap: var(--s3); flex-wrap: wrap; color: var(--ink-2); font-size: var(--t-1); }
.yr > summary:hover .y, .yr[open] > summary .y { color: var(--us); }
.bar { display: grid; grid-auto-flow: column; gap: 2px; width: 132px; height: 9px; }
.bar i { border-radius: 2px; }
.bar i.w { background: var(--us); }
.bar i.d { background: var(--rule-strong); }
.bar i.l { background: var(--sunk); box-shadow: inset 0 0 0 1px var(--rule); }
.bar i.u { background: repeating-linear-gradient(45deg, var(--rule) 0 3px, transparent 3px 6px); }
.legend { display: flex; gap: var(--s3); flex-wrap: wrap; align-items: center; color: var(--muted); font-size: var(--t-1); }
.legend b { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
tr.lg td:first-child { position: relative; padding-left: var(--s4); }
tr.lg td:first-child::before { content: ""; position: absolute; left: var(--s3); top: 50%; width: 5px; height: 5px; border-radius: 50%; background: var(--them); transform: translateY(-50%); }
.hist-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--s4); align-items: start; }
.hist-grid .card p { margin: 0 0 var(--s3); }
.points { display: grid; gap: var(--s4); }
.points h3 { font-size: var(--t0); margin: 0 0 var(--s1); }
.points p { margin: 0; color: var(--ink-2); }
svg.chart .elo { fill: none; stroke: var(--us); stroke-width: 2; stroke-linejoin: round; }
svg.chart .dot { fill: var(--us); stroke: var(--surface); stroke-width: 2; }
svg.chart .mid { stroke: var(--rule-strong); stroke-width: 1; stroke-dasharray: 4 4; }
"""


def bar(y: dict) -> str:
    """勝ち・分け・負け・結果不明の帯。幅が試合数の比になる。"""
    segs = [("w", y["win"]), ("d", y["draw"]), ("l", y["lose"]), ("u", y["unknown"])]
    cols = " ".join(f"{n}fr" for _, n in segs if n)
    cells = "".join(f'<i class="{c}"></i>' for c, n in segs if n)
    label = f'{y["win"]}勝 {y["draw"]}分 {y["lose"]}敗' + (f'・結果不明 {y["unknown"]}' if y["unknown"] else "")
    return f'<span class="bar" style="grid-template-columns:{cols}" role="img" aria-label="{e(label)}">{cells}</span>'


def elo_chart(hist: dict) -> str:
    pts = sorted(hist.items())
    if len(pts) < 2:
        return '<p class="muted small">点数の履歴がありません。</p>'
    w, h, ml, mr, mt, mb = 880, 230, 48, 18, 16, 34
    vals = [v for _, v in pts] + [1500]
    lo, hi = min(vals) - 45, max(vals) + 45

    def px(i: int) -> float:
        return ml + i / (len(pts) - 1) * (w - ml - mr)

    def py(v: float) -> float:
        return mt + (1 - (v - lo) / (hi - lo)) * (h - mt - mb)

    g = ['<g class="grid">']
    for k in range(4):
        y = py(lo + (hi - lo) * k / 3)
        g.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}"/>')
    g.append("</g>")
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        g.append(f'<text x="{ml - 8}" y="{py(v) + 4:.1f}" text-anchor="end">{round(v)}</text>')
    g.append(f'<line class="mid" x1="{ml}" x2="{w - mr}" y1="{py(1500):.1f}" y2="{py(1500):.1f}"/>')
    g.append(f'<text x="{w - mr}" y="{py(1500) - 7:.1f}" text-anchor="end">東京の平均 1500</text>')
    d = " ".join(f'{"L" if i else "M"}{px(i):.1f} {py(v):.1f}' for i, (_, v) in enumerate(pts))
    g.append(f'<path class="elo" d="{d}"/>')
    for i, (yr, v) in enumerate(pts):
        g.append(f'<circle class="dot" cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.5">'
                 f'<title>{e(yr)}年度 {round(v)}</title></circle>')
    step = max(1, round(len(pts) / 8))
    for i, (yr, _) in enumerate(pts):
        if i % step == 0 or i == len(pts) - 1:
            g.append(f'<text x="{px(i):.1f}" y="{h - 8}" text-anchor="middle">{e(yr)}</text>')
    lab = f"{pts[0][0]}年度から{pts[-1][0]}年度までの強さの点数の推移"
    return f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{e(lab)}">{"".join(g)}</svg>'


def res_cell(g: dict) -> str:
    if g["結果"] == "○":
        return '<span class="res w"><b class="g" aria-hidden="true">○</b>勝ち</span>'
    if g["結果"] == "●":
        return '<span class="res l"><b class="g" aria-hidden="true">×</b>負け</span>'
    if g["結果"] == "△":
        return '<span class="res"><b class="g" aria-hidden="true">△</b>引き分け</span>'
    return '<span class="muted small">結果なし</span>'


def stage_text(g: dict) -> str:
    if g["リーグ戦"]:
        return g["段階"] or "リーグ戦"
    stage = re.sub(r"^第\s*\d+\s*回\s*", "", g["段階"])
    return " ".join(x for x in (stage, g["ラウンド"]) if x)


def year_block(y: dict) -> str:
    rows = "".join(
        f'<tr{" class=\"lg\"" if g["リーグ戦"] else ""}><td>{e(g["大会"])}</td>'
        f'<td>{e(stage_text(g))}</td><td>{e(g["相手"])}</td>'
        f'<td class="n">{"—" if g["得点"] is None else f"{g['得点']}-{g['失点']}"}</td>'
        f'<td>{res_cell(g)}</td></tr>'
        for g in y["games"])
    chip = f'<span class="chip">{e(y["best"])}</span>' if y["best"] else ""
    return f"""<details class="card yr"{' open' if y["open"] else ''}>
<summary><span class="y">{e(y["year"])}<span class="small muted"> 年度</span></span>
<span class="r">{bar(y)}<span class="num">{y["win"]}勝 {y["draw"]}分 {y["lose"]}敗</span>{chip}</span></summary>
<div class="tbl"><table><thead><tr><th>大会</th><th>段階</th><th>相手</th><th class="n">スコア</th><th>結果</th></tr></thead>
<tbody>{rows}</tbody></table></div></details>"""


def win_pct(v: dict) -> str:
    n = v["win"] + v["draw"] + v["lose"]
    return "—" if not n else f'{v["win"] / n * 100:.0f}%'


def big_game(g: dict | None, lab: str) -> str:
    if not g:
        return ""
    return (f'<p><span class="eyebrow">{e(lab)}</span><br>'
            f'<b class="num">{g["得点"]}-{g["失点"]}</b> {e(g["相手"])} '
            f'<span class="muted small">{e(g["年度"])}年度 {e(g["大会"])} {e(stage_text(g))}</span></p>')


def render(d: dict, css: str, shell: str) -> str:
    ys = [y["year"] for y in d["years"]]
    played = d["win"] + d["draw"] + d["lose"]
    pct = f'{d["win"] / played * 100:.0f}%' if played else "—"
    diff = d["gf"] - d["ga"]

    kpis = [
        ("公式戦", f'{d["n"]}<small>試合</small>',
         f'トーナメント {d["cup"]}・リーグ戦 {d["league"]}'),
        ("勝敗", f'<span class="us">{d["win"]}</span><small>勝</small> {d["draw"]}<small>分</small> {d["lose"]}<small>敗</small>',
         f'勝率 {pct}' + (f'・結果の分からない試合が {d["unknown"]}' if d["unknown"] else "")),
        ("得失点", f'{d["gf"]}<small> - {d["ga"]}</small>', f'差 {"+" if diff > 0 else ""}{diff}'),
        ("いまの強さの点数", f'{round(d["elo"])}' if d["elo"] else "—",
         f'東京 {d["teams"]} 校のうち {d["place"]} 位' if d["place"] else ""),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="k">{e(k)}</span><span class="v num">{v}</span><span class="note">{e(n)}</span></div>'
        for k, v, n in kpis)

    def series_order(kv: tuple[str, dict]) -> tuple:
        return (kv[1]["league"], CUP_ORDER.index(kv[0]) if kv[0] in CUP_ORDER else 8, -kv[1]["n"])

    srows = "".join(
        f'<tr{" class=\"lg\"" if v["league"] else ""}><td>{e(k)}</td><td class="n">{v["n"]}</td>'
        f'<td class="n">{v["win"]}</td><td class="n">{v["draw"]}</td><td class="n">{v["lose"]}</td>'
        f'<td class="n">{win_pct(v)}</td></tr>'
        for k, v in sorted(d["series"].items(), key=series_order))

    orows = "".join(
        f'<tr><td>{e(n)}</td><td class="n">{c}</td><td class="n">{d["beat"].get(n, 0)}</td>'
        f'<td class="n">{d["drew"].get(n, 0)}</td><td class="n">{d["lost"].get(n, 0)}</td>'
        f'<td class="n">{c - d["beat"].get(n, 0) - d["drew"].get(n, 0) - d["lost"].get(n, 0) or ""}</td></tr>'
        for n, c in d["opponents"])

    points = "".join(f'<div><h3>{e(t)}</h3><p>{e(b)}</p></div>' for t, b in d["points"])

    nav_html = "".join(
        f'<a href="{e(href)}"{d["linkTarget"]}>{e(name)}</a>' if href else f"<b>{e(name)}</b>"
        for name, href in d["siteNav"])
    body = f"""<nav class="hist-nav" aria-label="ページ">{nav_html}</nav>

<header class="masthead">
  <span class="eyebrow">History {ys[0]}–{ys[-1]}</span>
  <div class="title-row"><h1><span class="us">{e(d["team"])}</span>の歩み</h1></div>
  <p class="lead">{ys[0]}年度から{ys[-1]}年度までの公式戦 {d["n"]} 試合。選手権・総体・新人戦・関東大会の
  東京都予選（トーナメント {d["cup"]} 試合）と、地区トップリーグ・NSリーグなどのリーグ戦（{d["league"]} 試合）を
  1本の年表にまとめました。</p>
</header>

<div class="kpis">{kpi_html}</div>

<section class="stack">
  <div class="sec-head"><h2>歩みの要点</h2><p>このページの表と図から言えること</p></div>
  <div class="card points">{points}</div>
</section>

<section class="stack">
  <div class="sec-head"><h2>強さの点数の移り変わり</h2><p>年度末の時点・{min(d["eloHistory"], default=ys[0])}年度から</p></div>
  <div class="card">{elo_chart(d["eloHistory"])}
    <p class="small muted">勝てば上がり、負ければ下がる点数（Elo）。1500 が東京全体の平均で、格上に勝つほど大きく上がります。
    年度をまたいでも点数は戻さず、そのまま次の代へ引き継ぎます。前の代が積み上げた点数が出発点になる、という見方です。
    トーナメントとリーグ戦の両方を使い、リーグ戦は動く幅を半分にしています（一発勝負ではないため）。</p></div>
</section>

<section class="stack">
  <div class="sec-head"><h2>大会・リーグ別の成績</h2><p>{ys[0]}年度からの通算</p></div>
  <div class="hist-grid">
    <div class="tbl"><table><thead><tr><th>大会</th><th class="n">試合</th><th class="n">勝</th><th class="n">分</th><th class="n">敗</th><th class="n">勝率</th></tr></thead>
    <tbody>{srows}</tbody></table></div>
    <div class="card">{big_game(d["best_win"], "いちばん大きな勝ち")}{big_game(d["worst"], "いちばん大きな負け")}
      <p class="small muted">得失点差がいちばん開いた試合。スコアの読み取れた {played} 試合から選んでいます。</p></div>
  </div>
</section>

<section class="stack">
  <div class="sec-head"><h2>年度ごとの記録</h2><p>年度を開くと全試合が出ます</p></div>
  <p class="legend"><span><b style="background:var(--us)"></b>勝ち</span><span><b style="background:var(--rule-strong)"></b>引き分け</span>
  <span><b style="background:var(--sunk);box-shadow:inset 0 0 0 1px var(--rule)"></b>負け</span><span><b style="background:var(--rule)"></b>結果なし</span>
  <span style="margin-left:auto">左に●が付く行はリーグ戦</span></p>
  {"".join(year_block(y) for y in reversed(d["years"]))}
</section>

<section class="stack">
  <div class="sec-head"><h2>よく当たる相手</h2><p>対戦の多い順に {len(d["opponents"])} 校</p></div>
  <div class="tbl"><table><thead><tr><th>相手</th><th class="n">対戦</th><th class="n">勝</th><th class="n">分</th><th class="n">敗</th><th class="n">結果なし</th></tr></thead>
  <tbody>{orows}</tbody></table></div>
</section>

<section class="prose">
  <h2>このページの元データ</h2>
  <p class="small muted">トーナメントは東京都高体連サッカー専門部の公式トーナメント表（現行サイトとインターネットアーカイブ）、
  リーグ戦は早大学院サッカー部が公開している星取表と goalnote の日程・結果から読み取りました。
  どちらも古い年ほど残っている資料が少なく、{ys[0]}年度から2010年度あたりのトーナメントは対戦相手だけ分かって
  スコアが読めない試合が混ざります（このページでは {d["unknown"]} 試合）。リーグ戦は星取表が残っている年だけで、
  {d["league_years"]} 年度ぶんです。勝率と得失点は、スコアの読み取れた試合だけで計算しています。
  下部チーム（B・C）の試合は含めていません。</p>
</section>"""

    return (shell.replace("__TITLE__", f'{d["team"]}の歩み｜都立武蔵丘高校サッカー部 年鑑')
            .replace("/*__CSS__*/", css + EXTRA_CSS)
            .replace('<main class="page" id="app"></main>', f'<main class="page" id="app">{body}</main>')
            .replace("const D = /*__DATA__*/null;", "")
            .replace("/*__JS__*/", ""))


def payload_for(team: str = "武蔵丘") -> dict | None:
    """歩みのページに載せる数字をまとめる。build_site.py の「全年度の通算」もこれを使う。"""
    me = normalize(team)

    rows = load_matches()
    elo, hist, _ = compute_elo(rows)
    cups = cup_games(rows, me)
    lg = for_school(load_all(), me)
    if not cups and not lg:
        return None

    c = collect(cups + lg)
    tot = {k: sum(y[k] for y in c["years"].values()) for k in ("win", "lose", "draw", "unknown")}
    act = active_in(rows, max(r["年度"] for r in rows))  # 順位の母数は今年度に大会へ出た学校（analyze_team と同じ）
    ranked = sorted(((k, v) for k, v in elo.items() if k in act), key=lambda x: -x[1])
    latest = max(c["years"])
    elo_hist = hist.get(me, {})

    payload = {
        "team": team, "n": c["n"], "cup": len(cups), "league": len(lg),
        "league_years": len({g["年度"] for g in lg}), **tot,
        "gf": sum(g["得点"] or 0 for y in c["years"].values() for g in y["games"]),
        "ga": sum(g["失点"] or 0 for y in c["years"].values() for g in y["games"]),
        "elo": elo.get(me), "teams": len(ranked),
        "place": next((i + 1 for i, (k, _) in enumerate(ranked) if k == me), None),
        "eloHistory": elo_hist,
        "years": [{"year": y, **{k: v[k] for k in ("win", "lose", "draw", "unknown")},
                   "best": furthest(v["games"]), "games": v["games"], "open": y == latest}
                  for y, v in c["years"].items()],
        "series": c["series"], "opponents": c["opponents"].most_common(24),
        "beat": c["beat"], "drew": c["drew"], "lost": c["lost"],
        "best_win": c["best_win"], "worst": c["worst"],
        "points": highlights(c, elo_hist, me),
    }

    return payload


def main() -> int:
    """数字だけを out/scout/history_<slug>.json に書く。ページは build_site.py が
    ほかのページと同じ形（左のツリー・章番号つき）で書き出す（2026-09-29 に移した）。"""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", default="武蔵丘")
    args = ap.parse_args()
    payload = payload_for(args.team)
    if payload is None:
        print(f"{args.team} の試合が見つかりません")
        return 1
    slug = SLUG.get(normalize(args.team), re.sub(r"\W+", "-", args.team))
    out = ROOT / f"out/scout/history_{slug}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    print(f'{args.team}: {payload["n"]} 試合（トーナメント {payload["cup"]} / リーグ {payload["league"]}） → {out.name}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
