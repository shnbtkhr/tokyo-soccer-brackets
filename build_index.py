"""年鑑の「対戦校名鑑」に使うデータを作る。

東京の高校を1校1件で並べ、地区・強さの点数・通算成績・今季のリーグ・武蔵丘との対戦を
まとめる。誌面は別に作るので、ここは数字を揃えることだけを受け持つ。

名簿に入れる学校（2つの条件のどちらかを満たすもの）
  1. 高体連の加盟校一覧にある（321校）
  2. トーナメントに10試合以上出ていて、名前が壊れていない

2 を足すのは、統廃合や改称で今の一覧から消えた学校が過去の対戦相手として出てくるため。
読み取りに失敗した名前（「帝京となりました。」のような断片）は 1〜4試合に偏るので、
10試合を境にすると機械的に落とせる。名簿に入れた学校には member を付け、誌面側で
「現在の加盟校一覧には無い」と断れるようにする。

加盟校一覧の側も normalize() を通してから突き合わせる。一覧は正式名（日本体育大学荏原）、
大会の表は略称（日体大荏原）で書かれているため、素の文字列では繋がらない。

  uv run python build_index.py
  uv run python build_index.py --district 5    # 1地区ぶんだけ確かめる

出力: out/scout/index_2026.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from analyze_team import compute_elo, load_matches
from build_history import CUP_ORDER, ROUND_RANK, tier_of
from build_outputs import normalize
from leagues import for_school, load_all

ROOT = Path(__file__).parent
OUT = ROOT / "out/scout/index_2026.json"
SEASON = 2026
ME = "武蔵丘"
MIN_GAMES = 10
RECENT = ("2026", "2025", "2024")  # 直近3年（新しい順）
DISTRICTS = {
    1: "江戸川区・江東区・墨田区・葛飾区・足立区の一部",
    2: "文京区・台東区・荒川区・北区・豊島区",
    3: "板橋区・練馬区の一部・北区の一部・足立区の一部",
    4: "品川区・大田区・目黒区の一部",
    5: "中野区・杉並区・練馬区・西東京市",
    6: "世田谷区・目黒区・渋谷区・港区・千代田区・中央区",
    7: "三鷹市・調布市・府中市・狛江市・多摩市・町田市ほか",
    8: "八王子市・立川市・武蔵野市・小金井市・福生市ほか",
}


def broken(name: str) -> bool:
    """読み取りに失敗した名前。数字・記号が混じるか、長すぎるもの。

    ひらがなの数や1文字を理由にしてはいけない。「かえつ有明」「東」はどちらも実在する
    学校で、前の版ではこの2校を名簿から落としていた。
    """
    return bool(re.search(r"[0-9()（）,、。※・]", name)) or not 1 <= len(name) <= 12


def load_standings() -> dict:
    """今季のリーグの順位表を、学校ごとに1件だけ持つ（上のリーグを優先）。"""
    out: dict[str, dict] = {}
    # 上のリーグから順に見る。帝京のようにプリンスリーグ関東に出ている学校は
    # T リーグの順位表に載らないので、ここを飛ばすと所属が空になる
    src = [("data/leagues/prince_kanto1_2026_standings.csv", "", 0),
           ("data/leagues/tleague_standings.csv", "ブロック", 1),
           ("data/leagues/district_standings.csv", "部", 2)]
    for path, div_key, pri in src:
        p = ROOT / path
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if r["年度"] == str(SEASON)]
        size = Counter((r["リーグ"], r.get(div_key, "")) for r in rows)
        for r in rows:
            school = normalize(r["学校"])
            # 控え（B・C）は学校の成績として扱わない
            if not school or r.get("区分") not in ("", "A", None):
                continue
            if school in out and out[school]["_pri"] <= pri:
                continue
            name = " ".join(x for x in (r["リーグ"], r.get(div_key, "")) if x)
            out[school] = {
                "name": name, "rank": int(r["順位"]) if r["順位"].isdigit() else None,
                "of": size[(r["リーグ"], r.get(div_key, ""))],
                "w": int(r["勝"] or 0), "d": int(r["分"] or 0), "l": int(r["敗"] or 0),
                "gf": int(r["得点"] or 0), "ga": int(r["失点"] or 0), "_pri": pri,
            }
    for v in out.values():
        v.pop("_pri", None)
    return out


def summarize(games: list[dict]) -> dict:
    """通算成績。PK は勝敗と分けて数える（勝率の出し方を誌面側が選べるように）。"""
    s = {"w": 0, "pkw": 0, "pkl": 0, "d": 0, "l": 0, "unknown": 0,
         "gf": 0, "ga": 0, "cleanSheets": 0, "scoreless": 0}
    for g in games:
        gf, ga, pf, pa = g["gf"], g["ga"], g["pf"], g["pa"]
        if gf is None:
            s["unknown"] += 1
            continue
        s["gf"] += gf
        s["ga"] += ga
        s["cleanSheets"] += ga == 0
        s["scoreless"] += gf == 0
        if gf > ga:
            s["w"] += 1
        elif gf < ga:
            s["l"] += 1
        elif pf is not None and pa is not None and pf != pa:
            s["pkw" if pf > pa else "pkl"] += 1
        else:
            s["d"] += 1
    n = s["w"] + s["pkw"] + s["pkl"] + s["d"] + s["l"]
    s["gfPer"] = round(s["gf"] / n, 2) if n else None
    s["gaPer"] = round(s["ga"] / n, 2) if n else None
    return s


def best_run(games: list[dict]) -> dict | None:
    """いちばん奥まで進んだ年と、そこがどこか。"""
    top, best = (-1, -1), None
    for g in games:
        v = (tier_of(g["stage"]), ROUND_RANK.get(g["round"], 0))
        if v > top:
            stage = re.sub(r"^第\s*\d+\s*回\s*", "", g["stage"])
            top = v
            best = {"year": int(g["year"]), "text": " ".join(x for x in (g["series"], stage, g["round"]) if x)}
    return best


def my_games(games: list[dict]) -> dict:
    """武蔵丘との対戦。顧問が「この学校と当たったことがあるか」を引くためのもの。"""
    vs = [g for g in games if g["opp"] == ME]
    out = []
    for g in sorted(vs, key=lambda x: (x["year"], x["series"])):
        res = "" if g["gf"] is None else "○" if g["gf"] > g["ga"] else "●" if g["gf"] < g["ga"] else "△"
        out.append({"year": int(g["year"]), "series": g["series"],
                    "round": " ".join(x for x in (re.sub(r"^第\s*\d+\s*回\s*", "", g["stage"]), g["round"]) if x),
                    "gf": g["gf"], "ga": g["ga"], "res": res})
    return {"n": len(out), "w": sum(1 for g in out if g["res"] == "○"),
            "l": sum(1 for g in out if g["res"] == "●"), "games": out}


def md(date: str) -> str:
    """「2026-09-13」も「9/13」も「9/13」の形にそろえる。無ければ空。"""
    d = (date or "").strip()
    m = re.match(r"(?:\d{4}-)?(\d{1,2})[-/](\d{1,2})", d)
    return f"{int(m[1])}/{int(m[2])}" if m else ""


def sort_key(g: dict) -> tuple:
    """日付の順に並べる。日付の無いものは末尾へ。

    今季の選手権は93%の試合に日付が入っていない（トーナメント表に日付欄が無い年がある）。
    末尾へ落とすだけだと「1回戦・ブロック決勝・2回戦」のような並びになって読めないので、
    日付の無いものは 大会 → 一次/二次 → 回戦の深さ の順に並べ直す。日付を推測して
    埋めることはしない。
    """
    series = g.get("series", "")
    m = re.match(r"(\d{1,2})/(\d{1,2})", g.get("date") or "")
    if m:
        mo = int(m[1])
        # 4月始まりの年度順。ただし関東大会の都予選だけは年度が始まる前（3月）に
        # 行われるので、12を足すと末尾に落ちてしまう。2026年度は27試合が3月だった
        late = mo < 4 and series != "関東"
        return (0, mo + 12 if late else mo, int(m[2]), 0, 0)
    cup = CUP_ORDER.index(series) if series in CUP_ORDER else 8
    rd = g.get("round", "")
    tier = 2 if ("二次" in rd or "都予選" in rd) else 1
    depth = next((v for k, v in ROUND_RANK.items() if k in rd), 0)
    return (1, cup, 0, -tier, depth)


def res_of(gf, ga) -> str:
    return "" if gf is None else "○" if gf > ga else "●" if gf < ga else "△"


def recent_years(games: list[dict], years: tuple[str, ...]) -> list[dict]:
    """直近の年度ごとの成績。上り調子か下り坂かを見るためのもの。

    大会（トーナメント）だけで数える。`best`（どこまで勝ち進んだか）が
    トーナメントにしか無い考え方で、summary とも揃うため。
    """
    out = []
    for y in years:
        gs = [g for g in games if str(g["year"]) == y]
        if not gs:
            continue
        rec = {"year": int(y), "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0}
        for g in gs:
            r = res_of(g["gf"], g["ga"])
            if not r:
                continue
            rec["w" if r == "○" else "l" if r == "●" else "d"] += 1
            rec["gf"] += g["gf"]
            rec["ga"] += g["ga"]
        b = best_run(gs)
        if b:
            rec["best"] = b["text"]
        out.append(rec)
    return out


def this_season(games: list[dict], league: list[dict], year: str, limit: int) -> list[dict]:
    """今季の全試合。大会とリーグ戦を日付順に並べる。"""
    out = []
    for g in games:
        # 二次予選の表は組み合わせが先に出るので、まだ行われていない試合が入っている。
        # 「誰に勝って誰に負けたか」の一覧なので、結果の無いものは載せない
        if str(g["year"]) != year or g["gf"] is None:   # 大会は数、リーグ戦は文字で年度
            continue
        stage = re.sub(r"^第\s*\d+\s*回\s*", "", g["stage"])
        out.append({"date": md(g.get("date", "")), "series": g["series"],
                    "round": " ".join(x for x in (stage, g["round"]) if x),
                    "opp": g["opp"], "gf": g["gf"], "ga": g["ga"],
                    "res": res_of(g["gf"], g["ga"])})
    for m in league:
        if str(m["年度"]) != year or m["得点"] is None:
            continue
        out.append({"date": md(m["日付"]), "series": m["大会"], "round": m["段階"],
                    "opp": m["相手"], "gf": m["得点"], "ga": m["失点"], "res": m["結果"]})
    out.sort(key=sort_key)
    # 「直近5試合」なので後ろから取る。先頭から取ると4月の試合ばかりになる
    return out[-limit:] if limit else out


def common_opponents(mine: list[dict], theirs: list[dict], limit: int) -> list[dict]:
    """武蔵丘との共通の対戦相手。直接対戦が無い学校の力関係を間接的に見るため。

    相手ごとに、いちばん新しい試合どうしを並べる。
    """
    def latest(gs: list[dict]) -> dict:
        by: dict[str, dict] = {}
        for g in gs:
            if g["gf"] is None or not g["opp"] or g["opp"] == "（不明）":
                continue
            cur = by.get(g["opp"])
            if not cur or g["year"] >= cur["year"]:
                by[g["opp"]] = g
        return by

    a, b = latest(mine), latest(theirs)
    shared = sorted(set(a) & set(b), key=lambda k: -max(int(a[k]["year"]), int(b[k]["year"])))
    out = []
    for k in shared[:limit]:
        x, y = a[k], b[k]
        out.append({"opp": k,
                    "me": {"gf": x["gf"], "ga": x["ga"], "res": res_of(x["gf"], x["ga"]), "year": int(x["year"])},
                    "them": {"gf": y["gf"], "ga": y["ga"], "res": res_of(y["gf"], y["ga"]), "year": int(y["year"])}})
    return out


def collect_games(rows: list[dict]) -> dict[str, list[dict]]:
    """学校ごとに、自分から見た試合の一覧を作る。"""
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        a, b = r["チームA_正規化"], r["チームB_正規化"]
        for me, opp, gf, ga, pf, pa in ((a, b, r["得点A"], r["得点B"], r["PK_A"], r["PK_B"]),
                                        (b, a, r["得点B"], r["得点A"], r["PK_B"], r["PK_A"])):
            if not me:
                continue
            num = lambda v: int(v) if str(v).strip().isdigit() else None  # noqa: E731
            by[me].append({"year": r["年度"], "series": r["大会"], "stage": r["段階"],
                           "round": r["ラウンド"], "opp": opp, "date": r["日付"],
                           "gf": num(gf), "ga": num(ga), "pf": num(pf), "pa": num(pa)})
    return by


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--district", type=int, default=0, help="1地区ぶんだけ中身を表示する")
    args = ap.parse_args()

    rows = load_matches()
    elo, hist, ngames = compute_elo(rows)
    games = collect_games(rows)
    # リーグ戦の試合数は、点数の動きやすさの目安になる（取れている量が地区で差がある）。
    # 合計ではなく内訳で持たせる
    league_all = load_all()
    league_n = Counter()
    for r in league_all:
        for school, squad in ((r["ホーム学校"], r["ホーム区分"]), (r["アウェイ学校"], r["アウェイ区分"])):
            if school and squad in ("", "A"):
                league_n[school] += 1
    # 学校ごとのリーグ戦は、339校ぶん for_school を回すと遅いので1回で作る
    league_by: dict[str, list[dict]] = defaultdict(list)
    for r in league_all:
        for home in (True, False):
            me = r["ホーム学校"] if home else r["アウェイ学校"]
            squad = r["ホーム区分"] if home else r["アウェイ区分"]
            if not me or squad not in ("", "A"):
                continue
            gf, ga = (r["得点H"], r["得点A"]) if home else (r["得点A"], r["得点H"])
            league_by[me].append({
                "年度": r["年度"], "大会": r["リーグ"], "段階": r["区分"], "日付": r["日付"],
                "相手": (r["アウェイ学校"] + r["アウェイ区分"]) if home else (r["ホーム学校"] + r["ホーム区分"]),
                "得点": gf, "失点": ga, "結果": "○" if gf > ga else "●" if gf < ga else "△"})
    standings = load_standings()
    # 加盟校一覧は正式名で書かれている。大会の表と繋ぐため、同じ名寄せを通す
    areas = {normalize(k): v for k, v in
             json.loads((ROOT / "out/scout/member_areas.json").read_text(encoding="utf-8")).items()}

    roster = sorted({k for k in areas} |
                    {k for k in elo if ngames.get(k, 0) >= MIN_GAMES and not broken(k)})
    rank_all = {k: i + 1 for i, k in enumerate(sorted(roster, key=lambda k: -elo.get(k, 0)))}
    by_district: dict[int, list[str]] = defaultdict(list)
    for k in roster:
        d = areas.get(k, {}).get("area")
        if d:
            by_district[d].append(k)
    drank = {}
    for d, ks in by_district.items():
        for i, k in enumerate(sorted(ks, key=lambda k: -elo.get(k, 0))):
            drank[k] = i + 1

    schools = []
    for k in roster:
        a = areas.get(k, {})
        g = games.get(k, [])
        mine = a.get("area") == 5
        rec = {
            "key": k, "display": ("都・" if a.get("kind") == "都立" else "") + k, "kana": None,
            "member": k in areas, "district": a.get("area"), "city": a.get("city"), "kind": a.get("kind"),
            "elo": round(elo[k]) if k in elo else None, "eloRank": rank_all[k],
            "districtRank": drank.get(k), "games": ngames.get(k, 0),
            "tournamentGames": len(g), "leagueGames": league_n.get(k, 0),
            "summary": summarize(g), "best": best_run(g), "league": standings.get(k),
            "vsMe": my_games(g),
        }
        # 量が増えすぎないよう、第5地区以外は今季と共通の相手を削る
        rec["recentYears"] = recent_years(g, RECENT)
        rec["thisSeason"] = this_season(g, league_by.get(k, []), str(SEASON), 0 if mine else 5)
        if k != ME:
            rec["commonOpponents"] = common_opponents(games.get(ME, []), g, 5 if mine else 3)
        if mine:
            ls = for_school(league_all, k)
            seen: dict[int, str] = {}
            for m in sorted(ls, key=lambda m: m["年度"]):
                if m["段階"] and "順位決定" not in m["段階"]:
                    seen.setdefault(int(m["年度"]), f'{m["大会"]} {m["段階"]}'.strip())
            rec["leagueHistory"] = [{"year": y, "name": n} for y, n in sorted(seen.items())]
            rec["eloHistory"] = {y: round(v) for y, v in sorted(hist.get(k, {}).items())}
        schools.append(rec)

    schools.sort(key=lambda s: (s["district"] or 99, -(s["elo"] or 0)))
    payload = {
        "generatedAt": date.today().isoformat(), "season": SEASON, "me": ME,
        "myDistrict": areas.get(ME, {}).get("area"),
        "nSchools": len(schools), "nMembers": sum(1 for s in schools if s["member"]),
        "nRated": sum(1 for s in schools if s["elo"] is not None),
        "nUnknownDistrict": sum(1 for s in schools if not s["district"]),
        "minGames": MIN_GAMES,
        # 誌面側が数の意味を取り違えないよう、単位を明記しておく
        "notes": {
            "summary": "トーナメント（選手権・総体・新人戦・関東の東京都予選）だけの通算。リーグ戦は含めない",
            "draws": "引き分けのうち PK で決着したものは pkw / pkl に分ける。d は PK の記載が無い引き分け",
            "games": "強さの点数の計算に使った試合数",
            "tournamentGames": "トーナメントの試合数（summary の合計と一致する）",
            "recentYears": f"直近3年（{RECENT[-1]}〜{RECENT[0]}年度）の年度別成績。"
                           "大会（トーナメント）だけで数える。best はその年度の最高到達点",
            "thisSeason": "今季の全試合。大会とリーグ戦を日付順に並べる。第5地区は全部、"
                          "他地区は直近5試合まで。まだ行われていない試合（二次予選の組み合わせ等）"
                          "は載せない。**今季の選手権は93%の試合に日付が入っていない**"
                          "（トーナメント表に日付欄が無い）ので、日付の無いものは末尾に回し、"
                          "そのなかで 大会→一次/二次→回戦の深さ の順に並べてある。"
                          "厳密な時系列として見せないこと",
            "commonOpponents": "武蔵丘との共通の対戦相手。相手ごとに、いちばん新しい試合どうしを"
                               "並べる。直接対戦の無い学校の力関係を間接的に見るためのもの。"
                               "第5地区は5件まで、他地区は3件まで",
            "leagueGames": "リーグ戦の試合数。トップチーム（無印とA）のみ。"
                           "地区によって取れている量が4倍ほど違うので、点数の動きやすさの目安に使う",
            "elo": "トーナメントの結果と、日付の取れたリーグ戦から計算。星取表（日付なし）は入らない",
            "eloRank": f"この名簿 {len(schools)} 校の中での順位。東京の全校ではない",
            "kana": "読みの出どころが無いため全校 null。五十音順で並べたい場合は誌面側で用意する",
            "leagueHistory": "第5地区のみ。星取表が残っている年だけなので、間の年が抜ける",
            "eloHistory": "第5地区のみ。年度末の値",
        },
        "districts": [{"no": d, "name": f"第{d}地区", "area": DISTRICTS[d],
                       "nSchools": sum(1 for s in schools if s["district"] == d)}
                      for d in sorted(DISTRICTS)],
        "schools": schools,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f'名簿 {payload["nSchools"]} 校（加盟校一覧 {payload["nMembers"]}・'
          f'点数あり {payload["nRated"]}・地区不明 {payload["nUnknownDistrict"]}）')
    for d in payload["districts"]:
        print(f'  第{d["no"]}地区 {d["nSchools"]:3}校')
    print(f'  地区不明   {payload["nUnknownDistrict"]:3}校')
    print(f'→ {OUT.relative_to(ROOT)}  {OUT.stat().st_size // 1024} KB')

    if args.district:
        print(f'\n=== 第{args.district}地区')
        for s in schools:
            if s["district"] != args.district:
                continue
            b = s["best"]["text"] if s["best"] else "—"
            lgn = s["league"]["name"] if s["league"] else "—"
            print(f'  {s["districtRank"]:2}. {s["key"]:14} 点数{s["elo"] or "—":>5} {s["games"]:3}試合'
                  f'  対武蔵丘 {s["vsMe"]["n"]}  {lgn[:18]:20} {b[:22]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
