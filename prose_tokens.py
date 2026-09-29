"""本文に書く数字を、書き出すときにデータから埋める。

本文（scout/final_2026.json・scout/years.json）に点数や見込みを手で書くと、データを直すたびに
古くなる。実際、このサイトでは手書きの数字とデータが3度ずれた（2026-09-25・27・29）。
そこで本文には {{式}} を書き、ここで計算した値に置き換える。

式は Python の式として評価する（書くのは自分たちなので、外から来た文字列は通さない）。
使える名前:

  G(年度, 大会, 回戦, 学校="武蔵丘")  その試合。.me .opp .gap(相手−自分) .p(勝つ見込み%)
                                     .now_opp .rise(相手の今−当時) .gf .ga .opp_name
  YE(年度, 学校="武蔵丘")            その年度末の点数
  NOW(学校="武蔵丘")                 いまの点数
  RANK(学校="武蔵丘") / NRATED        いまの順位 / 順位をつけた学校の数
  PEAK / LOW                          武蔵丘の記録上の最高・最低（.elo .year .series .round）
  NGAMES                              武蔵丘の大会の試合数（記録のあるもの）
  UPN / UPRANK                        今季1次予選の90分決着の番狂わせの件数 / 学習院戦の順位
  BT                                  点数の当たり具合（.acc .n .logloss .base_acc）
  PW(自分, 相手)                       2つの点数から出した勝つ見込み（%の整数）
  CS / CSW                            武蔵丘が完封した試合 / うち90分で勝った試合（相手の当時の点数の高い順）
  UPW(始め, 終わり)                   その年度の範囲で、90分で格上に勝った試合（古い順）
  idx(一覧, 年度, 大会, 回戦)          一覧の中での順位（1から）
  above(一覧, 年度, 大会, 回戦)        一覧でその試合より上にある試合を文にしたもの
  Y(年度)                             その年度のまとめ（years.json）。.rankEnd .nRatedEnd .n .w .l .gf .ga など
  GAMES                               武蔵丘の全試合（古い順。.i は並び順）
  at(年度, 大会, 回戦)                その試合の並び順（GAMES の .i）
  rec(一覧)                           勝敗を「10勝2PK勝4敗」の形にしたもの
  avg(*xs)                            平均（整数に丸める）

式が解けないときは書き出しを止める。黙って空欄にすると、数字の抜けた文が公開されるため。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parent
ME = "武蔵丘"
TOKEN = re.compile(r"\{\{((?:(?!\}\}).)+)\}\}")


def _p(me: float, opp: float) -> int:
    return round(100 / (1 + 10 ** ((opp - me) / 400)))


class Context:
    def __init__(self) -> None:
        m = json.loads((ROOT / "out/scout/musashigaoka_sen2026.json").read_text(encoding="utf-8"))
        self.teams = m["teams"]
        self.nrated = m.get("nTeamsRated")
        sq = json.loads((ROOT / "out/scout/squad_2026.json").read_text(encoding="utf-8"))
        self.squad = {(t["year"], t["series"], g["round"]): g for t in sq["tournaments"] for g in t["games"]}
        up = json.loads((ROOT / "out/scout/upsets_2026.json").read_text(encoding="utf-8"))
        solo = [x for x in up["upsets"] if not x.get("pk")]
        self.upn = len(solo)
        self.uprank = next((i + 1 for i, x in enumerate(solo) if x.get("winner") == ME), None)
        self.bt = json.loads((ROOT / "out/scout/backtest.json").read_text(encoding="utf-8"))
        yp = ROOT / "out/scout/years.json"
        self.years = json.loads(yp.read_text(encoding="utf-8"))["years"] if yp.exists() else {}

    def team(self, name: str) -> dict:
        if name not in self.teams:
            raise KeyError(f"{name} の点数は musashigaoka_sen2026.json に無い")
        return self.teams[name]

    def game(self, year: int, series: str, rnd: str, school: str = ME) -> SimpleNamespace:
        gs = [g for g in self.team(school)["games"]
              if g["year"] == year and g["series"] == series and g["round"] == rnd]
        if len(gs) != 1:
            raise KeyError(f"{school} {year} {series} {rnd} の試合が {len(gs)} 件ある（1件のはず）")
        g = gs[0]
        sq = self.squad.get((year, series, rnd), {}) if school == ME else {}
        now_opp = sq.get("nowOpp")
        return SimpleNamespace(
            me=g["myElo"], opp=g["oppElo"], gap=g["oppElo"] - g["myElo"], p=_p(g["myElo"], g["oppElo"]),
            gf=g["gf"], ga=g["ga"], opp_name=g["opp"], now_opp=now_opp,
            rise=(now_opp - g["oppElo"]) if now_opp is not None else None)

    def namespace(self) -> dict:
        me = self.team(ME)
        gs = me["games"]

        def ns(g: dict, i: int = -1) -> SimpleNamespace:
            return SimpleNamespace(i=i, year=g["year"], series=g["series"], round=g["round"], opp=g["opp"],
                                   opp_elo=g["oppElo"], me=g["myElo"], gap=g["oppElo"] - g["myElo"],
                                   gf=g["gf"], ga=g["ga"], res=g["res"])
        cs = [ns(g) for g in sorted((g for g in gs if g["ga"] == 0), key=lambda g: -g["oppElo"])]
        csw = [g for g in cs if g.res == "勝"]
        games = [ns(g, i) for i, g in enumerate(gs)]

        def at(y: int, series: str, rnd: str) -> int:
            return next(g.i for g in games if (g.year, g.series, g.round) == (y, series, rnd))

        def rec(lst: list) -> str:
            c = {k: sum(1 for g in lst if g.res == k) for k in ("勝", "PK勝", "PK負", "負")}
            return (f"{c['勝']}勝" + (f"{c['PK勝']}PK勝" if c["PK勝"] else "")
                    + (f"{c['PK負']}PK負" if c["PK負"] else "") + f"{c['負']}敗")

        def idx(lst: list, y: int, series: str, rnd: str) -> int:
            return next(i + 1 for i, g in enumerate(lst) if (g.year, g.series, g.round) == (y, series, rnd))

        def above(lst: list, y: int, series: str, rnd: str) -> str:
            return "、".join(f"{g.year}年度の{g.opp}（{g.opp_elo}）との{g.gf}-{g.ga}"
                            for g in lst[:idx(lst, y, series, rnd) - 1])

        def upw(y0: int, y1: int) -> list:
            return [ns(g) for g in gs if y0 <= g["year"] <= y1 and g["res"] == "勝" and g["oppElo"] > g["myElo"]]
        hi = max(gs, key=lambda g: g["myElo"])
        lo = min(gs, key=lambda g: g["myElo"])
        a, b = self.bt["adopted"], self.bt["base"]
        return {
            "G": self.game,
            "YE": lambda y, school=ME: self.team(school)["eloHistory"][str(y)],
            "NOW": lambda school=ME: round(self.team(school)["elo"]),
            "RANK": lambda school=ME: self.team(school)["eloRank"],
            "NRATED": self.nrated,
            "PEAK": SimpleNamespace(elo=hi["myElo"], year=hi["year"], series=hi["series"], round=hi["round"]),
            "LOW": SimpleNamespace(elo=lo["myElo"], year=lo["year"], series=lo["series"], round=lo["round"]),
            "NGAMES": len(gs),
            "UPN": self.upn, "UPRANK": self.uprank,
            "BT": SimpleNamespace(acc=f"{a['acc']:.1%}", n=f"{a['nDec']:,}", logloss=a["logloss"],
                                  base_acc=f"{b['acc']:.1%}", years=self.bt["evalYears"]),
            "GAMES": games, "at": at, "rec": rec,
            "Y": lambda y: SimpleNamespace(**{k: v for k, v in self.years[str(y)].items() if not isinstance(v, (list, dict))}),
            "PW": _p, "CS": cs, "CSW": csw, "UPW": upw, "idx": idx, "above": above, "len": len,
            "avg": lambda *xs: round(sum(xs) / len(xs)),
            "abs": abs, "round": round, "max": max, "min": min, "range": range, "sum": sum,
        }


def resolve(obj, ns: dict | None = None):
    """obj の中の文字列すべての {{式}} を値に置き換えて返す。"""
    if ns is None:
        ns = Context().namespace()

    def one(s: str) -> str:
        def sub(m: re.Match) -> str:
            expr = m.group(1).strip()
            try:
                v = eval(expr, {"__builtins__": {}, **ns})  # noqa: S307 — 自分たちで書いた本文だけを通す
            except Exception as e:  # 1つでも解けなければ止める
                raise ValueError(f"本文の {{{{{expr}}}}} を計算できない: {e}") from e
            if v is None:
                raise ValueError(f"本文の {{{{{expr}}}}} が空になった")
            return f"{v:+d}" if expr.startswith("+") else str(v)
        return TOKEN.sub(sub, s)

    if isinstance(obj, dict):
        # _note などの「_」で始まる欄は説明書きなので、式を解かない
        return {k: (v if k.startswith("_") else resolve(v, ns)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve(v, ns) for v in obj]
    if isinstance(obj, str):
        m = TOKEN.fullmatch(obj)
        if m and not m.group(1).strip().startswith("+"):
            # 値だけの欄（表の数値など）は、数のまま返す
            v = eval(m.group(1).strip(), {"__builtins__": {}, **ns})  # noqa: S307
            if isinstance(v, (int, float)):
                return v
        return one(obj)
    return obj
