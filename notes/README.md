# notes/ — 人と AI が読む文書

`docs/` は **GitHub Pages の公開フォルダ**（`out/site/` の HTML をコピーする場所）で、更新のたびに中身を全部消して入れ替える。
そのため、**文書（.md）は `docs/` に置かない。この `notes/` に置く。**

- 2026-09-12 に Pages を設定したとき、`docs/` にあった文書8本が更新手順の「`docs/*` を全消去」で消えた（コミット 69767e9）。Git の履歴から `notes/` に戻したのがこのフォルダ
- 更新手順の正本: `C:\Users\shnbt\.copilot\session-state\a6b0cbd0-.../claude-code-update-flow.md`

## 置いてあるもの

| ファイル | 中身 |
|---|---|
| `strength_rating.md` | 強さの点数（Elo）の設計。AI 向けの仕様 |
| `name_merge_proposal.md` | 学校名の表記ゆれ統合の一覧（ユーザー承認済み・反映済み） |
| `draw_analysis_senshuken.md` | 選手権 東京大会の組み合わせの分析。1次予選免除の決まり（推定） |
| `district_collector_spec.md` | 地区リーグの読み取り部品の決まり |
| `district_sources_chatgpt_20260911.md` | ChatGPT の地区リーグ調査（未検証の記録） |
| `district_sources_gemini_20260911.md` | Gemini Deep Research の地区リーグ調査（未検証の記録） |
| `deep_research_prompt_district_leagues.md` | 地区リーグ探しの依頼文 |
| `research_prompt_exemption.md` | 1次予選免除の決まりを調べる依頼文 |

確かめた結果のデータは `data/`（`data/leagues/sources.csv`・`data/seeds/`・`data/connections/`）にある。
