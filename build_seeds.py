"""2次予選から出てくる強豪校（1次予選の免除校）を分析し、その中で順位をつける。

どの学校が免除かは、過去の組み合わせから割り出した決まり（総体二次トーナメントの出場校＋T1・T2 の学校＋scout/seeds_2026.json の追加分）で決める。推定なので、
2次予選の組み合わせが出たら入れ替えること。

学校ごとに出すもの:
- 今季の所属リーグと順位（Tリーグ・プリンスリーグ関東。Bチーム以下の位置も）、リーグの直近5試合
- 過去の大会の成績（年度 × 大会の、いちばん先まで進んだ段階）
- 強さの点数（analyze_team.py の Elo）と、武蔵丘が勝つ見込み
- 武蔵丘とのつながり（connections.py と同じ数え方）
- 糸口（格下に負けた試合・無得点の試合・PK戦・接戦・リーグの失点など、崩すきっかけになりそうな数字）

順位のつけ方（総合点）は Claude Code が置いたもので、当たり具合は確かめていない（内訳は data/seeds/seeds_2026.md）:
- 3つの物差しを、強豪の中でいちばん上を100・いちばん下を0に換算し、重みをかけて平均する
  強さの点数 50% ／ 今季のリーグの位置 30% ／ 武蔵丘とのつながり 20%
- つながりが無い学校は、残り2つの重みで平均する

出力: out/scout/seeds_2026.json（サイト用）・data/seeds/seeds_2026.csv・data/seeds/seeds_2026.md（AI・Notebook 用）
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import connections as cn
from analyze_team import BASE, compute_elo, load_matches, played, result_for, summarize, win_prob
from build_outputs import normalize

ROOT = Path(__file__).parent
ME = "武蔵丘"
SEASON = 2026
CFG = json.loads((ROOT / "scout/seeds_2026.json").read_text(encoding="utf-8"))
REACH = {"決勝敗退": "準優勝", "準決勝敗退": "ベスト4", "準々決勝敗退": "ベスト8"}
SERIES = ("関東", "総体", "選手権", "新人戦")
DEPTH = {"総体": ("二次", "一次", "支部"), "選手権": ("二次", "一次"), "関東": ("",), "新人戦": ("",)}


def csv_rows(path: str) -> list[dict]:
    return list(csv.DictReader((ROOT / path).open(encoding="utf-8-sig")))


def teams_of(rows: list[dict], year: int, series: str, kw: str = "") -> set:
    return {k for r in rows if r["年度"] == year and r["大会"] == series and kw in r["段階"] for k in (r["kA"], r["kB"])} - {""}


def seed_keys(rows: list[dict], t12: set) -> list[str]:
    """免除とみる学校 = (総体二次の出場校 ∪ T1・T2 の学校) のうち 1次予選にいないもの ＋ scout/seeds_2026.json の追加分。"""
    return sorted(((teams_of(rows, SEASON, "総体", "二次") | t12) - teams_of(rows, SEASON, "選手権", "一次")) | set(CFG["extras"]))


def exemption_evidence(rows: list[dict], tl_st: list[dict], schools: set, seeds: set) -> dict:
    """免除の決まりが過去にどれだけ当てはまったか（年度ごと）と、当てはまらない例。"""
    t12 = defaultdict(set)
    tl_a = defaultdict(dict)
    for r in tl_st:
        if r["区分"] == "A" and r["学校"] in schools:
            tl_a[int(r["年度"])][r["学校"]] = r["リーグ"]
            if r["リーグ"] in ("T1", "T2"):
                t12[int(r["年度"])].add(r["学校"])
    years = []
    for y in range(2022, SEASON + 1):
        one, two, so2 = teams_of(rows, y, "選手権", "一次"), teams_of(rows, y, "選手権", "二次"), teams_of(rows, y, "総体", "二次")
        ex = (two - one) if two else seeds
        known_t = y in t12
        years.append({
            "year": y, "exempt": len(ex), "fromFirst": len(one), "so2": len(so2), "so2Exempt": len(so2 & ex),
            "t12": len(t12[y]) if known_t else None, "t12Exempt": len(t12[y] & ex) if known_t else None,
            "t12Only": len((ex - so2) & t12[y]) if known_t else None,
            "other": sorted(ex - so2 - t12[y]) if known_t else sorted(ex - so2), "otherKnown": known_t, "estimated": not two,
        })
    # 当てはまらない例（今年）: 関東予選に出た・T3〜T5 にいるのに 1次予選に出ている
    one = teams_of(rows, SEASON, "選手権", "一次")
    kanto = teams_of(rows, SEASON, "関東")
    lower = Counter()
    lower_in_first = Counter()
    for k, lg in tl_a[SEASON].items():
        if lg in ("T3", "T4", "T5"):
            lower[lg] += 1
            lower_in_first[lg] += k in one
    return {"years": years, "kantoInFirst": sorted(kanto & one), "kantoN": len(kanto), "kantoExempt": len(kanto & seeds),
            "lower": {lg: {"n": lower[lg], "inFirst": lower_in_first[lg]} for lg in sorted(lower)}}


def first_round_blocks(rows: list[dict], tl_a: dict) -> tuple[list, dict]:
    """1次予選の全ブロック。ブロックごとの学校（組み合わせ表の順）と、勝ち残りかどうか。"""
    by_block: dict = defaultdict(list)
    for r in rows:
        if r["年度"] == SEASON and r["大会"] == "選手権" and "一次" in r["段階"]:
            m = re.search(r"【(\d+)】", r["ブロック"])
            if m:
                by_block[int(m[1])].append(r)
    blocks, block_of = [], {}
    for no in sorted(by_block):
        rs = by_block[no]
        order: list = []
        for r in rs:
            for k in (r["kA"], r["kB"]):
                if k and k not in order:
                    order.append(k)
        lost = {k for r in rs if r["勝者"] for k in (r["kA"], r["kB"]) if k and k != normalize(r["勝者"])}
        final = next((r for r in rs if r["ラウンド"] == "ブロック決勝"), None)
        winner = normalize(final["勝者"]) if final and final["勝者"] else None
        played = sum(1 for r in rs if r["勝者"])
        for k in order:
            block_of[k] = no
        blocks.append({"no": no, "winner": winner, "played": played, "matches": len(rs),
                       "teams": [{"key": k, "out": k in lost, "tl": tl_a.get(k)} for k in order]})
    return blocks, block_of


def tleague_list(tl_st: list[dict], schools: set, seeds: set, block_of: dict) -> list:
    """2026年度の T1〜T5 の全チームと、選手権での扱い。"""
    groups: dict = defaultdict(list)
    for r in tl_st:
        if int(r["年度"]) != SEASON:
            continue
        k, sq = r["学校"], r["区分"]
        if k not in schools:
            st, lab = "club", "クラブ"
        elif sq != "A":
            st, lab = "sub", f"控え（{sq}）"
        elif k in seeds:
            st, lab = "seed", "免除"
        elif k in block_of:
            st, lab = "first", f"1次【{block_of[k]}】"
        else:
            st, lab = "unknown", "不明"
        groups[(r["リーグ"], r["ブロック"])].append({"rank": int(r["順位"]), "team": r["チーム"], "key": k, "status": st, "label": lab})
    return [{"league": lg, "block": b, "rows": sorted(v, key=lambda x: x["rank"])} for (lg, b), v in sorted(groups.items())]


def short_reach(stage: str, reach: str) -> str:
    lab = "二次" if "二次" in stage else "一次" if "一次" in stage else "支部" if "支部" in stage else ""
    if "東京代表" in reach:
        reach = "優勝（全国大会）"
    return (lab + " " if lab else "") + REACH.get(reach, reach.replace("敗退", ""))


def tournament_table(key: str, teams_csv: list[dict]) -> dict:
    """年度 × 大会ごとに、いちばん先まで進んだ段階。"""
    out: dict = defaultdict(dict)
    rows = [t for t in teams_csv if t["学校_正規化"] == key]
    for y in range(2022, SEASON + 1):
        for s in SERIES:
            cand = [t for t in rows if int(t["年度"]) == y and t["大会"] == s]
            for kw in DEPTH[s]:
                hit = [t for t in cand if kw in t["段階"]]
                if hit:
                    t = hit[0]
                    out[y][s] = {"text": short_reach(t["段階"], t["最終到達"]), "path": t["戦績"], "top": t["最終到達"] in ("優勝", "決勝敗退", "準決勝敗退")}
                    break
        ex = any(int(t["年度"]) == y and t["大会"] == "選手権" and "二次" in t["段階"] for t in rows) and not any(int(t["年度"]) == y and t["大会"] == "選手権" and "一次" in t["段階"] for t in rows)
        if ex and "選手権" in out[y]:
            out[y]["選手権"]["exempt"] = True
    return {y: out[y] for y in sorted(out, reverse=True)}


def league_info(key: str, tl_st: list[dict], tl_m: list[dict], pr_st: list[dict], pr_m: list[dict]) -> dict:
    size = Counter((r["年度"], r["リーグ"], r["ブロック"]) for r in tl_st)
    mine = [r for r in tl_st if r["学校"] == key]

    def pack(r: dict, league: str, n: int, level: float) -> dict:
        rank = int(r["順位"])
        return {"league": league, "rank": rank, "n": n, "pts": int(r["勝点"]), "played": int(r["試合"]), "w": int(r["勝"]), "d": int(r["分"]), "l": int(r["敗"]),
                "gf": int(r["得点"]), "ga": int(r["失点"]), "pos": round(level + (rank - 1) / n, 3), "team": r["チーム"]}

    cur = last = None
    pr = next((r for r in pr_st if r["学校"] == key), None)
    if pr:
        cur = pack(pr, pr["リーグ"], len(pr_st), 0)
    for yr, slot in ((SEASON, "cur"), (SEASON - 1, "last")):
        a = next((r for r in mine if int(r["年度"]) == yr and r["区分"] == "A"), None)
        if a and not (slot == "cur" and cur):
            v = pack(a, f"{a['リーグ']}{' ' + a['ブロック'] if a['ブロック'] else ''}", size[(a["年度"], a["リーグ"], a["ブロック"])], int(a["リーグ"][1]))
            if slot == "cur":
                cur = v
            else:
                last = v
    reserves = [f"{r['区分']}チーム {r['リーグ']}{r['ブロック'][:1] if r['ブロック'] else ''} {r['順位']}位" for r in sorted(mine, key=lambda r: r["区分"]) if int(r["年度"]) == SEASON and r["区分"] != "A"]
    # 直近の試合（新しい順に5つ）
    form = []
    if pr:
        ms = [m for m in pr_m if m["実施"] == "済" and key in (m["ホーム学校"], m["アウェイ学校"])]
        for m in ms:
            home = m["ホーム学校"] == key
            gf, ga = (int(m["ホーム得点"]), int(m["アウェイ得点"])) if home else (int(m["アウェイ得点"]), int(m["ホーム得点"]))
            form.append({"date": m["日付"], "opp": m["アウェイ"] if home else m["ホーム"], "gf": gf, "ga": ga})
    elif cur:
        sq = "A"
        for m in tl_m:
            if int(m["年度"]) != SEASON or m["実施"] != "済":
                continue
            if m["ホーム学校"] == key and m["ホーム区分"] == sq:
                form.append({"date": m["日付"], "opp": m["アウェイ"], "gf": int(m["ホーム得点"]), "ga": int(m["アウェイ得点"])})
            elif m["アウェイ学校"] == key and m["アウェイ区分"] == sq:
                form.append({"date": m["日付"], "opp": m["ホーム"], "gf": int(m["アウェイ得点"]), "ga": int(m["ホーム得点"])})
    form.sort(key=lambda g: g["date"], reverse=True)
    for g in form:
        g["res"] = "勝" if g["gf"] > g["ga"] else "負" if g["gf"] < g["ga"] else "分"
    if not cur:  # Tリーグにもプリンスにもいない → 地区リーグ（順位は未確認）
        cur = {"league": "地区リーグ（未確認）", "rank": None, "n": None, "pos": 6.5}
    return {"cur": cur, "last": last, "reserves": reserves, "form": form[:5]}


def clues(t: dict, games: list, me_elo: float) -> list[str]:
    """崩すきっかけになりそうな数字。"""
    out = []
    recent = [g for g in games if g["year"] >= SEASON - 1]
    ups = sorted([g for g in recent if g["res"] in ("負", "PK負") and g["myElo"] and g["oppElo"] and g["myElo"] - g["oppElo"] > 50],
                 key=lambda g: g["oppElo"] - g["myElo"])
    if ups:
        out.append("直近2年で<b>格下に負けた試合が{}つ</b>: ".format(len(ups)) + "、".join(
            f"{g['year']} {g['series']} {g['round']}で{g['opp'].replace('都・', '')}に{g['gf']}-{g['ga']}{'（PK ' + g['pk'] + '）' if g['pk'] else ''}（相手は{g['myElo'] - g['oppElo']}点下）" for g in ups[:3]) + "。")
    else:
        out.append("直近2年、格下（50点以上下）への負けは<b>無い</b>。取りこぼしの少ない学校。")
    S = summarize(recent)
    if S["n"]:
        out.append(f"直近2年の大会 {S['n']}試合で、無得点が<b>{S['scoreless']}試合</b>、1点差以内の決着が<b>{S['oneGoal']}試合</b>、1試合平均の失点 <b>{S['gaPer']}</b>。")
    A = summarize(games)
    npk = A["pkw"] + A["pkl"]
    if npk:
        tail = "数が少なく、傾向は言えない。" if npk < 3 else "PK戦には強い。" if A["pkw"] > A["pkl"] else "PK戦に持ち込めば五分以上。"
        out.append(f"PK戦は5年間で<b>{A['pkw']}勝{A['pkl']}敗</b>。{tail}")
    lg = t["league"]
    cur = lg["cur"]
    if cur.get("played"):
        out.append(f"今季の{cur['league']}は{cur['played']}試合で失点<b>{cur['ga']}</b>（1試合 {cur['ga'] / cur['played']:.1f}）、{cur['w']}勝{cur['d']}分{cur['l']}敗。")
    if lg["form"]:
        f = lg["form"]
        c = Counter(g["res"] for g in f)
        out.append(f"リーグの直近{len(f)}試合は{c['勝']}勝{c['分']}分{c['負']}敗、失点{sum(g['ga'] for g in f)}。")
    h = t["eloHistory"]
    if str(SEASON - 1) in h or (SEASON - 1) in h:
        prev = h.get(SEASON - 1, h.get(str(SEASON - 1)))
        d = t["elo"] - prev
        if abs(d) >= 15:
            out.append(f"強さの点数は昨年度末から<b>{d:+d}</b>（{'上り調子' if d > 0 else '下り気味'}）。")
    return out


def main() -> int:
    rows = load_matches()
    elo, hist, n_games = compute_elo(rows)
    games: dict = defaultdict(list)
    for r in rows:
        if played(r):
            for k in (r["kA"], r["kB"]):
                if k:
                    games[k].append(result_for(r, k))
    ranked = [k for k, _ in sorted(elo.items(), key=lambda kv: -kv[1]) if n_games.get(k, 0) >= 5]
    rank_of = {k: i + 1 for i, k in enumerate(ranked)}
    teams_csv = csv_rows("out/teams.csv")
    tl_st, tl_m = csv_rows("data/leagues/tleague_standings.csv"), csv_rows("data/leagues/tleague_matches.csv")
    pr_st, pr_m = csv_rows("data/leagues/prince_kanto1_2026_standings.csv"), csv_rows("data/leagues/prince_kanto1_2026_matches.csv")
    areas = json.loads((ROOT / "out/scout/member_areas.json").read_text(encoding="utf-8"))
    adj, disp = cn.load(SEASON)
    me_elo = elo.get(ME, BASE)

    schools = set(areas) | {k for k in games if games[k]}  # 加盟校一覧か、高体連の大会に出たことがある = 学校（クラブではない）
    tl_a = {r["学校"]: r["リーグ"] for r in tl_st if int(r["年度"]) == SEASON and r["区分"] == "A" and r["学校"] in schools}
    so2 = teams_of(rows, SEASON, "総体", "二次")
    past_ex = {y: teams_of(rows, y, "選手権", "二次") - teams_of(rows, y, "選手権", "一次") for y in range(2022, SEASON)}
    prince = {r["学校"] for r in pr_st}
    first_keys = teams_of(rows, SEASON, "選手権", "一次")

    def reach_of(key: str, y: int, series: str, kw: str = "") -> str:
        t = next((t for t in teams_csv if t["学校_正規化"] == key and int(t["年度"]) == y and t["大会"] == series and kw in t["段階"]), None)
        return short_reach(t["段階"], t["最終到達"]).replace("二次 ", "").replace("東京都予選 ", "") if t else ""

    def exempt_reasons(key: str) -> dict:
        tags = []
        if key in so2:
            tags.append({"tag": "総体二次", "text": f"2026年度 総体の二次トーナメントに出場（{reach_of(key, SEASON, '総体', '二次')}）", "sure": True})
        if key in prince:
            tags.append({"tag": "プリンス", "text": "プリンスリーグ関東1部に所属（T1より上）", "sure": False})
        if tl_a.get(key) in ("T1", "T2"):
            tags.append({"tag": tl_a[key], "text": f"Tリーグ {tl_a[key]} にトップチームが所属", "sure": True})
        if not tags:
            tags.append({"tag": "その他", "text": "総体二次にも T1・T2 にも当てはまらない。1次予選の組み合わせにいないので免除とみた（決まりは未確認）", "sure": False})
        facts = ["1次予選の組み合わせ（266校）に名前が無い"]
        lg = tl_a.get(key)
        if lg in ("T3", "T4", "T5"):
            same = sorted(k for k, v in tl_a.items() if v == lg)
            first = [k for k in same if k in first_keys]
            facts.append(f"Tリーグ {lg} に所属。ただし {lg} の {len(same)} 校のうち {len(first)} 校（{'・'.join(first)}）は1次予選に出ているので、{lg} にいることだけでは免除の理由にならない")
        yrs = [y for y in range(2022, SEASON) if key in past_ex[y]]
        facts.append("過去の1次予選免除: " + ("・".join(f"{y}" for y in yrs) + f"年度（{len(yrs)}/4年）" if yrs else "なし（今年が初めて）"))
        if k := reach_of(key, SEASON, "関東"):
            facts.append(f"2026年度 関東予選: {k}")
        if n := reach_of(key, SEASON - 1, "新人戦"):
            facts.append(f"2025年度 新人戦（地区）: {n}")
        return {"tags": tags, "facts": facts, "short": "・".join(t["tag"] for t in tags)}

    seeds = []
    for key in seed_keys(rows, {k for k, lg in tl_a.items() if lg in ("T1", "T2")}):
        latest = max((t for t in teams_csv if t["学校_正規化"] == key), key=lambda t: int(t["年度"]), default=None)
        display = re.sub(r"^(都・|都立)", "", latest["学校"]) if latest else key
        gs = games[key]
        cs = cn.chains(adj, ME, key, SEASON)
        top = cn.pick(cs, 4)
        t = {
            "key": key, "display": display, "area": areas.get(key),
            "elo": round(elo.get(key, BASE)), "eloRank": rank_of.get(key), "eloHistory": hist.get(key, {}), "vsMe": round(win_prob(me_elo, elo.get(key, BASE)), 3),
            "summary": summarize(gs), "recent": summarize([g for g in gs if g["year"] >= SEASON - 1]),
            "tourn": tournament_table(key, teams_csv),
            "league": league_info(key, tl_st, tl_m, pr_st, pr_m),
            "h2h": [g for g in games[ME] if g["oppKey"] == key],
            "conn": {"summary": cn.summarize(cs), "top": [{"path": [disp.get(p, p).replace("都・", "") for p in c["path"]], "legs": c["legs"], "implied": c["implied"], "w": c["w"], "hops": c["hops"]} for c in top]},
            "exempt": exempt_reasons(key),
        }
        t["why"] = t["exempt"]["short"]
        t["clues"] = clues(t, gs, me_elo)
        seeds.append(t)

    # 総合点: 強豪の中で、いちばん上=100・いちばん下=0 に換算して重みづけ平均
    W = CFG["weights"]

    def scale(vals: dict, higher_better: bool) -> dict:
        v = {k: x for k, x in vals.items() if x is not None}
        lo, hi = min(v.values()), max(v.values())
        return {k: round(100 * ((x - lo) if higher_better else (hi - x)) / (hi - lo), 1) if hi > lo else 50.0 for k, x in v.items()}

    e_s = scale({t["key"]: t["elo"] for t in seeds}, True)
    l_s = scale({t["key"]: t["league"]["cur"]["pos"] for t in seeds}, False)
    c_s = scale({t["key"]: t["conn"]["summary"]["weighted"] for t in seeds}, False)  # 目安がマイナス = 相手が武蔵丘より上
    for t in seeds:
        parts = {"elo": e_s.get(t["key"]), "league": l_s.get(t["key"]), "conn": c_s.get(t["key"])}
        wsum = sum(W[k] for k, v in parts.items() if v is not None)
        t["scores"] = {**parts, "total": round(sum(W[k] * v for k, v in parts.items() if v is not None) / wsum, 1)}
    seeds.sort(key=lambda t: -t["scores"]["total"])
    for i, t in enumerate(seeds, 1):
        t["rank"] = i
    for part in ("elo", "league", "conn"):
        order = sorted([t for t in seeds if t["scores"][part] is not None], key=lambda t: -t["scores"][part])
        for i, t in enumerate(order, 1):
            t.setdefault("partRank", {})[part] = i

    seed_set = {t["key"] for t in seeds}
    blocks, block_of = first_round_blocks(rows, tl_a)
    out = {"asOf": CFG["asOf"], "status": CFG["status"], "rule": CFG["rule"], "weights": W, "me": ME, "meElo": round(me_elo), "nTeamsRated": len(rank_of), "seeds": seeds,
           "evidence": exemption_evidence(rows, tl_st, schools, seed_set), "firstRound": blocks, "nFirst": len(block_of), "myBlock": block_of.get(ME),
           "tleague": tleague_list(tl_st, schools, seed_set, block_of)}
    path = ROOT / "out/scout/seeds_2026.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    write_tables(out)
    print(f"wrote {path.relative_to(ROOT)}（{len(seeds)}校）")
    for t in seeds:
        c = t["league"]["cur"]
        print(f"{t['rank']:2d} {t['display']:10s} 総合{t['scores']['total']:5.1f}  点数{t['elo']}  {c['league']} {c.get('rank') or ''}  つながり{t['conn']['summary']['weighted']}  勝つ見込み{t['vsMe']:.0%}")
    return 0


def write_tables(out: dict) -> None:
    d = ROOT / "data/seeds"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "seeds_2026.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["順位", "学校", "総合点", "強さの点数", "強さの点数_換算", "今季のリーグ", "リーグ順位", "リーグ_換算", "つながり_目安", "つながり_換算", "武蔵丘が勝つ見込み", "免除の根拠"])
        for t in out["seeds"]:
            c, s = t["league"]["cur"], t["scores"]
            w.writerow([t["rank"], t["display"], s["total"], t["elo"], s["elo"], c["league"], c.get("rank") or "", s["league"], t["conn"]["summary"]["weighted"], s["conn"] if s["conn"] is not None else "", t["vsMe"], t["why"]])
    W = out["weights"]
    md = ["# 2次予選から出てくる強豪校（2026年度 第105回 選手権東京都予選）", "",
          f"作成: {out['asOf']}（Claude Code・build_seeds.py）。状態: {out['status']}", "",
          "## 免除校の決め方（推定）", "", *[f"- {r}" for r in out["rule"]], "",
          "## 総合点の出し方（Claude Code が置いた方法。ユーザー承認前・当たり具合は未検証）", "",
          f"- 強さの点数（Elo）{int(W['elo'] * 100)}% ／ 今季のリーグの位置 {int(W['league'] * 100)}% ／ 武蔵丘とのつながり {int(W['conn'] * 100)}%",
          "- それぞれ、強豪の中でいちばん上を100・いちばん下を0に換算してから平均する。つながりが無い学校は残り2つで平均する",
          "- リーグの位置: プリンス関東1部=0、T1=1 … T5=5 に、ブロック内の順位（(順位−1)/チーム数）を足した値。小さいほど上。Tリーグにもプリンスにもいない学校は 6.5（地区リーグ・順位未確認）",
          f"- 武蔵丘の強さの点数: {out['meElo']}", "",
          "## ランキング", "", "| 順位 | 学校 | 総合点 | 強さの点数 | 今季のリーグ | つながり（目安） | 武蔵丘が勝つ見込み |", "|---|---|---|---|---|---|---|"]
    for t in out["seeds"]:
        c = t["league"]["cur"]
        lg = f"{c['league']} {c['rank']}位/{c['n']}" if c.get("rank") else c["league"]
        cw = t["conn"]["summary"]["weighted"]
        md.append(f"| {t['rank']} | {t['display']} | {t['scores']['total']} | {t['elo']}（{t['eloRank']}位） | {lg} | {'' if cw is None else f'{cw:+.2f}'} | {t['vsMe']:.0%} |")
    md.append("")
    for t in out["seeds"]:
        lg = t["league"]
        md += [f"## {t['rank']}. {t['display']}", "", f"- 免除の根拠: {t['why']}", f"- 地区: " + (f"第{t['area']['area']}地区・{t['area']['city']}" if t["area"] else "不明")]
        c = lg["cur"]
        md.append(f"- 今季のリーグ: {c['league']}" + (f" {c['rank']}位/{c['n']}（{c['w']}勝{c['d']}分{c['l']}敗・得点{c['gf']} 失点{c['ga']}）" if c.get("rank") else ""))
        if lg["last"]:
            md.append(f"- 昨季: {lg['last']['league']} {lg['last']['rank']}位/{lg['last']['n']}")
        if lg["reserves"]:
            md.append("- 控えチーム（今季）: " + "、".join(lg["reserves"]))
        md.append("- 大会の成績: " + " ／ ".join(f"{y}年度 " + "・".join(f"{s} {v['text']}" for s, v in yr.items()) for y, yr in t["tourn"].items()))
        cs = t["conn"]["summary"]
        md.append(f"- 武蔵丘とのつながり: {cs['n']}本（武蔵丘が上とみる {cs['up']}・下とみる {cs['down']}）、重みつき平均 {cs['weighted']}" if cs["n"] else "- 武蔵丘とのつながり: なし")
        md += ["- 糸口:", *[f"  - {re.sub(r'</?b>', '**', c)}" for c in t["clues"]], ""]
    (d / "seeds_2026.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
