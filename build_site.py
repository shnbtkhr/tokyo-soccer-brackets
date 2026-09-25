"""武蔵丘スカウトのサイト（7ページ）を書き出す。

- index           … ブロック全体（入口）
- musashigaoka    … 武蔵丘の自己分析
- showa-daiichi   … 1回戦の相手
- gakushuin / itabashi-yutoku … 2回戦の相手候補
- joto / higashimurayama      … ブロック決勝の相手候補
- seeds           … 2次予選から出てくる強豪（1次予選の免除校。build_seeds.py の出力）

入力は build_scout_page.build_data() と同じ（analyze_team.py・fetch_leagues.py の出力と scout/sen2026_block10.json）。
見た目と部品は scout/site/（page.html・site.css・site.js）に1か所だけ置き、各ページに埋め込む。

--links local    … ページどうしを相対リンクでつなぐ（手元で開く用。out/site/）
--links artifact … scout/site_urls.json の公開URLでつなぐ（claude.ai 上で開く用。out/site_artifact/）
"""

from __future__ import annotations

import argparse
import base64
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_team import BASE, CARRY, K, LEAGUE_WEIGHT, win_prob
from build_scout_page import build_data

ROOT = Path(__file__).parent
SLUG = {"武蔵丘": "musashigaoka", "昭和第一": "showa-daiichi", "学習院": "gakushuin", "板橋有徳": "itabashi-yutoku", "城東": "joto", "東村山": "higashimurayama"}
# ページの呼び名はここだけで決める。タブ・左パネル・パンくずで同じ語を使うため、
# ばらばらに書くと「武蔵丘 の歩み」「2004年からの歩み」のように同じページが別名になる
SITE_NAME = "都立武蔵丘高校サッカー部 年鑑"
PAGE_NAME = {
    "index": "2026年度の記録",
    "musashigaoka": "武蔵丘の記録",
    "showa-daiichi": "1回戦 昭和第一戦",
    "gakushuin": "2回戦 学習院戦",
    "joto": "ブロック決勝 城東戦",
    "seeds": "2次予選 都大会",
    "book": "対戦校名鑑",
    "history-musashigaoka": "武蔵丘の歩み",
}
TITLE = {k: f"{v}｜{SITE_NAME}" for k, v in PAGE_NAME.items()}


def band_of(g: dict) -> str:
    gap = (g.get("oppElo") or 1500) - (g.get("myElo") or 1500)
    return "格上" if gap > 50 else "格下" if gap < -50 else "同格"


def wins(gs: list) -> tuple[int, int, int, int]:
    return tuple(sum(g["res"] == r for g in gs) for r in ("勝", "PK勝", "PK負", "負"))


def league_line(t: dict) -> str:
    for lg in t.get("leagues", []):
        row = next((r for r in lg["table"] if r["team"] == lg["teamName"]), None)
        played = [g for g in lg["games"] if g["res"]]
        c = Counter(g["res"] for g in played)
        rec = f"{c['勝']}勝{c['分']}分{c['負']}敗"
        return f"今季 {lg['league']} " + (f"{row['rank']}位/{len(lg['table'])}・" if row else "") + rec
    return "今季のリーグ戦は未確認"


def team_points(t: dict, me_t: dict, me_games: list, br: dict) -> list[str]:
    """相手校の「スカウティングの要点」を数字から書く。"""
    pts = []
    gap = t["elo"] - me_t["elo"]
    band = "格上" if gap > 50 else "格下" if gap < -50 else "同格"
    w, pw, pl, l = wins([g for g in me_games if band_of(g) == band])
    pts.append(f"強さの点数は武蔵丘より<b>{gap:+d}</b>で、<b>{band}</b>にあたる。武蔵丘は5年間、{band}の相手に <b>{w}勝 {pw}PK勝 {pl}PK負 {l}敗</b>。")
    for lg in t.get("leagues", [])[:1]:
        row = next((r for r in lg["table"] if r["team"] == lg["teamName"]), None)
        played = [g for g in lg["games"] if g["res"]]
        c = Counter(g["res"] for g in played)
        gf, ga = sum(g["gf"] for g in played), sum(g["ga"] for g in played)
        pos = f"{row['rank']}位（{len(lg['table'])}チーム中）" if row else ""
        pts.append(f"今季の{lg['league']}は<b>{pos}</b>、{len(played)}試合 {c['勝']}勝{c['分']}分{c['負']}敗・得点{gf} 失点{ga}。")
    if not t.get("leagues"):
        pts.append("今季のリーグ戦の結果は見つかっていない。調子は大会の結果から判断するしかない。")
    S = t["summary"]
    pts.append(f"過去5年の公式戦は1試合平均 <b>得点{S['gfPer']}・失点{S['gaPer']}</b>。無得点の試合が{S['scoreless']}/{S['n']}、無失点が{S['cleanSheets']}/{S['n']}。")
    if S["pkw"] + S["pkl"]:
        pts.append(f"PK戦は{S['pkw']}勝{S['pkl']}敗。武蔵丘は{me_t['summary']['pkw']}勝{me_t['summary']['pkl']}敗。")
    st26 = [st for st in t["stages"] if st["year"] == 2026]
    if st26:
        pts.append("2026年度の公式戦: " + "／".join(f"{st['series']} {st['stage']}は{st['reach']}（{st['path']}）" for st in st26) + "。")
    return pts


def self_insights(me_t: dict, block: dict, opp_of_round: dict) -> tuple[list, list, str]:
    gs = me_t["games"]
    S = me_t["summary"]
    bands = []
    for b in ("格上", "同格", "格下"):
        sub = [g for g in gs if band_of(g) == b]
        w, pw, pl, l = wins(sub)
        bands.append({"band": b, "n": len(sub), "w": w, "pkw": pw, "pkl": pl, "l": l})
    up = bands[0]
    even = bands[1]
    down = bands[2]
    losses = [g for g in gs if g["res"] in ("負", "PK負")]
    scoreless_losses = sum(g["gf"] == 0 for g in losses)
    close = sum(abs(g["gf"] - g["ga"]) <= 1 for g in gs)
    sr = me_t["bySeries"]
    strong = [k for k, v in opp_of_round.items() if v - me_t["elo"] > 50]
    weak = [k for k, v in opp_of_round.items() if me_t["elo"] - v > 50]
    ins = [
        {"fig": f"{up['w'] + up['pkw']}勝", "head": "格上の相手には、5年間で勝てていない",
         "body": f"差が50点を超える格上とは{up['n']}試合で{up['w']}勝{up['pkw']}PK勝{up['pkl']}PK負{up['l']}敗。" + (f"この山では{'・'.join(strong)}が格上にあたる。" if strong else "")},
        {"fig": f"{even['w'] + even['pkw']}/{even['n']}", "head": "同格の相手には、ほぼ互角以上",
         "body": f"同格とは{even['n']}試合で{even['w']}勝{even['pkw']}PK勝{even['pkl']}PK負{even['l']}敗。格下には{down['w']}勝{down['pkw']}PK勝{down['pkl']}PK負{down['l']}敗と取りこぼしが少ない。" + (f"この山では{'・'.join(weak)}が格下にあたる。" if weak else "")},
        {"fig": f"{S['pkw']}勝{S['pkl']}敗", "head": "PK戦に強い", "body": f"PK戦は{S['pkw'] + S['pkl']}試合で{S['pkw']}勝{S['pkl']}敗。同点で終盤を迎えても、PK戦に持ち込めば分がある。"},
        {"fig": f"{S['scoreless']}/{S['n']}", "head": f"無得点で終わる試合が{round(S['scoreless'] / S['n'] * 100)}%ある", "body": f"{S['n']}試合のうち{S['scoreless']}試合が無得点。負けた{len(losses)}試合のうち{scoreless_losses}試合は無得点で、点が取れない日に負けている。"},
        {"fig": f"{close}", "head": "1点差以内の接戦が多い", "body": f"1点差以内（PK戦を含む）で終わった試合が{close}/{S['n']}。先制点と終盤の守り方が勝敗を分けやすい。"},
        {"fig": f"{sr['選手権']['gfPer']} / {sr['選手権']['gaPer']}", "head": "選手権は数字が良い",
         "body": f"1試合平均の得点／失点は、選手権 {sr['選手権']['gfPer']}／{sr['選手権']['gaPer']}、総体 {sr['総体']['gfPer']}／{sr['総体']['gaPer']}、新人戦 {sr['新人戦']['gfPer']}／{sr['新人戦']['gaPer']}。秋の選手権で失点が一番少ない。"},
    ]
    note = "試合の時点の強さの点数で分けています。2022年度の最初の試合は、どの学校も1500から数え始めたため、この年の格の判定は甘めです。"
    return ins, bands, note


def elo_explainer(T: dict, me: str, r1: str, opps: list) -> dict:
    """入口ページの「強さの点数のしくみ」に載せる値。数値は analyze_team.py の設定から取る（説明と計算がずれないように）。"""
    me_e, op_e = T[me]["elo"], T[r1]["elo"]
    p = win_prob(me_e, op_e)

    def case(label: str, res: float, gf: int, ga: int) -> dict:
        margin = abs(gf - ga)
        mult = 1.0 if margin <= 1 else 1.5 if margin == 2 else (11 + margin) / 8
        d = round(K * mult * (res - p))
        return {"label": label, "delta": d, "me": me_e + d, "opp": op_e - d}

    return {
        "base": int(BASE), "k": int(K), "carry": CARRY, "leagueWeight": LEAGUE_WEIGHT, "band": 50,
        "example": {"me": T[me]["display"], "opp": T[r1]["display"], "meElo": me_e, "oppElo": op_e, "diff": me_e - op_e, "p": round(p, 3),
                    "cases": [case("2-0 勝ち", 1, 2, 0), case("1-0 勝ち", 1, 1, 0), case("PK戦", 0.5, 1, 1), case("0-1 負け", 0, 0, 1), case("0-3 負け", 0, 0, 3)]},
        "opponents": [{"name": T[k]["display"], "diff": me_e - T[k]["elo"]} for k in opps],
        "uses": [
            "「武蔵丘が勝つ見込み」は、いまの両校の点数を手順2の式に入れたもの。",
            "「この山を勝ち抜く見込み」は、山の組み合わせに沿って、1試合ずつの見込みを掛け合わせたもの。終わった試合は結果どおりに扱う。",
            "「当たる確率」＝ 武蔵丘がその試合まで勝ち上がる見込み × 相手がその試合まで勝ち上がる見込み。武蔵丘が途中で負けるとどちらとも当たらないので、"
            "同じ回戦の候補2校を足しても100%にはならず、足した値は「武蔵丘がその回戦まで勝ち上がる見込み」になる。100%との差は「武蔵丘がその前に負ける」場合"
            "（内訳は「勝ち上がりの道」の帯グラフ）。試合どうしは影響し合わない（独立）とみなして掛け算している。",
            "「格上・格下」は、試合の時点で点数の差が 50 点を超える相手。",
        ],
        "caveats": [
            "2022〜2026年度の大会の試合を、試合前の点数で当てられたかで設定を選んだ。2025・26年度の大会1,314試合で、見込みの高い側が勝った割合は80.3%（旧方式は76.9%）。",
            "リーグ戦をそのまま入れると当たり具合は悪くなった。控え（B・C）やクラブは点数が分からないまま始まるため。控えは学校のAから差し引いた点数で始め、試合数の少ないチームとの結果では学校の点数を動かさないようにして、はじめて良くなった。",
            "地区リーグは地区ごとに取れた量が違う（第8地区は学校の試合記録だけ）。取れた量の多い地区の学校ほど点数がよく動く。",
            "いちばん古い 2004年度の序盤は全校が 1500 点から始まるため、その時期の点数はあてにならない。ホームかどうか、延長かどうかは考えていない。",
        ],
    }


def meet_breakdown(T: dict, block: list, me: str, decided: list) -> dict:
    """回戦ごとに、100% を「相手Aと当たる／相手Bと当たる／武蔵丘がその前に負ける」に分ける。

    まだ終わっていない試合だけ強さの点数の見込みで計算し、終わった試合は結果どおりに畳む。
    「当たる確率」= 武蔵丘がその回戦まで勝ち上がる見込み × 相手がその回戦まで勝ち上がる見込み。
    同じ回戦の候補を足すと「武蔵丘がその回戦まで勝ち上がる見込み」になり、100% との差は武蔵丘がその前に負ける場合。
    """
    e = {k: T[k]["elo"] for k in block}
    won = {frozenset((d["a"], d["b"])): d["winner"] for d in decided}

    def dist(seq: list) -> dict:
        """seq の小さな山を勝ち上がる確率の分布。終わった試合は 1.0 / 0.0 に畳む。"""
        if len(seq) == 1:
            return {seq[0]: 1.0}
        half = len(seq) // 2
        left, right = dist(seq[:half]), dist(seq[half:])
        out: dict = defaultdict(float)
        for a, pa in left.items():
            for b, pb in right.items():
                w = won.get(frozenset((a, b)))
                if w:
                    out[w] += pa * pb
                else:
                    p = win_prob(e[a], e[b])
                    out[a] += pa * pb * p
                    out[b] += pa * pb * (1 - p)
        return dict(out)

    i = block.index(me)
    pair = block[(i // 2) * 2:(i // 2) * 2 + 2]          # 武蔵丘の1回戦のペア
    pair2 = block[((i // 2) ^ 1) * 2:((i // 2) ^ 1) * 2 + 2]  # 2回戦で当たりうる2校
    half = block[(i // 4) * 4:(i // 4) * 4 + 4]          # 武蔵丘の側の4校
    other = block[((i // 4) ^ 1) * 4:((i // 4) ^ 1) * 4 + 4]  # 反対側の4校
    d2, d3, dp2, dp3 = dist(pair), dist(half), dist(pair2), dist(other)

    def step(reach: float, opps: list, shares: dict, before: str) -> dict:
        return {"reach": round(reach, 3), "before": before,
                "opps": [{"key": o, "share": round(shares.get(o, 0.0), 3), "meet": round(reach * shares.get(o, 0.0), 3)}
                         for o in opps if shares.get(o, 0.0) > 0]}

    r1o = block[i ^ 1]
    return {
        "1回戦": step(1.0, [r1o], {r1o: 1.0}, ""),
        "2回戦": step(d2.get(me, 0.0), pair2, dp2, "1回戦で負ける"),
        "ブロック決勝": step(d3.get(me, 0.0), other, dp3, "2回戦までに負ける"),
        "detail": {"p1": round(d2.get(me, 0.0), 3), "p2": {o: round(win_prob(e[me], e[o]), 3) for o in pair2},
                   "r1": {o: round(dp2.get(o, dp3.get(o, 0.0)), 3) for o in pair2 + other}},
    }


def build(links: str) -> Path:
    data = build_data("武蔵丘", ROOT / "scout/sen2026_block10.json")
    FINAL = json.loads((ROOT / "scout/final_2026.json").read_text(encoding="utf-8"))
    UPSETS = json.loads((ROOT / "out/scout/upsets_2026.json").read_text(encoding="utf-8"))
    SQUAD = json.loads((ROOT / "out/scout/squad_2026.json").read_text(encoding="utf-8"))
    BOOK = json.loads((ROOT / "out/scout/index_2026.json").read_text(encoding="utf-8"))
    me = data["me"]
    T = data["teams"]
    block = data["block"]
    sched = {m["no"]: m for m in data["schedule"] if m.get("no")}
    i_me = block.index(me)
    r1 = block[i_me ^ 1]
    r2 = [block[i] for i in ((0, 1) if i_me in (2, 3) else (2, 3))]
    # 反対の山でブロック決勝に来うる2校＝向こうの2回戦【150】に出た2校。
    # alive で絞ると、負けた側のページが消えてリンク切れになる（2026-09-21）
    other = block[4:] if i_me < 4 else block[:4]
    fin = [k for k in other if k in (sched[150]["a"], sched[150]["b"])]
    r2_alive = [k for k in r2 if T[k]["alive"]]
    fin_alive = [k for k in fin if T[k]["alive"]]
    # 勝ち残りが1校になったら「候補」ではなく確定の相手
    rounds = {r1: ("1回戦", False), **{k: ("2回戦", len(r2_alive) > 1) for k in r2}, **{k: ("ブロック決勝", len(fin_alive) > 1) for k in fin}}
    r1_no = next(m["no"] for m in data["schedule"] if m.get("no") and me in (m["a"], m["b"]) and m["round"] == "1回戦")
    # 次の試合 = 武蔵丘の試合で、まだ勝者の決まっていないもの
    mine_no = next((m["no"] for m in data["schedule"] if m.get("no") and me in (m["a"], m["b"]) and not m.get("winner")), None)

    def mine_score(m: dict) -> str:
        return m["score"] if m["a"] == me else "-".join(reversed(m["score"].split("-")))

    def leg(n: str, label: str, no: int, teams: list) -> dict:
        m = sched[no]
        st = {"n": n, "round": label, "when": f"{m['date']}({m['dow']}) {m['time']}", "teams": teams}
        if m.get("score") and me in (m["a"], m["b"]):
            st["result"] = {"score": mine_score(m), "winner": m["winner"]}
        return st

    road = [leg("1", "1回戦", r1_no, [r1]), leg("2", "2回戦", 149, r2), leg("3", "ブロック決勝", 208, fin)]
    nxt_sched = sched[mine_no] if mine_no else None
    nxt_opp_key = (nxt_sched["a"] if nxt_sched["b"] == me else nxt_sched["b"]) if nxt_sched else None
    bd = meet_breakdown(T, block, me, data["decided"])
    for st in road:
        st["bd"] = bd[st["round"]]
    # 「当たる確率」は meet_breakdown を正本にする。build_scout_page 側の計算は
    # 1回戦しか畳まないため、2回戦以降が終わると 0% を返す（2026-09-21）
    meet_now = {o["key"]: o["meet"] for r in ("1回戦", "2回戦", "ブロック決勝") for o in bd[r]["opps"]}
    # 終わった試合の結果（その学校から見たスコアと相手）。outcome は最後の試合＝いまの状態
    outcomes: dict[str, list] = {}
    for d in data["decided"]:
        for side, opp in ((d["a"], d["b"]), (d["b"], d["a"])):
            sc = d["score"] if side == d["a"] else "-".join(reversed(d["score"].split("-")))
            outcomes.setdefault(side, []).append(
                {"won": d["winner"] == side, "score": sc, "opp": T[opp]["display"] if opp in T else opp, "round": d.get("round", "1回戦")}
            )
    outcome = {k: v[-1] for k, v in outcomes.items()}
    brief = {}
    for k in block:
        t = T[k]
        rnd = rounds.get(k, ("", False))
        brief[k] = {
            "display": t["display"], "alive": t["alive"], "blockWin": t["blockWin"], "vsMe": t["vsMe"],
            "meetProb": None if k == me else meet_now.get(k, 0.0),
            "elo": t.get("elo"), "eloRank": t.get("eloRank"), "area": t.get("area"), "round": rnd[0], "candidate": rnd[1],
            "leagueLine": league_line(t), "outcome": outcome.get(k), "outcomes": outcomes.get(k, []),
        }
    # 武蔵丘が実際に戦った相手と、次の相手だけを扱う。当たらなかった学校は載せない
    played = {d["a"] if d["b"] == me else d["b"] for d in data["decided"] if me in (d["a"], d["b"])}
    opps = [k for k in (r1, *r2, *fin) if k in played or k == nxt_opp_key]  # 当たった順→次の相手
    # 当たらなかった学校のカードは出さない。ページを作らないのでリンクが切れる
    for st in road:
        st["teams"] = [k for k in st["teams"] if k in opps]
    order = ["index", SLUG[me], *[SLUG[k] for k in opps], "seeds", "book"]
    # 歩みのページは build_history.py が別に書き出す。ここでは行き先として繋ぐだけ
    hist = f"history-{SLUG[me]}"
    for k in opps:
        TITLE[SLUG[k]] = f"{PAGE_NAME.get(SLUG[k], T[k]['display'].replace('都・', ''))}｜{SITE_NAME}"
    def state(k: str) -> str:
        if not T[k]["alive"]:
            return f"{rounds[k][0]}・敗退"
        return f"{rounds[k][0]}" + ("の候補" if rounds[k][1] else "・次の相手" if k == nxt_opp_key else "")

    titles = {k: PAGE_NAME.get(k, k) for k in [*order, hist]}

    urls: dict = {}
    if links == "artifact":
        urls = json.loads((ROOT / "scout/site_urls.json").read_text(encoding="utf-8"))
        hrefs = {s: urls.get(s, urls["index"]) for s in [*order, hist]}
        target, out_dir = "_blank", ROOT / "out/site_artifact"
    else:
        hrefs = {s: ("index.html" if s == "index" else f"{s}.html") for s in [*order, hist]}
        target, out_dir = None, ROOT / "out/site"
    out_dir.mkdir(parents=True, exist_ok=True)

    def nav_label(base: str, no: int) -> str:
        m = sched[no]
        return f"{base} 終了" if m.get("winner") else f"{base} {m['date']}"

    def nav_items(keys: list) -> list:
        return [{"slug": SLUG[k], "label": T[k]["display"].replace("都・", ""), "out": not T[k]["alive"]} for k in keys]

    keep = [k for k in opps]

    def item(slug: str, **kw) -> dict:
        return {"slug": slug, "label": PAGE_NAME.get(slug, slug), **kw}

    # 左パネルは「記録 → 試合 → 資料」の3段。名前は PAGE_NAME から引くので、
    # タブ名・パンくず・ツリーで同じ語になる
    nav = [
        {"label": "記録", "items": [item("index"), item(SLUG[me], cls="me"), item(hist)]},
        {"label": "1次予選の3試合", "items": [
            item(SLUG[k], out=not T[k]["alive"]) for k in (r1, *r2, *fin) if k in keep]},
        {"label": "資料", "phase": 2, "items": [item("seeds"), item("book")]},
    ]
    # 収録している試合数と、点数の計算に実際に使えた試合数（結果の読めたもの）は別の数字。
    # 2004年度まで遡った結果、古い年は対戦だけ分かってスコアが無い試合が増えた
    import rating
    from analyze_team import load_matches as _lm
    all_rows = _lm()
    total, rated = len(all_rows), sum(1 for r in all_rows if rating.played_tournament(r))
    first_year = min(r["年度"] for r in all_rows)
    common = {
        "me": me, "blockLabel": data["blockLabel"], "asOf": data["asOf"], "schedule": data["schedule"], "slots": data["slots"],
        "decided": data["decided"], "block": block, "brief": brief, "nav": nav, "links": hrefs, "linkTarget": target,
        "keyToSlug": {k: SLUG[k] for k in [me, *opps]}, "order": order, "titles": titles,
        "nTeamsRated": data["nTeamsRated"], "styleNone": data["styleNone"],
        "totalMatches": total, "ratedMatches": rated, "firstYear": first_year,
        "doneNote": "・".join(dict.fromkeys(d.get("round", "1回戦") for d in data["decided"])) + "は終了",
        "final": FINAL, "nextOpp": nxt_opp_key, "upsets": UPSETS, "over": not T[me]["alive"], "squad": SQUAD,
    }
    css = (ROOT / "scout/site/site.css").read_text(encoding="utf-8")
    js = (ROOT / "scout/site/site.js").read_text(encoding="utf-8")
    shell = (ROOT / "scout/site/page.html").read_text(encoding="utf-8")

    def write(slug: str, page: dict) -> None:
        html = shell.replace("__TITLE__", TITLE[slug]).replace("/*__CSS__*/", css).replace("/*__JS__*/", js)
        html = html.replace("/*__DATA__*/null", json.dumps({**common, **page, "slug": slug}, ensure_ascii=False))
        path = out_dir / ("index.html" if slug == "index" else f"{slug}.html")
        path.write_text(html, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")

    nm = sched[mine_no] if mine_no else None
    nxt_opp = (nm["a"] if nm["b"] == me else nm["b"]) if nm else None
    write("index", {"page": "hub", "next": {**nm, "opp": nxt_opp} if nm else None, "road": road, "formNote": data["formNote"], "pyramid": data["pyramid"],
                    "pyramidNote": data["pyramidNote"], "method": data["method"], "totalMatches": total, "ratedMatches": rated, "firstYear": first_year,
                    "elo": elo_explainer(T, me, nxt_opp or r1, opps)})
    me_t = {**T[me], "key": me}
    ins, bands, note = self_insights(me_t, block, {T[k]["display"]: T[k]["elo"] for k in opps})
    mine = brief[me].get("outcomes") or []
    done = "、".join(f"{o['round']}で{o['opp'].replace('都・', '')}に{o['score']}" for o in mine)
    all_won = mine and all(o["won"] for o in mine)
    lead = (f"第{T[me]['area']['area']}地区（{T[me]['area']['city']}）の{T[me]['area']['kind']}高校。"
            + (f"1次予選は{done}{'と勝ち上がりました' if all_won else 'という結果です'}。" if done else "")
            + (f"次は{nxt_sched['date']}({nxt_sched['dow']}) {nxt_sched['time']}の{T[nxt_opp_key]['display'].replace('都・', '')}戦です。" if nxt_sched and nxt_opp_key else "")
            + f"過去5年の公式戦{T[me]['summary']['n']}試合と今季のNSリーグから、強みと課題を整理しました。")
    write("musashigaoka", {"page": "self", "self": me_t, "insights": ins, "bands": bands, "bandNote": note, "selfLead": lead, "road": road})
    for k in opps:
        t = {**T[k], "key": k}
        t["autoPoints"] = team_points(t, me_t, T[me]["games"], brief[k])
        write(SLUG[k], {"page": "team", "team": t, "meHistory": T[me]["eloHistory"]})
    second = json.loads((ROOT / "out/scout/second_2026.json").read_text(encoding="utf-8"))
    # トーナメント表は画像をページに埋め込む（data URI）。こうすると手元・GitHub Pages・
    # claude.ai のどれでも同じ1ファイルで同じように出る
    png = (ROOT / "out/site/assets/sen26_2j_pred.png").read_bytes()
    assets = {"png": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
              "pdf": "https://shnbtkhr.github.io/tokyo-soccer-brackets/assets/sen26_2j_pred.pdf"}
    write("seeds", {"page": "second", "second": second, "assets": assets})
    write("book", {"page": "book", "book": BOOK})
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--links", choices=["local", "artifact"], default="local")
    args = ap.parse_args()
    build(args.links)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
