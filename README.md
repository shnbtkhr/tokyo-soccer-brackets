# tokyo-soccer-brackets

東京都高体連サッカー専門部（tokyosoccer-u18.com）のトーナメント表 PDF から、対戦カード・スコア・勝者を読み取り、
Gemini Notebook（旧 NotebookLM）およびローカル AI（Claude Code / Antigravity）で高度な解析を行うデータ基盤＆スカウティングシステム。

## 💡 システムの設計思想：2層ハイブリッド AI アーキテクチャ

本プロジェクトは、役割の異なる 2 つの AI 環境を組み合わせることで高度なサッカー戦術分析を実現しています。

```
【入力素材（PDF/Web）】
       │
       ▼
【ローカル高度 AI エンジン】 (Claude Code / Antigravity)
 ├─ 幾何幾何学 PDF ベクトルパース (parse_bracket.py)
 ├─ 経年減衰付き Elo レーティング計算 (analyze_team.py)
 ├─ Tリーグ / 地区リーグ戦スクレイピング (fetch_leagues.py)
 └─ 勝ち上がり確率シミュレーション & Webダッシュボード生成 (build_scout_page.py)
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
【クラウド RAG 層】                          【インタラクティブ Web ダッシュボード】
 (Gemini Notebook / NotebookLM)               (out/scout/musashigaoka.html 等)
 └─ out/notebook/*.md 投入による自然言語 Q&A    └─ 指導者・選手向けリアルタイム分析・戦略閲覧
```

- **Gemini Notebook (NotebookLM) の役割**:
  `out/notebook/*.md` や CSV データを投入し、「◯◯高校の全大会の成績は？」といった対話的な自然言語検索・Q&Aを担当。
  ※環境内に **NotebookLM MCP / nlm CLI** が完備されており、`nlm source add` や `notebooklm-mcp` 経由で、生成された Markdown データが自動的にクラウド上の NotebookLM（「105th All Japan High School Soccer Tournament Tokyo Qualifiers」）へ直接同期・照会されます。
- **ローカル AI (Claude Code & Antigravity) の役割**:
  Gemini Notebook へのデータ投入前後の「より高度・複雑な解析と開発」を担当。
  - PDF の細い線分描画命令からの勝者・スコア復元
  - 学年交代（3年生引退）を考慮した Elo レーティング補正
  - トーナメント戦とリーグ戦データを複合したブロック優勝確率計算・スカウト HTML 自動生成
  - ※ローカルでの開発・高度解析は **Claude Code** が主導し、Claude Code の休眠中（API制限時）は **Antigravity** が作業と改善を引き継ぎます。


## 使い方


```powershell
uv sync
# 1. PDF を pdfs/ に置く（取得スクリプトは README 末尾）
# 2. 解析（out/json/ に1ファイル1JSON。--overlay で検証用画像も出す）
uv run python parse_bracket.py pdfs/sotai25_2jt.pdf --overlay out/overlay
# 3. 構造の点検（試合数=葉-1、スコアと勝者の矛盾、前後半の合計など）
uv run python check_structure.py
# 4. CSV と Notebook 用 Markdown を作る
uv run python build_outputs.py
```

`build_outputs.py` は CSV を書く前に、1つの表の中で成り立たない読み取りを取り消し
（得点が片側だけ・同じ得点の組が表の3割以上・勝者が全試合で同じ側）、空いたところを
高校サッカードットコムの結果（`data/koko_tokyo_matches.csv`）で埋める。
埋めた試合は備考に「結果は高校サッカードットコム」が付く。目視の訂正（`corrections.csv`）が
いちばん強く、自動の穴埋めがいちばん弱い。

Windows のコンソールでは `$env:PYTHONIOENCODING = "utf-8"` を付けないと日本語の出力が化けて見える（データは壊れていない）。

## 出力

| ファイル | 中身 |
|---|---|
| `out/matches.csv` | 1行 = 1試合（全大会・15,607試合／2004〜2026年度。うち結果が読めたもの 9,909） |
| `out/teams.csv` | 1行 = 1校 × 1大会段階。勝・PK勝・PK負・敗と戦績の並び |
| `out/notebook/{sotai,senshuken,shinjin,kanto}.md` | 大会系統ごとの試合一覧と学校別戦績 |
| `out/notebook/schools.md` | 学校ごとの全大会戦績。「◯◯高校の全大会の成績」に Gemini が答えられるようにするためのもの |
| `out/overlay/*.png` | 読み取った勝者・スコア・学校名を元の PDF に重ねた検証用画像 |

## 読み取りの仕組み（parse_bracket.py）

1. 描画命令の細い矩形を水平・垂直の線分に戻し、同じ直線上の断片をつなぐ。日付の列を区切る点線は先に取り除く
2. 「両端に枝が付き、途中から出口の線が出る線分」を試合線として探す。4辺が閉じた形（名前の囲み枠）は除外する
3. 向きは左→右・右→左・下→上・上→下の4通り。試合ごとに「決勝へ向かう方向」を正にした座標へ写してから読む
4. 勝者は、試合線のうち赤い部分がどちら側の枝につながっているかで決める
5. スコアは試合線の近くの数字を「段」にまとめて読む（本スコア・前半・後半・延長前半・延長後半）。PK は「0P4／0K5」「7PK8」「1PK1／1PK4」「0 P 3」「P4／K5」「2（5PK3）2」の書き方がある
6. 学校名は、枝の先の名前欄から、上下で隣り合う枝との中間までの文字を拾う。縦書きの均等割付にも対応する

## 既知の限界

- PDF にスコアが書かれていない試合が数件ある（赤線だけ、「＊」だけ、0-0 で PK の記載なし）。`check_structure.py` が6件を指摘し、うち5件は PDF 側の記載漏れ
- 自動で読めなかった1件は `corrections.csv` に目視で確かめた値を置いている
- 日付は 37% の試合で取れていない（列の見出しに日付が無い表がある）
- 学校名の名寄せ（`学校_正規化`）は機械的な寄せで、完全ではない。原文は `チームA` / `チームB` に残している
- 2022・2023年度の中支部予選は、ブロックの行き先（「中1」など）を読めていない
- 2026年度の選手権一次予選は開催中のスナップショット。赤線が未反映の試合はスコアから勝者を決めている（状態欄に記載）
- **古い年ほどスコアが薄い。** アーカイブに残っているのが「結果が入る前の版」だけのことがあるため。
  2004〜2010年度はスコアがほぼ無く（学校名も 2004〜2007年度は字形の情報が埋め込まれておらず読めない）、
  2011〜2016年度で3〜7割、2017年度以降は9割前後。年度ごとの埋まり具合は `out/matches.csv` を年度で数えると出る
- 高校サッカードットコムで埋められるのは 2014〜2021年度だけ（同サイトの大会一覧がそこまで）。
  2008〜2013年度の穴は埋め先がまだ無い
- 地区リーグの星取表のうち、2チームだけの順位決定戦は「期日／グループA／vs／グループB／会場」の
  1行もので、星取表とは別の読み方をしている。行き先が決まっていない（見出しが「〇位・〇位」の）
  ものと、2020年度の中止分は読み取れない

## 検証（2026-09-24）

- 高校サッカードットコムとトーナメント表の両方にスコアがある 3,208 試合で一致率 92.7%。
  食い違った 235 件のうち 201 件は3つのファイルに集中しており、中身を見るとすべて
  トーナメント表側の誤読（日付 8/16 を 1-6 と読む等）だった。この3ファイルは上記の
  取り消し規則が拾う
- 取り消し: スコア 370 件・勝者 272 件。穴埋め: 911 件（候補が割れたもの 0・赤線と矛盾したもの 0）
- 地区リーグの星取表と goalnote の両方にある 2024〜2026年度を突き合わせ、同じ試合 145 件が一致。
  食い違って見えた 12 件は、いずれも同じ2校の別チーム（BとC、DとE）どうしの試合だった
- 校名の表記ゆれ（附／付・大学／大・舍／舎 の書き分けだけが違うもの）15組 20 通りを
  `scout/school_aliases.json` に足した。学校の数は 658 → 643

## 検証（2026-09-11）

- 構造点検: 4,010試合で指摘6件（うち5件は PDF 側の記載漏れ）
- 前後半が書かれた56試合は、すべて合計が本スコアと一致
- 公開ニュースと突き合わせた決勝6件がすべて一致（総体2025・2026、選手権102回A/B・104回A、関東2024）
- オーバーレイ画像で支部予選・新人戦・選手権一次を目視確認

## PDF の取得

```bash
BASE=https://tokyosoccer-u18.com
mkdir -p pdfs && cd pdfs
for n in 22 23 24 25 26; do
  if [ "$n" = "22" ]; then SHIBU="22sotai_higashi12 22sotai_naka34 22sotai_minami56 22sotai_nishi78"
  else SHIBU="${n}sotai_12higashi ${n}sotai_34naka ${n}sotai_56minami ${n}sotai_78nishi"; fi
  for f in $SHIBU; do curl -fsS -O "$BASE/SOTAI$n/$f.pdf"; done
  curl -fsS -O "$BASE/SOTAI$n/sotai${n}_1jt.pdf"; curl -fsS -O "$BASE/SOTAI$n/sotai${n}_2jt.pdf"
  curl -fsS -O "$BASE/SEN$n/sen${n}_1j.pdf"
  if [ "$n" != "26" ]; then
    curl -fsS -O "$BASE/SEN$n/sen${n}_2j.pdf"
    for i in 1 2 3 4 5 6 7 8; do curl -fsS -O "$BASE/SINJ$n/sinj${n}_$i.pdf"; done
  fi
done
curl -fsS -O "$BASE/SINJ23/kanto2024.pdf"; curl -fsS -O "$BASE/SINJ24/2025kanto.pdf"
```

関東大会の2本はディレクトリ名と年度がずれている（kanto2024 は SINJ23 配下）。ファイル名の年が正しい。

## 過去の年度・リーグ戦の取得

現行サイトに残っているのは直近の数年ぶんだけなので、古い年はインターネットアーカイブと
高校サッカードットコムから集める。どれも取得したものをファイルに残し、二度目からは
取りに行かない。

```bash
uv run python fetch_archive.py          # 2004〜2021年度のトーナメント表 PDF（252本）
uv run python collect_koko_tokyo.py     # 東京都予選の結果（2014〜2021年度・6,507試合）
uv run python koko_fill.py              # 何件埋まるかを見るだけ（書き込まない）

uv run python fetch_league_pdfs.py      # T リーグの日程 PDF（2018〜2024年度・85本）
uv run python parse_league_pdfs.py      # → data/leagues/tleague_archive_matches.csv
uv run python collect_koko_tleague.py   # T リーグ 2014〜2020年度の順位表と全試合

uv run python parse_district_stars.py --list   # 地区リーグの星取表 2008〜2026年度（PDF 20本）
uv run python leagues.py --team 武蔵丘         # 5つの出どころを1つにそろえて見る

uv run python build_history.py          # 1校の歩みのページ（既定は武蔵丘）
uv run python check_pages.py            # 公開前の点検（out/site の全ページ）
```

リーグ戦は出どころが5つあり、同じ試合が重なって入っている。`leagues.py` が年度・対戦・
スコアで突き合わせ、**足し合わせずに「いちばん多く持っている出どころの数」に合わせる**
（2回戦制で同じスコアの試合が2つある場合を潰さないため）。日付のある行を先に採る。

星取表の PDF は早大学院サッカー部が公開しているもので、**同校が入っている組のぶんしか
残っていない**。武蔵丘のリーグ戦が 2013〜2015・2017・2020年度で抜けているのはそのため。
