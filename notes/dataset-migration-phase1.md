# データセット移行 段階1 — 実装の仕様

決定：Vault の審議 `Projects/99_vault-decisions/soccer-dataset-layer.md`（2026-09-30 採用）
表の定義（契約書）：`C:\Users\shnbt\dev\obsidian-vault\Datasets\tokyo-hs-soccer\SCHEMA.md` — **実装の前に全部読むこと。食い違ったら SCHEMA.md が正しい**

## 目的

いまのデータ（このリポジトリの `out/matches.csv`・`data/leagues/*.csv`・校名の寄せ・地区・訂正）を、SCHEMA.md の9つの表に**情報を落とさずに**変換し、Vault に書き出す。

**段階1ではサイトの組み立ては切り替えない。** 既存のスクリプトの動作・出力は1バイトも変えない（例外は下の「既存コードへの変更」の1点だけ）。

## 作るもの（このリポジトリの中）

| ファイル | 役割 |
|---|---|
| `dataset/__init__.py` | 空でよい |
| `dataset/paths.py` | 書き出し先。環境変数 `SOCCER_DATASET_DIR`、無ければ `C:\Users\shnbt\dev\obsidian-vault\Datasets\tokyo-hs-soccer` |
| `dataset/export.py` | 旧データ → 9表。`uv run python -m dataset.export` で Vault に書き出す |
| `dataset/check.py` | SCHEMA.md の「検査」6項目。`uv run python -m dataset.check`。1つでも引っかかれば終了コード1 |
| `dataset/legacy.py` | 9表 → 旧来の形（アダプタ）。下の往復テストで使う。段階2でサイトの組み立てがこれを使う |
| `tests/test_dataset_roundtrip.py` | 下の受け入れテスト T1〜T6。`uv run python -m pytest tests/test_dataset_roundtrip.py`（pytest が無ければ `uv add --dev pytest`） |

## 入力

- 大会：`out/matches.csv`（`build_outputs.py` の出力。15,118行）。列の意味は `build_outputs.py` を読む
- リーグ戦：`leagues.py` の `load_all()` が読む5経路（`district_stars_matches.csv`＝星取表、`district_matches.csv`＝goalnote、`tleague_matches.csv`＝Tリーグ公式、`tleague_archive_matches.csv`・`tleague_history_matches.csv`＝Tリーグ過去、`prince_kanto1_2026_matches.csv`＝プリンス）。**実施が「済」でない行も `status=予定` として取り込む**
- 順位表：`data/leagues/district_standings.csv`・`tleague_standings.csv`・`tleague_history_standings.csv`・`prince_kanto1_2026_standings.csv`
- 校名：`build_outputs.normalize()`・`scout/school_aliases.json`・`out/scout/member_areas.json`（地区・市区町村・都立/私立）
- 訂正：`corrections.csv`（列 `file,team1,team2,field,value,reason`。`file` は出典 PDF のファイル名）
- PDF のハッシュ：`pdfs/` と `pdfs/archive/` にあるファイルの sha256（無いものは空欄）

## 変換の決まり（SCHEMA.md に無い実装上の決まり）

1. **学校**：`legacy_key` は、旧コードがキーにしている文字列そのもの。大会は `チームA_正規化`/`チームB_正規化`、リーグ戦は `ホーム学校`/`アウェイ学校`。**寄せ方を変えない**（段階1で学校を統合・分割すると、数字が変わったのが移行の誤りか修正か区別できなくなる）。`school_id` は、`legacy_key` を「初めて現れた年度、キーの文字列」の順に並べて `S0001` から振る。**`schools.csv` が既にあれば、そこにある対応を使い、新しいキーにだけ続きの番号を振る**（2回目以降の書き出しで ID が変わらないように）
2. **学校の区分**：`member_areas.json` にあれば `kind`・`district`・`city`・`official_name` をそこから。無ければ、大会に一度でも出ていれば `不明`、リーグ戦だけに出る名前は `クラブ`（`東京ヴェルディ`・`FC`・`SC` を含むなど）か `不明`。迷うものは `不明` にし、`note` に「区分未確認」と書く
3. **校名の書き方**：大会の `チームA`/`チームB`、リーグの `ホーム`/`アウェイ`（原文）、`school_aliases.json` の `exact_map` のキーを、すべて `school_names.csv` に入れる。同じ書き方が2つの学校を指す場合は検査で止める（起きたら、実装を止めて報告する）
4. **チーム**：区分が空欄のトップチームは `A`。大会の試合は常に `A`
5. **大会**：`段階` から「第N回」を `edition` に分け、SCHEMA.md の表の `stage` に置き換える（`一次予選`→`1次予選`、`一次トーナメント`→`都1次トーナメント` など）。リーグは、`series` に正式なリーグ名（`T1`〜`T5` の行は `series=Tリーグ`・`stage=T5`）、`stage` に部（`load_all` の `区分`。末尾の「ブロック」は除く）
6. **試合（大会）**：`area`＝`地区・支部`、`block`＝`ブロック`（先頭の `→` は外す）、`page`＝`ページ`、`round`＝`ラウンド`、`match_no`＝`試合番号`、`date_text`＝`日付`（1日に決まれば `date` も）、`halves`＝`前後半`、`note`＝`備考`。`status`・`winner_basis` は SCHEMA.md の対応表どおり。延長は `スコア` に「(延長)」があれば1
7. **試合（リーグ）**：`load_all()` が残した行が1試合。**残さなかった重なりの行も捨てず**、同じ試合の `match_sources`（`role=重複`）にする。どの行がどの試合の重なりかは、`load_all()` の `key()` と同じ鍵で決める。`round` は節
8. **出典**：`出典PDF`・リーグの `出典` の文字列1つにつき1行。`feed` は経路。`備考` に「結果は高校サッカードットコム」とある大会の試合は、`高校サッカードットコム` の出典を `role=補完` で付ける（大会ごとに1つの出典でよい）
9. **同じ表の別版の重なり**：`build_outputs.drop_version_duplicates()` が落とした行を `match_sources`（`role=重複`）に残す。そのために下の「既存コードへの変更」を入れる
10. **訂正**：`corrections.csv` の各行を、`出典PDF` のファイル名と2校から `match_id` に直す。見つからない行があれば、実装を止めて報告する
11. **書き出し**：UTF-8（BOM なし）・LF・主キーの昇順。`_staging/` は作らない（段階1は直接書く）

## 既存コードへの変更（1点だけ）

`build_outputs.py` の `drop_version_duplicates()` が、落とした行を `out/dropped_duplicates.csv`（`build_outputs` が書く `matches.csv` と同じ列）に書き出すようにする。**`matches.csv` の中身は変えない。** 変更後に `uv run python build_outputs.py` を回し、`out/matches.csv` が変更前とバイト単位で同じことを確かめる（変更前に `out/matches.csv` を別名で控えておく）。

## 受け入れテスト（すべて通るまで完了としない）

| テスト | 内容 |
|---|---|
| T1 | `dataset.check` の6項目がすべて通る |
| T2 | 大会の往復：`legacy.tournament_rows()` が返す行と `out/matches.csv` の行が、行数・並び・次の列で一致する：`年度,大会,段階,地区・支部,ブロック,ページ,ラウンド,日付,試合番号,チームA,チームB,スコア,得点A,得点B,PK_A,PK_B,前後半,勝者,備考,チームA_正規化,チームB_正規化,出典PDF`。`状態` は `analyze_team.played()` の真偽が一致すること |
| T3 | リーグの往復：`legacy.league_rows()` が `leagues.load_all()` と完全に一致する（同じ並びの dict のリスト） |
| T4 | 点数の往復：`legacy.feed_rows(feed)` が返す行（goalnote・Tリーグ公式・プリンス）を元の CSV の代わりに読ませて `rating.run(load_matches(), rating.ADOPTED)` を回すと、`elo`・`hist`・`n_games` が元と完全に一致する。`rating.py` を書き換えずに、テストの中で `rating.league_games` の読み込み先を差し替えて確かめる |
| T5 | 順位表の往復：4つの順位表 CSV の行（主催者の値）が `standings.csv` から復元できる |
| T6 | 冪等：`dataset.export` を2回続けて回すと、2回目の書き出しで Vault のファイルが1バイトも変わらない |

## 進め方の決まり

- **機械的な変換は、全件を一度に処理してから結果をまとめて報告する。ファイル1件ずつ確認を求めない。**
- ただし次のときは、そこで止めて報告する（判断はこちらで行う）：同じ書き方が2つの学校を指す／訂正の行が試合に対応しない／テストがどうしても通らず、SCHEMA.md の変更が要りそうなとき
- **git のコミットはしない**（Vault もこのリポジトリも）。Vault には `Datasets/tokyo-hs-soccer/` の下の9つの CSV だけを書く。`SCHEMA.md`・`README.md` は触らない
- Windows。Python は `uv run python`、`PYTHONIOENCODING=utf-8` を付ける。`python` 単体はストアのスタブなので使わない

## 報告すること

- 9表それぞれの行数
- T1〜T6 の結果
- 変換で迷って決めたこと（区分が「不明」になった学校の数、クラブと判定したもの、など）
- 変更・作成したファイルの一覧
