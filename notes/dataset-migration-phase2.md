# データセット移行 段階2 — サイトの組み立てを Vault の表から読む

前提：段階1が完了している（`dataset/`・`tests/test_dataset_roundtrip.py` 6本合格。コミット 99c2cd9）
表の定義：`C:\Users\shnbt\dev\obsidian-vault\Datasets\tokyo-hs-soccer\SCHEMA.md`

## 目的

サイトの組み立て（集計・点数・ページ）が、このリポジトリの `out/matches.csv`・`data/leagues/*.csv` などではなく、**Vault の9つの表から読む**ようにする。

**合格の条件はただ1つ：切り替えの前と後で、組み立ての出力が完全に一致すること。** 段階2では数字を1つも変えない。

## やり方

既存の集計スクリプトを書き換えて新しい表を直接読ませるのではなく、**Vault の表から旧来の形のファイルを作り（実体化）、読み込み先だけを差し替える**。集計の中身には手を入れない。旧来の形をやめて表を直接読む書き換えは、この後の段階で1本ずつ行う。

1. `dataset/materialize.py`：Vault の表から、旧来の形のファイルを `out/legacy/` に書き出す（`uv run python -m dataset.materialize`）。`legacy.py` の関数を使う
2. `dataset/source.py`：読み込み先を決める関数を1つだけ置く。例：`path("out/matches.csv")` → 環境変数 `SOCCER_SOURCE` が `legacy` ならそのまま、それ以外（既定）なら `out/legacy/matches.csv`
3. 下の「読む側」のスクリプトの、旧データを開く箇所を `source.path(...)` 経由に変える。**それ以外の行は変えない**

## 読む側（差し替える）と書く側（触らない）

読む側：`analyze_team.py`・`rating.py`・`rating_backtest.py`・`leagues.py`・`connections.py`・`build_index.py`・`build_leagues.py`・`build_seeds.py`・`build_squad.py`・`build_years.py`・`build_scout_page.py`・`league_coverage.py`（`out/scout/member_areas.json`・`out/teams.csv` を読む箇所も含む。漏れが無いか、自分で grep して確かめること）

書く側（取得・読み取り）：`collect_*.py`・`parse_*.py`・`fetch_*.py`・`merge_sources.py`・`discover_junior_soccer.py`・`build_outputs.py`・`koko_fill.py`。**段階2では触らない。** これらは引き続き `data/`・`out/` に書き、`dataset.export` が Vault に移す（取り込みの流れを Vault の `_staging/` 経由に直すのは段階4）

## 実体化するファイル

読む側が開いているファイルすべて。少なくとも：`out/matches.csv`・`out/teams.csv`（`build_outputs.build_teams` で作れる）・`data/leagues/` の試合と順位表の各 CSV・`out/scout/member_areas.json`。

**読む側が使う列は、すべて元と同じ値で復元すること。** 使っていない列は空欄でよい。どの列を使っているかは、読む側のコードを読んで決める。**Vault の表に無い情報が要る場合（例：会場・時刻・地区名など）は、そこで止めて報告する**（表に列を足すかどうかはこちらで決める）。

## 合格の確かめ方

`scripts/compare_build.sh`（または .py）を作り、次を自動で行う。

1. `SOCCER_SOURCE=legacy` で組み立て一式を回し、出力を `out/_cmp/legacy/` に控える
2. 既定（Vault から）で同じ一式を回し、`out/_cmp/dataset/` に控える
3. 2つを比べ、違いがあれば一覧を出して終了コード1

組み立て一式（README の順）：`rating_backtest.py`・`analyze_team.py`・`league_coverage.py`・`build_squad.py`・`build_upsets.py`・`build_index.py`・`build_seeds.py`・`build_second.py`・`draw_second.py`・`build_generations.py`・`build_years.py`・`build_history.py`・`build_site.py --links local`。`build_outputs.py`・`fetch_leagues.py` は回さない（書く側のため）。

比べるもの：`out/scout/*.json`・`notes/rating_backtest.md`・`out/site/*.html`。HTML は埋め込みデータ（`const D = ...`）を JSON として比べる。日時など実行ごとに変わる値があれば、その値だけを除いて比べ、何を除いたかを報告に書く。

**時間のかかる `rating_backtest.py` は、1回目に同じ結果になることを確かめたら、2回目以降の比較では省いてよい。**

## 進め方の決まり

- **機械的な差し替えは、全件を一度に行ってから結果をまとめて報告する。ファイル1件ずつ確認を求めない。**
- 止めて報告するのは、次のときだけ：Vault の表に無い情報が要る／比較の違いが、実体化の誤りでは説明できない
- **git のコミットはしない。Vault は読むだけ**（表を書き換えない。`dataset.export` も回さない）
- 公開用の `docs/` には書かない
- Windows。`uv run python`、`PYTHONIOENCODING=utf-8`。`python` 単体は使わない

## 報告すること

- 変更したスクリプトと、それぞれ何箇所変えたか
- 実体化したファイルと、それぞれ元と一致した列・空欄にした列
- 比較の結果（一致したファイル数・違いがあればその内容）。比較から除いた値
- 作成・変更したファイルの一覧
