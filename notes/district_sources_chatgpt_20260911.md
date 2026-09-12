# ChatGPT による地区リーグ調査の結果（2026-09-11 受領・未検証）

ユーザーが ChatGPT に notes/deep_research_prompt_district_leagues.md 相当の依頼をして得た回答の記録。**URL はまだ確かめていない。**
Claude Code が1件ずつ開いて確かめ、結果は data/leagues/sources.csv に入れる（「Claude確認」の列）。Gemini Deep Research の回答も後で届く予定。

受け取った時点で気づいた怪しい点:
- 第1地区 2024 1部と2部Bに同じ順位表 URL（junior-soccer.jp …/table/49172）
- 第3地区 2024 1部・3部A・3部Bに同じ URL（…/table/47948）
- 第1地区の「2024年度」の結果ページ（riverside-league.com/schedule_division1.html など）は年度の入っていない現行ページ
- 第4地区 kawakitanet の gameid が年度ごとに連番（9154〜9157, 9466〜9469, 9761〜9764）。本当に開いて確かめたか要確認

## 第1地区 リバーサイドユースリーグ（公式 https://riverside-league.com/ ）
- 2024 1部: 結果 https://riverside-league.com/schedule_division1.html ／ 順位 https://junior-soccer.jp/sp/kanto/tokyo/league/table/49172 （確認済みと主張。1部10チーム規模）
- 2024 2部A: 結果 https://riverside-league.com/schedule_division2_group_a.html ／ 順位 https://junior-soccer.jp/sp/kanto/tokyo/league/order/49171 （9チーム規模）
- 2024 2部B: 結果 https://www.riverside-league.com/schedule_division2_group_b.html ／ 順位 https://junior-soccer.jp/sp/kanto/tokyo/league/table/49172 （10チーム規模）
- 2025 1部・2部A・2部B: 未発見
- 2026: 1部・2部A・2部B の存在は確認、年度別 URL は未特定（2026年度は30チーム規模）

## 第2地区 DUOリーグ（goalnote）
- 2024 https://www.goalnote.net/detail.php?tid=15652 ／ 2025 tid=16985 ／ 2026 tid=18409（3年度とも確認済みと主張）

## 第3地区 第3地区ユースリーグ（公式 Wix https://kmnkzt1530.wixsite.com/youthleage ）
- 2026 構成: 1部・2部A・2部B・3部A・3部B・3部C・3部D（7リーグ）。Wix から結果サイト https://ws.eniblo.com/ へのリンクあり。下層 URL は未特定
- 2024 1部・3部A・3部B: https://junior-soccer.jp/kanto/tokyo/league/table/47948 （3つとも同じ URL）
- 2024 3部C: https://junior-soccer.jp/kanto/tokyo/league/table/50057 ／ 2024 3部D: https://junior-soccer.jp/kanto/tokyo/league/table/47953
- 2024 1部は9チーム規模（成立学園C・東京成徳B・都立高島など）。3部C 7チーム、3部D 6チーム
- 2025: Wix の過去結果リンクは確認、各部の URL は未特定

## 第4地区 4地区ユースリーグ（Kawakita https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8 ）
結果 = select.php?gameid=N&pref_cd=8 ／ 順位 = main.php?gameid=N&pref_cd=8
- 2024: 1部 9154・2部 9155・3部A 9156・3部B 9157
- 2025: 1部 9466・2部 9467・3部A 9468・3部B 9469
- 2026: 1部 9761・2部 9762・3部A 9763・3部B 9764（2026: 1部10・2部10・3部A 11・3部B 11チーム）

## 第5地区 NSリーグ（goalnote）
- 2026 https://www.goalnote.net/detail.php?tid=18597 （確認済み）。2024・2025 は未発見

## 第6地区 第6地区ユースリーグ
- 一元的な結果サイトは未発見
- 2024 3部A の存在: https://www.metro.ed.jp/roka-h/activities/2024/07/clubentry_75.html
- 2026 1部の存在: https://bukatsunavi.com/page/komabagakuen/soccer/news_details/?id=6a3237fe12fca

## 第7地区 第7地区ユースリーグ（Google サイト https://sites.google.com/view/youthleague-7/ 、スプレッドシート埋め込み）
- 2025 各部: https://sites.google.com/view/youthleague-7/archives/2025/Scores/1 ・/2a ・/2b ・/3a ・/3b
- 2024 アーカイブ: https://sites.google.com/view/youthleague-7/archives/2024
- 2026: 1部・2部A・2部B・3部A・3部B（現行サイト。各ページ URL は未特定）

## 第8地区 8地区ユースリーグ
- 地区全体の公式結果サイトは未発見
- 2024 1部: Player! https://web.playerapp.tokyo/competition/14485 （確認済みと主張）
- 2024 3部B・2026 2部A: 東京電機大高 https://dendai-highschool-soccer.1web.jp/results.html （一部確認）
- 2025 1部: 東海大菅生 https://sc.footballnavi.jp/tokaisugaofc/news_list.php?curY=1909&kn=10308&nowpg=2 （一部確認）
- 2025 2部: Player! https://web.playerapp.tokyo/competition/16069 ／ 2025 3部: Player! https://web.playerapp.tokyo/competition/16071
- 2026 3部A・1部: 存在のみ

## ChatGPT の優先順位
第8 → 第3 → 第4 → 第6 → 第1 → 第2 → 第5 → 第7
