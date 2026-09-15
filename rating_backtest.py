"""強さの点数の設定を、過去の大会の試合を当てる力で比べる。

各設定で点数を最初から計算し、評価年度の大会の試合について「試合の前の点数から出した勝つ見込み」と結果を比べる。
- 対数損失（log loss）: 小さいほど良い。見込みを外したときに大きく罰する。基準は「いつも50%」の 0.693
- ブライアスコア: 小さいほど良い。基準は 0.25
- 的中率: PK・引き分けを除いた試合で、見込みの高い側が勝った割合
結果は notes/rating_backtest.md に書く。
"""

from __future__ import annotations

import csv
import math
from itertools import product
from pathlib import Path

import rating
from rating import Config

ROOT = Path(__file__).parent


def score(preds: list, min_games: int = 0) -> dict:
    ps = [(p, s) for p, s, na, nb in preds if min(na, nb) >= min_games]
    if not ps:
        return {"n": 0}
    eps = 1e-6
    ll = -sum(s * math.log(max(p, eps)) + (1 - s) * math.log(max(1 - p, eps)) for p, s in ps) / len(ps)
    br = sum((p - s) ** 2 for p, s in ps) / len(ps)
    dec = [(p, s) for p, s in ps if s in (0.0, 1.0) and p != 0.5]
    acc = sum((p > 0.5) == (s == 1.0) for p, s in dec) / len(dec) if dec else 0
    return {"n": len(ps), "logloss": round(ll, 4), "brier": round(br, 4), "acc": round(acc, 3), "nDec": len(dec)}


BINS = [(0, .05), (.05, .1), (.1, .2), (.2, .35), (.35, .5)]


def calibration(preds: list) -> list:
    """見込みの低い側から見て、見込みの帯ごとに「見込みの平均」と「実際に勝った割合」（PK・引き分けは半分）を並べる。"""
    ps = [(1 - p, 1 - s) if p > 0.5 else (p, s) for p, s, *_ in preds]
    out = []
    for lo, hi in BINS:
        sub = [(p, s) for p, s in ps if lo <= p < hi]
        if sub:
            out.append({"band": f"{lo:.0%}〜{hi:.0%}", "n": len(sub), "pred": sum(p for p, _ in sub) / len(sub), "actual": sum(s for _, s in sub) / len(sub)})
    return out


def calib_rows(old: list, new: list) -> list:
    rows = []
    for lo, hi in BINS:
        band = f"{lo:.0%}〜{hi:.0%}"
        o = next((c for c in old if c["band"] == band), None)
        n = next((c for c in new if c["band"] == band), None)
        cell = lambda c: (str(c["n"]), f"{c['pred']:.1%} → {c['actual']:.1%}") if c else ("―", "―")  # noqa: E731
        rows.append(f"| {band} | {' | '.join(cell(o))} | {' | '.join(cell(n))} |")
    return rows


def main() -> int:
    rows = list(csv.DictReader((ROOT / "out/matches.csv").open(encoding="utf-8-sig")))
    for r in rows:
        r["年度"] = int(r["年度"])
    configs = [Config(k=32, carry=0.75, league_weight=0.0, name="今の方式（大会だけ・K32・持ち越し0.75）")]
    # 1) 大会だけで K と持ち越しを変える
    for k, carry in product((32, 40, 56, 72, 88), (0.75, 0.9, 1.0)):
        if (k, carry) != (32, 0.75):
            configs.append(Config(k=k, carry=carry, name=f"大会だけ・K{k}・持ち越し{carry}"))
    # 2) リーグ戦をそのまま入れる（控えもクラブも1500点から）
    for tl, di, nm in ((True, True, "全リーグ"), (True, False, "Tリーグ＋プリンス"), (False, True, "地区リーグだけ")):
        configs.append(Config(k=32, carry=0.75, league_weight=1.0, use_tleague=tl, use_district=di, use_prince=tl, name=f"そのまま入れる・K32・持ち越し0.75・{nm}・重み1.0"))
    # 3) 直し方を入れてリーグ戦を足す（控えの最初の点数・仮の期間10試合・階層で最初の点数）
    for k, lw in product((56, 72, 88), (0.1, 0.25, 0.5)):
        configs.append(Config(k=k, carry=1.0, league_weight=lw, reserve_prior=True, provisional=10, level_prior=True, name=f"直して入れる・K{k}・持ち越し1.0・全リーグ・重み{lw}"))
    for k in (56, 72, 88):
        configs.append(Config(k=k, carry=1.0, league_weight=0.25, use_district=False, reserve_prior=True, provisional=10, level_prior=True, name=f"直して入れる・K{k}・持ち越し1.0・Tリーグ＋プリンス・重み0.25"))
    results = []
    for cfg in configs:
        res = {"cfg": cfg}
        for label, yrs in (("2025-26", (2025, 2026)), ("2024", (2024,))):
            o = rating.run([dict(r) for r in rows], cfg, eval_years=yrs)
            res[label] = score(o["preds"])
            if label == "2025-26":
                res["calib"] = calibration(o["preds"])
            res[label + "_5"] = score(o["preds"], 5)
        results.append(res)
        print(f"{cfg.name:52s} 25-26 ll={res['2025-26']['logloss']} acc={res['2025-26']['acc']} | 2024 ll={res['2024']['logloss']}")
    write_md(results)
    return 0


def write_md(results: list) -> None:
    base = results[0]
    ranked = sorted(results[1:], key=lambda r: r["2025-26"]["logloss"])
    best = ranked[0]
    b = base["2025-26"]
    md = ["# 強さの点数の設定を比べた結果（rating_backtest.py）", "",
          "各設定で2022年度から点数を計算し直し、**大会の試合の前の点数から出した勝つ見込み**が結果とどれだけ合っていたかを比べた。",
          "リーグ戦（Tリーグ・プリンス関東・地区リーグ）は点数の計算には使うが、当たり具合は大会の試合だけで測る（サイトで使うのは大会の見込みのため）。", "",
          "- 対数損失: 小さいほど良い（いつも50%と言った場合は 0.693）",
          "- ブライアスコア: 小さいほど良い（いつも50%なら 0.25）",
          "- 的中率: PK戦・引き分けを除き、見込みの高い側が勝った割合",
          "- 設定は2025・2026年度の大会で選び、2024年度の大会でも同じ傾向か確かめた（選んだ年度だけにたまたま合った設定を避けるため）", "",
          f"## 結論", "",
          f"- 今の方式: 対数損失 {b['logloss']}・ブライア {b['brier']}・的中率 {b['acc']:.1%}（2025・26年度 {b['n']} 試合）",
          f"- 一番良かった設定: **{best['cfg'].name}** → 対数損失 {best['2025-26']['logloss']}・ブライア {best['2025-26']['brier']}・的中率 {best['2025-26']['acc']:.1%}",
          f"- 2024年度の大会: 今の方式 {base['2024']['logloss']} → この設定 {best['2024']['logloss']}", "",
          "## 見込みと実際（2025・26年度の大会。見込みの低い側から見た値）", "",
          "対数損失だけでは「見込みが極端すぎないか」は分からないので、見込みの帯ごとに実際に勝った割合を比べた。",
          "旧方式は見込みを控えめに出しすぎていた（29%と言った試合で実際は7%）。今の方式は見込みと実際がよく合う。", "",
          "| 見込みの帯 | 旧方式: 試合数 | 旧方式: 見込み → 実際 | 今の方式: 試合数 | 今の方式: 見込み → 実際 |", "|---|---|---|---|---|",
          *calib_rows(base["calib"], best["calib"]),
          "",
          "## わかったこと", "",
          "1. **リーグ戦をそのまま入れると、大会の当たり具合は悪くなった**（地区リーグは特に）。地区リーグには強い学校の控え（B・C）やクラブが多く、"
          "最初はみな1500点から始まる。実は強い控えに負け続けた学校は点数を大きく下げ（例: 芝 −147）、弱いリーグで勝ち続けた学校は上がりすぎた。"
          "点数は奪い合いなので、その影響がリーグに出ていない学校（堀越など）にも広がり、学校の点数のばらつきが縮んだ",
          "2. 直し方: ①控えは、その学校の A の点数から B は100点・C は200点…引いた値で始める ②試合数10未満のチームとの試合では、学校の点数を動かさない（仮の期間）"
          " ③リーグで初めて出てくるチームは、リーグの階層（プリンス +300 … T5 ±0 … 地区3部 −150）で最初の点数を決める。リーグの重みも大会の半分にした",
          "3. **K を大きく・年度をまたいでも点数を平均へ戻さない（持ち越し1.0）ほうが当たった**。高校サッカーでは、学校ごとの強さ（指導・部員の集まり方）が年度をまたいでも続くためとみられる",
          "4. K と持ち越しは、比べた範囲の端（K88・持ち越し1.0）が一番良かった。K をさらに大きくするとまだ少し良くなる可能性があるが、1試合で点数が大きく動きすぎるので、ここで止めた",
          "5. 採用した設定（rating.py の ADOPTED）: K88・持ち越し1.0・全リーグを重み0.5で入れる・控えの最初の点数・仮の期間10試合・階層で最初の点数", "",
          "## 全設定（2025・26年度の対数損失の小さい順）", "",
          "| 設定 | 対数損失 25-26 | ブライア 25-26 | 的中率 25-26 | 対数損失 2024 | 対数損失 25-26（両校とも5試合以上） |", "|---|---|---|---|---|---|"]
    for r in [base] + ranked:
        a, c, d = r["2025-26"], r["2024"], r["2025-26_5"]
        md.append(f"| {r['cfg'].name} | {a['logloss']} | {a['brier']} | {a['acc']:.1%} | {c['logloss']} | {d.get('logloss', '')}（{d['n']}試合） |")
    (Path(__file__).parent / "notes/rating_backtest.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
