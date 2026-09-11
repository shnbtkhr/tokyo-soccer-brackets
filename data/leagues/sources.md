# 東京都 高校サッカー 地区リーグの結果ページ一覧（2024〜2026年度）

ChatGPT の調査結果（docs/district_sources_chatgpt_20260911.md）を、Claude Code のサブエージェントが1件ずつ開いて確かめたもの（2026-09-11）。
全件は data/leagues/sources.csv。「Claude確認」の列が確かめた結果。

確かめた結果: 確認済み（ChatGPTの記載どおり） 47、新たに発見 45、未発見 12、ChatGPTの記載と違う 10、確認済み（Geminiの記載どおり） 2、Geminiの記載と違う 1

## 第1地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | リバーサイドユースリーグ 1部 | 確認済み | ChatGPTの記載と違う | https://junior-soccer.jp/sp/kanto/tokyo/league/match/49170 | https://junior-soccer.jp/sp/kanto/tokyo/league/order/49170 | 非公式集計サイト(junior-soccer.jp) | 1部のtidが49172ではなく49170だった。49171ページの下部に関連リーグとして1部・2部Bの順位が埋め込まれておりそこからtidを特定 |
| 2024 | リバーサイドユースリーグ 2部A | 確認済み | ChatGPTの記載と違う | https://junior-soccer.jp/sp/kanto/tokyo/league/match/49171 | https://junior-soccer.jp/sp/kanto/tokyo/league/order/49171 | 非公式集計サイト(junior-soccer.jp) | tid自体は一致。結果ページURLとして挙げていたriverside-league.com側が実は2026年度の現行ページだった |
| 2024 | リバーサイドユースリーグ 2部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://junior-soccer.jp/sp/kanto/tokyo/league/match/49172 | https://junior-soccer.jp/sp/kanto/tokyo/league/order/49172 | 非公式集計サイト(junior-soccer.jp) | tid49172=2部Bという対応そのものは正しかった |
| 2025 | リバーサイドユースリーグ 1部 | 未発見 | 未発見 |  |  | 不明 | 公式サイトに2025年度の過去ページ・アーカイブリンクが無い(topics.htmlは更新履歴のみで2026年度分しか無い)。junior-soccer.jpでも2025年度のtidへのリンクは見つからなかった |
| 2025 | リバーサイドユースリーグ 2部A | 未発見 | 未発見 |  |  | 不明 | 同上。2025年度のページ・tidともに未発見 |
| 2025 | リバーサイドユースリーグ 2部B | 未発見 | 未発見 |  |  | 不明 | 同上。2025年度のページ・tidともに未発見 |
| 2026 | リバーサイドユースリーグ 1部 | 確認済み | ChatGPTの記載と違う | https://riverside-league.com/schedule_division1.html | https://riverside-league.com/standing_division1.html | 公式サイト(独自HTML・cp932エンコード) | 年度がChatGPT記載の2024ではなく2026(現行シーズン)だった。2024/2025年度の過去ページはサイト内に存在しない |
| 2026 | リバーサイドユースリーグ 2部A | 一部確認 | ChatGPTの記載と違う | https://riverside-league.com/schedule_division2_group_a.html |  | 公式サイト(独自HTML・cp932エンコード) | 年度が2024ではなく2026だった(内容はChatGPT記載のURLと同一) |
| 2026 | リバーサイドユースリーグ 2部B | 一部確認 | ChatGPTの記載と違う | https://www.riverside-league.com/schedule_division2_group_b.html |  | 公式サイト(独自HTML・cp932エンコード) | 年度が2024ではなく2026だった(内容はChatGPT記載のURLと同一) |

## 第2地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | DUOリーグ グループA | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=15652 | https://www.goalnote.net/detail-standings.php?tid=15652 | goalnote | raw/web/goalnote_15652_detail.htmlのtitleで2024年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2024 | DUOリーグ グループB | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=15652 | https://www.goalnote.net/detail-standings.php?tid=15652 | goalnote | raw/web/goalnote_15652_detail.htmlのtitleで2024年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2024 | DUOリーグ グループC | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=15652 | https://www.goalnote.net/detail-standings.php?tid=15652 | goalnote | raw/web/goalnote_15652_detail.htmlのtitleで2024年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2024 | DUOリーグ グループD | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=15652 | https://www.goalnote.net/detail-standings.php?tid=15652 | goalnote | raw/web/goalnote_15652_detail.htmlのtitleで2024年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2024 | DUOリーグ グループE | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=15652 | https://www.goalnote.net/detail-standings.php?tid=15652 | goalnote | raw/web/goalnote_15652_detail.htmlのtitleで2024年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2025 | DUOリーグ グループA | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=16985 | https://www.goalnote.net/detail-standings.php?tid=16985 | goalnote | raw/web/goalnote_16985_detail.htmlのtitleで2025年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2025 | DUOリーグ グループB | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=16985 | https://www.goalnote.net/detail-standings.php?tid=16985 | goalnote | raw/web/goalnote_16985_detail.htmlのtitleで2025年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2025 | DUOリーグ グループC | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=16985 | https://www.goalnote.net/detail-standings.php?tid=16985 | goalnote | raw/web/goalnote_16985_detail.htmlのtitleで2025年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2025 | DUOリーグ グループD | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=16985 | https://www.goalnote.net/detail-standings.php?tid=16985 | goalnote | raw/web/goalnote_16985_detail.htmlのtitleで2025年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2025 | DUOリーグ グループE | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=16985 | https://www.goalnote.net/detail-standings.php?tid=16985 | goalnote | raw/web/goalnote_16985_detail.htmlのtitleで2025年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2026 | DUOリーグ グループA | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18409 | https://www.goalnote.net/detail-standings.php?tid=18409 | goalnote | raw/web/goalnote_18409_detail.htmlのtitleで2026年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2026 | DUOリーグ グループB | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18409 | https://www.goalnote.net/detail-standings.php?tid=18409 | goalnote | raw/web/goalnote_18409_detail.htmlのtitleで2026年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2026 | DUOリーグ グループC | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18409 | https://www.goalnote.net/detail-standings.php?tid=18409 | goalnote | raw/web/goalnote_18409_detail.htmlのtitleで2026年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2026 | DUOリーグ グループD | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18409 | https://www.goalnote.net/detail-standings.php?tid=18409 | goalnote | raw/web/goalnote_18409_detail.htmlのtitleで2026年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |
| 2026 | DUOリーグ グループE | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18409 | https://www.goalnote.net/detail-standings.php?tid=18409 | goalnote | raw/web/goalnote_18409_detail.htmlのtitleで2026年度DUOリーグと確認。detail-standings.phpはグループ単位の表5本のみで部の見出しなし。detail-schedule.phpにも |

## 第3地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | 第3地区ユースリーグ 1部 | 一部確認 | ChatGPTの記載と違う | https://www.juniorsoccer-news.com/post-1629009 | https://www.juniorsoccer-news.com/post-1629009 | 独自サイト | Gemini: post-1629009は2024年度の根拠URLとしてGeminiも提示。開いて確認したところ1部〜3部D全ブロックの最終順位が掲載されており有用だった |
| 2024 | 第3地区ユースリーグ 2部A | 確認済み | ChatGPTの記載と違う | https://junior-soccer.jp/kanto/tokyo/league/table/47948 | https://junior-soccer.jp/kanto/tokyo/league/order/47948 | 独自サイト | ChatGPTは47948を1部/3部A/3部Bの共通URLと記載していたが実際に開くと見出しは【2部A】2024年度第3地区リーグユースリーグ。3ブロック共通ではなく2部A専用ページだった |
| 2024 | 第3地区ユースリーグ 2部B | 一部確認 | 新たに発見 | https://www.juniorsoccer-news.com/post-1629009 | https://www.juniorsoccer-news.com/post-1629009 | 独自サイト | ChatGPTは2部Bに触れていない。最終順位のみ確認（試合ごとの結果ページ未特定） |
| 2024 | 第3地区ユースリーグ 3部A | 一部確認 | ChatGPTの記載と違う | https://www.juniorsoccer-news.com/post-1629009 | https://www.juniorsoccer-news.com/post-1629009 | 独自サイト | 【板橋有徳】2024年度は3部Aに所属し6位（7チーム中）。ChatGPTは47948を3部Aの結果URLとしていたが誤り（47948は2部A） |
| 2024 | 第3地区ユースリーグ 3部B | 一部確認 | ChatGPTの記載と違う | https://www.juniorsoccer-news.com/post-1629009 | https://www.juniorsoccer-news.com/post-1629009 | 独自サイト | ChatGPTは47948を3部Bの結果URLとしていたが誤り（47948は2部A）。最終順位のみ確認 |
| 2024 | 第3地区ユースリーグ 3部C | 確認済み | 確認済み（ChatGPTの記載どおり） | https://junior-soccer.jp/kanto/tokyo/league/table/50057 | https://junior-soccer.jp/kanto/tokyo/league/order/50057 | 独自サイト | ChatGPTの記載どおり【3部C】2024年度第3地区リーグの戦績表 |
| 2024 | 第3地区ユースリーグ 3部D | 確認済み | 確認済み（ChatGPTの記載どおり） | https://junior-soccer.jp/kanto/tokyo/league/table/47953 | https://junior-soccer.jp/kanto/tokyo/league/order/47953 | 独自サイト | ChatGPTの記載どおり【3部D】2024年度第3地区リーグの戦績表。都立板橋（有徳ではない別の都立高校）が5位で登場。板橋有徳と混同しないよう注意 |
| 2025 | 第3地区ユースリーグ 1部 | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | Gemini: 提示URL(seijogakko/club_news/29952)を確認したが日付不明の過去記事（2部優勝→1部昇格、感染症言及あり）で2025年度の記事ではない可能性が高い。2025年度情報は公式Wixのブログ記事から取得 |
| 2025 | 第3地区ユースリーグ 2部A | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（駿台学園C優勝／2位都立戸山）。試合ごとの結果ページ・順位表は未特定 |
| 2025 | 第3地区ユースリーグ 2部B | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（駿台学園D優勝／2位目白研心C）。試合ごとの結果ページ・順位表は未特定 |
| 2025 | 第3地区ユースリーグ 3部A | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（大東文化第一B優勝）。試合ごとの結果ページ・順位表は未特定 |
| 2025 | 第3地区ユースリーグ 3部B | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（Criacao Shinjuku優勝）。試合ごとの結果ページ・順位表は未特定 |
| 2025 | 第3地区ユースリーグ 3部C | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（目白研心D優勝）。試合ごとの結果ページ・順位表は未特定 |
| 2025 | 第3地区ユースリーグ 3部D | 一部確認 | 新たに発見 | https://kmnkzt1530.wixsite.com/youthleage/single-post/2025年度リーグ戦結果 |  | 独自サイト | 公式Wixのブログ記事に最終結果のみ掲載（都立大山優勝）。試合ごとの結果ページ・順位表は未特定 |
| 2026 | 第3地区ユースリーグ 1部 | 確認済み | 新たに発見 | https://ws.eniblo.com/YZezPNf8HYgIbzABs3/ | https://ws.eniblo.com/YZezPNf8HYgIbzABs3/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり |
| 2026 | 第3地区ユースリーグ 2部A | 確認済み | 新たに発見 | https://ws.eniblo.com/6TRkWT3l4eqWypXPEz/ | https://ws.eniblo.com/6TRkWT3l4eqWypXPEz/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり |
| 2026 | 第3地区ユースリーグ 2部B | 確認済み | 新たに発見 | https://ws.eniblo.com/WNlqrd5NRPqtv9vxKw/ | https://ws.eniblo.com/WNlqrd5NRPqtv9vxKw/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり |
| 2026 | 第3地区ユースリーグ 3部A | 確認済み | 新たに発見 | https://ws.eniblo.com/vXwlUaacWCy9NaZ3D2/ | https://ws.eniblo.com/vXwlUaacWCy9NaZ3D2/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり。都立板橋有徳はここではなく3部Dに所属 |
| 2026 | 第3地区ユースリーグ 3部B | 確認済み | 新たに発見 | https://ws.eniblo.com/6LfQ0YtO939PdhyS1P/ | https://ws.eniblo.com/6LfQ0YtO939PdhyS1P/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり。都立板橋（有徳ではない）が5位で在籍。 |
| 2026 | 第3地区ユースリーグ 3部C | 確認済み | 新たに発見 | https://ws.eniblo.com/4wp4WRHRPP2JDy9i58/ | https://ws.eniblo.com/4wp4WRHRPP2JDy9i58/ranks.html | 独自サイト | Gemini: metro.ed.jp/shinjuku-h/activities/2026/04/3_3_c_2.html を確認。2026/4/11都立新宿vs都立上野2-2、【第3地区ユースリーグ3部C第2節】と明記されており2026 |
| 2026 | 第3地区ユースリーグ 3部D | 確認済み | 新たに発見 | https://ws.eniblo.com/79SqSF8lncWz80vpmO/ | https://ws.eniblo.com/79SqSF8lncWz80vpmO/ranks.html | 独自サイト | 公式Wix(kmnkzt1530.wixsite.com/youthleage)からws.eniblo.comへのリンクをたどって実URLを特定。勝敗表(top)に加えranks.htmlに順位表あり。【最重要】都立板橋有徳の2026年度所 |

## 第4地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | 4地区ユースリーグ (Geminiの手がかり検証) | 一部確認 | Geminiの記載と違う |  |  | 学校ブログ/ニュース記事（結果・順位表ではない） | 年度誤り。Gemini: 記事タイトルは「2022年度 東京 第4地区ユースリーグ 1部優勝は東京実業高校C！最終結果掲載」であり2024年度の記事ではない（Geminiの年度表記が誤り）。本文末に「参照：東京都 4地区ユースリーグ HP」 |
| 2024 | 4地区ユースリーグ 1部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9154 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9154 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 1部 2024年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2024 | 4地区ユースリーグ 2部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9155 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9155 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 2部 2024年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2024 | 4地区ユースリーグ 3部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9156 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9156 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部A 2024年度」で一致。main.phpは順位表<table>1本（11チーム）。select.phpは<table>を使わないリスト形式で |
| 2024 | 4地区ユースリーグ 3部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9157 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9157 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部B 2024年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で |
| 2025 | 4地区ユースリーグ (Geminiの手がかり検証) | 一部確認 | 確認済み（Geminiの記載どおり） |  |  | 学校ブログ/ニュース記事（結果・順位表ではない） | Gemini: 二松学舎大学附属高校サッカー部の部活動ニュースページで、自チームの試合結果を随時ブログ的に掲載しているのみ（2021〜2026年度分が混在）。地区全体の結果・順位表は掲載していないため、Geminiの「校内ニュースで一部試合 |
| 2025 | 4地区ユースリーグ 1部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9466 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9466 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 1部 2025年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2025 | 4地区ユースリーグ 2部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9467 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9467 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 2部 2025年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2025 | 4地区ユースリーグ 3部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9468 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9468 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部A 2025年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で |
| 2025 | 4地区ユースリーグ 3部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9469 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9469 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部B 2025年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で |
| 2026 | 4地区ユースリーグ (Geminiの手がかり検証) | 一部確認 | 確認済み（Geminiの記載どおり） |  |  | 学校ブログ/ニュース記事（結果・順位表ではない） | Gemini: 二松学舎大学附属高校サッカー部の部活動ニュースページで、自チームの試合結果を随時ブログ的に掲載しているのみ（2021〜2026年度分が混在）。地区全体の結果・順位表は掲載していないため、Geminiの「校内ニュースで一部試合 |
| 2026 | 4地区ユースリーグ 1部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9761 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9761 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 1部 2026年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2026 | 4地区ユースリーグ 2部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9762 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9762 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 2部 2026年度」で一致。main.phpは順位表<table>1本（10チーム）。select.phpは<table>を使わないリスト形式で日 |
| 2026 | 4地区ユースリーグ 3部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9763 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9763 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部A 2026年度」で一致。main.phpは順位表<table>1本（11チーム）。select.phpは<table>を使わないリスト形式で |
| 2026 | 4地区ユースリーグ 3部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.kawakitanet.com/league_soccer/select.php?pref_cd=8&gameid=9764 | https://www.kawakitanet.com/league_soccer/main.php?pref_cd=8&gameid=9764 | 独自サイト(Kawakita) | main.php titleとselect.php titleがどちらも「4地区ユースリーグ 3部B 2026年度」で一致。main.phpは順位表<table>1本（11チーム）。select.phpは<table>を使わないリスト形式で |

## 第5地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | NSリーグ 1部 | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループA=1部 の対応を確認 |
| 2024 | NSリーグ 2部A | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループB=2部A の対応を確認 |
| 2024 | NSリーグ 2部B | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループC=2部B の対応を確認 |
| 2024 | NSリーグ 3部A | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループD=3部A の対応を確認 |
| 2024 | NSリーグ 3部B | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループE=3部B の対応を確認 |
| 2024 | NSリーグ 3部C | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=15685 | https://www.goalnote.net/detail-standings.php?tid=15685 | goalnote | raw/web/district/d5/goalnote_15685_detail.htmlのtitleで2024年度NSリーグと確認。detail-schedule.phpの見出し行から グループF=3部C の対応を確認 |
| 2025 | NSリーグ 1部 | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループA=1部 の対応を確認 |
| 2025 | NSリーグ 2部A | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループB=2部A の対応を確認 |
| 2025 | NSリーグ 2部B | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループC=2部B の対応を確認 |
| 2025 | NSリーグ 3部A | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループD=3部A の対応を確認 |
| 2025 | NSリーグ 3部B | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループE=3部B の対応を確認 |
| 2025 | NSリーグ 3部C | 確認済み | 新たに発見 | https://www.goalnote.net/detail-schedule.php?tid=16999 | https://www.goalnote.net/detail-standings.php?tid=16999 | goalnote | raw/web/district/d5/goalnote_16999_detail.htmlのtitleで2025年度NSリーグと確認。detail-schedule.phpの見出し行から グループF=3部C の対応を確認 |
| 2026 | NSリーグ 1部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループA=1部 の対応を確認 |
| 2026 | NSリーグ 2部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループB=2部A の対応を確認 |
| 2026 | NSリーグ 2部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループC=2部B の対応を確認 |
| 2026 | NSリーグ 3部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループD=3部A の対応を確認 |
| 2026 | NSリーグ 3部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループE=3部B の対応を確認 |
| 2026 | NSリーグ 3部C | 確認済み | 確認済み（ChatGPTの記載どおり） | https://www.goalnote.net/detail-schedule.php?tid=18597 | https://www.goalnote.net/detail-standings.php?tid=18597 | goalnote | raw/web/district/d5/goalnote_18597_detail.htmlのtitleで2026年度NSリーグと確認。detail-schedule.phpの見出し行から グループF=3部C の対応を確認 |

## 第6地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 1部 | 未発見 | 未発見 |  |  | 不明 | 根拠となるページ未発見 |
| 2024 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 2部A | 未発見 | 未発見 |  |  | 不明 | 根拠となるページ未発見 |
| 2024 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 2部B | 未発見 | 未発見 |  |  | 不明 | 根拠となるページ未発見 |
| 2024 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 3部A | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://www.metro.ed.jp/roka-h/activities/2025/01/clubentry_90.html |  | 独自サイト | ChatGPTが提示したclubentry_75(2024/07/16、開催中の速報)に加え、確定結果を記載したclubentry_90(2025/01/16公開)を新たに発見して補強した |
| 2024 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 3部B | 未発見 | 未発見 |  |  | 不明 | 根拠となるページ未発見 |
| 2025 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 不明（1部/2部/3部とも未特定） | 未発見 | ChatGPTの記載と違う |  |  | 不明 | Gemini: 提示のkoko-soccer.com/score/4208を開いて確認したところ見出しは「2025年度 令和7年度東京新人戦（新人選手権大会）第6地区」というノックアウト方式のトーナメント表であり、地区リーグ（総当たり戦の順 |
| 2026 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 1部 | 確認済み | 新たに発見 | https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv |  | Googleサイト（スプレッドシート埋め込み） | Gemini: koko-soccer.com/score/4208は本ブロックの根拠にはならない（2025年度の新人戦であり別大会。詳細は2025年度の行を参照） |
| 2026 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 2部A | 確認済み | 新たに発見 | https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv |  | Googleサイト（スプレッドシート埋め込み） | tokyo6league.com(公式ポータル)の各部ページが2026年度分としてGoogleサイト(sites.google.com/gakugei-hs.info/league6)へ誘導。埋め込みGoogleフォーム回答シートを見つけ、 |
| 2026 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 2部B | 確認済み | 新たに発見 | https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv |  | Googleサイト（スプレッドシート埋め込み） | tokyo6league.com(公式ポータル)の各部ページが2026年度分としてGoogleサイト(sites.google.com/gakugei-hs.info/league6)へ誘導。埋め込みGoogleフォーム回答シートを見つけ、 |
| 2026 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 3部A | 確認済み | 新たに発見 | https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv |  | Googleサイト（スプレッドシート埋め込み） | tokyo6league.com(公式ポータル)の各部ページが2026年度分としてGoogleサイト(sites.google.com/gakugei-hs.info/league6)へ誘導。埋め込みGoogleフォーム回答シートを見つけ、 |
| 2026 | 第6地区リーグU-18（通称・第6地区ユースリーグ） 3部B | 一部確認 | 新たに発見 | https://docs.google.com/spreadsheets/d/1vY7m-UeNZODVhNsxWN_Wn9Nt-7p4BdPc8PC64K5_qAo/gviz/tq?tqx=out:csv |  | Googleサイト（スプレッドシート埋め込み） | tokyo6league.com(公式ポータル)の各部ページが2026年度分としてGoogleサイト(sites.google.com/gakugei-hs.info/league6)へ誘導。埋め込みGoogleフォーム回答シートを見つけ、 |

## 第7地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | 第7地区ユースリーグ 1部 | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/archives/2024/Scores/1st-division | https://sites.google.com/view/youthleague-7/archives/2024/Scores/1st-division | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT/Geminiともに2024年度は「archives/2024」というトップページのURLのみで、部ごとのURLは未特定だった。トップページHTML内のサイトマップ情報(/view/youthleague-7/archives |
| 2024 | 第7地区ユースリーグ 2部A | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-a | https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-a | Googleサイト(静的テキスト・最終順位のみ) | 同上。トップページのサイトマップ情報から発見 |
| 2024 | 第7地区ユースリーグ 2部B | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-b | https://sites.google.com/view/youthleague-7/archives/2024/Scores/2nd-division-b | Googleサイト(静的テキスト・最終順位のみ) | 同上 |
| 2024 | 第7地区ユースリーグ 3部A | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-a | https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-a | Googleサイト(静的テキスト・最終順位のみ) | 同上 |
| 2024 | 第7地区ユースリーグ 3部B | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-b | https://sites.google.com/view/youthleague-7/archives/2024/Scores/3rd-division-b | Googleサイト(静的テキスト・最終順位のみ) | 同上 |
| 2025 | 第7地区ユースリーグ 1部 | 確認済み | 確認済み（ChatGPTの記載どおり） | https://sites.google.com/view/youthleague-7/archives/2025/Scores/1 | https://sites.google.com/view/youthleague-7/archives/2025/Scores/1 | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT記載のURLと一致。トップページのサイトマップでも同じパスを確認 |
| 2025 | 第7地区ユースリーグ 2部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://sites.google.com/view/youthleague-7/archives/2025/Scores/2a | https://sites.google.com/view/youthleague-7/archives/2025/Scores/2a | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT記載のURLと一致 |
| 2025 | 第7地区ユースリーグ 2部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://sites.google.com/view/youthleague-7/archives/2025/Scores/2b | https://sites.google.com/view/youthleague-7/archives/2025/Scores/2b | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT記載のURLと一致 |
| 2025 | 第7地区ユースリーグ 3部A | 確認済み | 確認済み（ChatGPTの記載どおり） | https://sites.google.com/view/youthleague-7/archives/2025/Scores/3a | https://sites.google.com/view/youthleague-7/archives/2025/Scores/3a | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT記載のURLと一致 |
| 2025 | 第7地区ユースリーグ 3部B | 確認済み | 確認済み（ChatGPTの記載どおり） | https://sites.google.com/view/youthleague-7/archives/2025/Scores/3b | https://sites.google.com/view/youthleague-7/archives/2025/Scores/3b | Googleサイト(静的テキスト・最終順位のみ) | ChatGPT記載のURLと一致 |
| 2026 | 第7地区ユースリーグ 1部 | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/scores/1st-division | https://docs.google.com/spreadsheets/d/e/2PACX-1vQVPxsdzQeHgNi4Bg02sDdW2DYT-H-jTe8Q3NttnomTX3wCBomCCepRUQPb_Szwlq6D9RkOnPZnznB2/pub?gid=513876327&single=true&output=csv | Googleサイト(スプレッドシート埋め込み・pubhtml/CSV取得可) | ChatGPTは2026年度について「1部・2部A・2部Bの存在は確認、年度別URLは未特定」としていた。トップページHTML内のiframe src属性から各ブロックのスプレッドシートID・URLを特定した |
| 2026 | 第7地区ユースリーグ 2部A | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/scores/2nd-division-a | https://docs.google.com/spreadsheets/d/e/2PACX-1vQDgq8t4JUX3Bwny3MQXdTAYZz1ya47lHunDLtuGBYg3R_y30tCEiB5YIfLLXnNPXTVL_FTW0FzIOC6/pub?gid=513876327&single=true&output=csv | Googleサイト(スプレッドシート埋め込み・pubhtml/CSV取得可) | ChatGPTは2026年度について「1部・2部A・2部Bの存在は確認、年度別URLは未特定」としていた。トップページHTML内のiframe src属性から各ブロックのスプレッドシートID・URLを特定した |
| 2026 | 第7地区ユースリーグ 2部B | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/scores/2nd-division-b | https://docs.google.com/spreadsheets/d/e/2PACX-1vSnG2t7r30I6bfEEBBGZRKWZo3ixiupiIdVCBR4RyKdn1TUhL8C6i2pEiNNaZ4yslVIUR5LF92BaFMS/pub?gid=513876327&single=true&output=csv | Googleサイト(スプレッドシート埋め込み・pubhtml/CSV取得可) | ChatGPTは2026年度について「1部・2部A・2部Bの存在は確認、年度別URLは未特定」としていた。トップページHTML内のiframe src属性から各ブロックのスプレッドシートID・URLを特定した |
| 2026 | 第7地区ユースリーグ 3部A | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/scores/3rd-division-a | https://docs.google.com/spreadsheets/d/e/2PACX-1vQx2FQdzhqIHTKWyZgvsblEu1BNjxh8D164OyzusdtyTV3U3iqZhlZdR2x2Iiu-FXllAvaRzSJW3AUI/pub?gid=513876327&single=true&output=csv | Googleサイト(スプレッドシート埋め込み・pubhtml/CSV取得可) | ChatGPTは2026年度について「1部・2部A・2部Bの存在は確認、年度別URLは未特定」としていた。トップページHTML内のiframe src属性から各ブロックのスプレッドシートID・URLを特定した |
| 2026 | 第7地区ユースリーグ 3部B | 確認済み | 新たに発見 | https://sites.google.com/view/youthleague-7/scores/3rd-division-b | https://docs.google.com/spreadsheets/d/e/2PACX-1vSz-Rl0rEvqrXiYZjx_kzGuJ4RUw2SNB336r2xVEhaeSiIrUKWdA3VM-XDAJIXoihKh_eDUxW1Hw5Nl/pub?gid=513876327&single=true&output=csv | Googleサイト(スプレッドシート埋め込み・pubhtml/CSV取得可) | ChatGPTは2026年度について「1部・2部A・2部Bの存在は確認、年度別URLは未特定」としていた。トップページHTML内のiframe src属性から各ブロックのスプレッドシートID・URLを特定した |

## 第8地区

| 年度 | リーグ・部 | 状態 | Claude確認 | 結果 | 順位表 | 形式 | メモ |
|---|---|---|---|---|---|---|---|
| 2024 | 8地区ユースリーグ 1部 | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://web.playerapp.tokyo/competition/14485 | https://web.playerapp.tokyo/competition/14485 | JS描画(React/api.ookami.me) | HTTP200/静的HTMLにはtitleとmeta以外の試合データなし・本文表示はJS必須 |
| 2024 | 8地区ユースリーグ 2部(ブロック不明) | 一部確認 | 新たに発見 | https://www.metro.ed.jp/higashimurayama-h/activities/club_9/index.html |  | HTML(ニュースブログ・沿革表あり・順位表なし) | ChatGPT・Geminiともに2024年2部は未記載。都立東村山高校自身のページで発見 |
| 2024 | 8地区ユースリーグ 3部A | 未発見 | 未発見 |  |  | 不明 | 検索したが該当ページ見つからず |
| 2024 | 8地区ユースリーグ 3部B | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://dendai-highschool-soccer.1web.jp/results.html |  | HTML(div構造のスコアカード・順位表なし) | HTTP200・charset=utf-8で正常に読める・bs4でdivクラスcaption/player/totalを抽出可能 |
| 2025 | 8地区ユースリーグ 1部 | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://sc.footballnavi.jp/tokaisugaofc/news_list.php?curY=1909&kn=10308&nowpg=2 |  | HTML(shift_jisのニュース一覧・順位表なし) | HTTP200・charset=shift_jisでのデコードが必要・見出し一覧のみでスコア本文なし |
| 2025 | 8地区ユースリーグ 2部(ブロック不明) | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://web.playerapp.tokyo/competition/16069 | https://web.playerapp.tokyo/competition/16069 | JS描画(React/api.ookami.me) | HTTP200・titleで年度部一致・本文はJS必須のため未確認 |
| 2025 | 8地区ユースリーグ 3部(Player!表記・ブロック不明) | 一部確認 | 確認済み（ChatGPTの記載どおり） | https://web.playerapp.tokyo/competition/16071 | https://web.playerapp.tokyo/competition/16071 | JS描画(React/api.ookami.me) | HTTP200・titleで年度部一致・本文はJS必須のため未確認 |
| 2025 | 8地区ユースリーグ 3部A | 一部確認 | 新たに発見 | https://dendai-highschool-soccer.1web.jp/results.html |  | HTML(div構造のスコアカード・順位表なし) | 見出しテキストで年度・部・ブロック完全一致 |
| 2025 | 8地区ユースリーグ 3部B | 未発見 | 未発見 |  |  | 不明 | 検索したが該当ページ見つからず |
| 2026 | 8地区ユースリーグ 1部 | 未発見 | 未発見 |  |  | 不明 | X(x.com)はcurlでHTTP200が返るがJS必須のSPAシェルのみで投稿本文は取得不可・WebFetchもHTTP402で拒否 |
| 2026 | 8地区ユースリーグ 2部A | 一部確認 | 新たに発見 | https://dendai-highschool-soccer.1web.jp/results.html |  | HTML(div構造のスコアカード・順位表なし) | 東村山の2026年度所属のクロス確認はChatGPT/Geminiになし。見出しテキストと東村山側の日付・スコアの整合を確認 |
| 2026 | 8地区ユースリーグ 2部B | 未発見 | 未発見 |  |  | 不明 | 検索したが該当ページ見つからず |
| 2026 | 8地区ユースリーグ 3部A | 未発見 | 未発見 |  |  | 不明 | 検索したが該当ページ見つからず |
