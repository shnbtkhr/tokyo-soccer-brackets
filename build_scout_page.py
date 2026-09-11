"""武蔵丘の視点のスカウティングページ（HTML）を作る。

入力:
- out/scout/musashigaoka_sen2026.json（analyze_team.py の出力）
- out/teams.csv（大会段階ごとの最終到達）
- scout/sen2026_block10.json（日程・会場・公開情報。手で管理する）
出力: out/scout/musashigaoka.html（scout_template.html にデータを埋め込んだもの）
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from analyze_team import win_prob
from build_outputs import normalize

ROOT = Path(__file__).parent


def main() -> int:
    a = json.loads((ROOT / "out/scout/musashigaoka_sen2026.json").read_text(encoding="utf-8"))
    manual = json.loads((ROOT / "scout/sen2026_block10.json").read_text(encoding="utf-8"))
    leagues_path = ROOT / "out/scout/leagues_2026.json"
    leagues = json.loads(leagues_path.read_text(encoding="utf-8")) if leagues_path.exists() else {}
    block = a["block"]
    stages = {k: [] for k in block}
    for t in csv.DictReader((ROOT / "out/teams.csv").open(encoding="utf-8-sig")):
        k = t["学校_正規化"]
        if k in stages:
            stages[k].append({"year": int(t["年度"]), "series": t["大会"], "stage": t["段階"] + (" " + t["地区・支部"] if t["地区・支部"] else ""), "reach": t["最終到達"], "record": f"{t['勝']}勝 {t['PK勝']}PK勝 {t['PK負']}PK負 {t['敗']}敗", "path": t["戦績"]})
    order = {"関東": 0, "総体": 1, "選手権": 2, "新人戦": 3}
    for k in stages:
        stages[k].sort(key=lambda s: (-s["year"], order[s["series"]], s["stage"]))

    elo = {k: a["teams"][k]["elo"] for k in block}
    me = a["me"]
    # 武蔵丘がその相手と当たる確率（当たるラウンドまで両方が勝ち上がる確率）
    alive = {k: True for k in block}
    for d in a["decided"]:
        for t in d["teams"]:
            if t != d["winner"]:
                alive[t] = False

    def p(x, y):
        return win_prob(elo[x], elo[y])

    b = block
    r1 = {b[0]: p(b[0], b[1]), b[1]: p(b[1], b[0]), b[2]: p(b[2], b[3]), b[3]: p(b[3], b[2])}
    for i in (4, 6):
        x, y = b[i], b[i + 1]
        r1[x], r1[y] = (1.0 if alive[x] else 0.0), (1.0 if alive[y] else 0.0)
        if alive[x] and alive[y]:
            r1[x], r1[y] = p(x, y), p(y, x)
    meet = {}
    my_r1 = r1[me]
    meet[b[2]] = 1.0  # 1回戦の相手
    for o in (b[0], b[1]):
        meet[o] = my_r1 * r1[o]
    my_r2 = my_r1 * sum(r1[o] * p(me, o) for o in (b[0], b[1]))
    r2_right = {}
    for o in b[4:]:
        other = [q for q in b[4:] if q != o and (b.index(q) // 2) != (b.index(o) // 2)]
        r2_right[o] = r1[o] * sum(r1[q] * p(o, q) for q in other)
    for o in b[4:]:
        meet[o] = my_r2 * r2_right[o]

    data = {
        "me": me,
        "block": block,
        "asOf": manual["asOf"],
        "blockLabel": manual["blockLabel"],
        "schedule": manual["schedule"],
        "slots": manual["slots"],
        "decided": manual["decided"],
        "teams": {
            k: {
                **{f: a["teams"][k][f] for f in ("elo", "eloRank", "eloHistory", "summary", "bySeries", "recent", "games", "names")},
                "display": manual["display"].get(k, k),
                "alive": alive[k],
                "blockWin": a["blockWinProb"].get(k, 0.0),
                "vsMe": a["comparisons"].get(k, {}).get("winProb"),
                "meetProb": round(meet.get(k, 0.0), 3) if k != me else None,
                "headToHead": a["comparisons"].get(k, {}).get("headToHead", []),
                "common": a["comparisons"].get(k, {}).get("common", []),
                "stages": stages[k],
                "info": manual["info"].get(k, {}),
                "leagues": leagues.get(k, []),
                "style": manual.get("style", {}).get(k),
            }
            for k in block
        },
        "nTeamsRated": a["nTeamsRated"],
        "ratingsTop": a["ratingsTop"][:30],
        "method": manual["method"],
        "styleNone": manual.get("styleNone", ""),
        "formNote": manual.get("formNote", []),
    }
    html = (ROOT / "scout/scout_template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    out = ROOT / "out/scout/musashigaoka.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    for k in block:
        print(k, "meet", data["teams"][k]["meetProb"], "vsMe", data["teams"][k]["vsMe"], "blockWin", data["teams"][k]["blockWin"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
