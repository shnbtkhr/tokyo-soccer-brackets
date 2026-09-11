# Gemini Deep Research による地区リーグ調査の結果（2026-09-11 受領・未検証）

ユーザーが docs/deep_research_prompt_district_leagues.md を Gemini Deep Research に渡して得た回答の記録。ChatGPT の回答（docs/district_sources_chatgpt_20260911.md）より URL は少ない。
Claude Code のサブエージェントが ChatGPT の候補を確かめている最中に届いたため、Gemini にしか無い手がかりだけを追加で確かめさせた。

## ChatGPT との違い

- 第4地区: Gemini は「集約ポータル未発見」。ChatGPT は Kawakita（kawakitanet.com）の gameid を12件挙げている
- 第3地区: どちらも地区全体の結果ページは未特定。ChatGPT は公式 Wix と ws.eniblo.com を挙げている
- 第1・7地区: Gemini はトップページだけで、年度・部ごとの URL は無い
- 第5地区: どちらも 2026年度 tid=18597 のみ

## Gemini にしか無い手がかり

- 第3地区: https://www.juniorsoccer-news.com/post-1629009 （2024）・https://www.seijogakko.ed.jp/club_news/29952/ （2025）・https://www.metro.ed.jp/shinjuku-h/activities/2026/04/3_3_c_2.html （2026）
- 第4地区: https://www.juniorsoccer-news.com/post-1152626 （2024）・https://www.nishogakusha-highschool.ac.jp/sports009/ （2025・2026）
- 第6地区: https://koko-soccer.com/score/4208 （2024〜2026 の根拠として挙げている）。参加校として駒場東邦・日大三B・駒澤大高E・野津田
- 第8地区: https://x.com/fussa_fc

## 受け取った CSV（原文のまま）

```
地区,リーグ名,年度,部・ブロック,結果ページのURL,順位表ページのURL,形式,goalnote_tid,チームの区別,状態,根拠のURL,メモ
第1地区,リバーサイドユースリーグ,2024,1部,https://riverside-league.com/schedule_division1.html,https://riverside-league.com/schedule_division1.html,独自サイト,,A・B・Cの表記あり,確認済み,https://riverside-league.com/,1部の日程結果および順位掲載
第1地区,リバーサイドユースリーグ,2025,1部,https://riverside-league.com/schedule_division1.html,https://riverside-league.com/schedule_division1.html,独自サイト,,A・B・Cの表記あり,一部確認,https://riverside-league.com/,サイト内更新順次反映
第1地区,リバーサイドユースリーグ,2026,1部,https://riverside-league.com/schedule_division1.html,https://riverside-league.com/schedule_division1.html,独自サイト,,A・B・Cの表記あり,一部確認,https://riverside-league.com/,サイト内更新順次反映
第2地区,DUOリーグ,2024,全部,https://www.goalnote.net/detail-schedule.php?tid=15652,https://www.goalnote.net/detail-standings.php?tid=15652,goalnote,15652,A・B・Cの表記あり,確認済み,https://www.goalnote.net/detail-schedule.php?tid=15652,Goalnote公式ポータル
第2地区,DUOリーグ,2025,全部,https://www.goalnote.net/detail-schedule.php?tid=16985,https://www.goalnote.net/detail-standings.php?tid=16985,goalnote,16985,A・B・Cの表記あり,確認済み,https://www.goalnote.net/detail-schedule.php?tid=16985,Goalnote公式ポータル
第2地区,DUOリーグ,2026,全部,https://www.goalnote.net/detail-schedule.php?tid=18409,https://www.goalnote.net/detail-standings.php?tid=18409,goalnote,18409,A・B・Cの表記あり,確認済み,https://www.goalnote.net/detail-schedule.php?tid=18409,Goalnote公式ポータル
第3地区,第3地区ユースリーグ,2024,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.juniorsoccer-news.com/post-1629009,専用ポータル未発見。各校ブログ・報道で結果確認
第3地区,第3地区ユースリーグ,2025,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.seijogakko.ed.jp/club_news/29952/,各校サッカー部Web等で一部結果掲載
第3地区,第3地区ユースリーグ,2026,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.metro.ed.jp/shinjuku-h/activities/2026/04/3_3_c_2.html,都立新宿高校・成城高校等の活動報告で一部掲載
第4地区,第4地区ユースリーグ,2024,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.juniorsoccer-news.com/post-1152626,集約ポータル未発見
第4地区,第4地区ユースリーグ,2025,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.nishogakusha-highschool.ac.jp/sports009/,二松学舎大附等の校内ニュースで一部掲載
第4地区,第4地区ユースリーグ,2026,1部・2部・3部,,,不明,,A・B・Cの表記あり,一部確認,https://www.nishogakusha-highschool.ac.jp/sports009/,校内ニュースで一部試合結果のみ確認
第5地区,NSリーグ,2024,全部,,,不明,,不明,未発見,,専用Goalnote TID未特定
第5地区,NSリーグ,2025,全部,,,不明,,不明,未発見,,専用Goalnote TID未特定
第5地区,NSリーグ,2026,全部,https://www.goalnote.net/detail-schedule.php?tid=18597,https://www.goalnote.net/detail-standings.php?tid=18597,goalnote,18597,A・B・Cの表記あり,確認済み,https://www.goalnote.net/detail-schedule.php?tid=18597,Goalnote公式ポータル
第6地区,第6地区ユースリーグ,2024,1部・2部,,,不明,,A・B・Cの表記あり,一部確認,https://koko-soccer.com/score/4208,集約ポータル未発見
第6地区,第6地区ユースリーグ,2025,1部・2部,,,不明,,A・B・Cの表記あり,一部確認,https://koko-soccer.com/score/4208,各校速報サイト等で一部掲載
第6地区,第6地区ユースリーグ,2026,1部・2部,,,不明,,A・B・Cの表記あり,一部確認,https://koko-soccer.com/score/4208,一部結果のみ確認
第7地区,第7地区ユースリーグ,2024,全部,https://sites.google.com/view/youthleague-7/,https://sites.google.com/view/youthleague-7/,Googleサイト（スプレッドシート埋め込み）,,A・B・Cの表記あり,確認済み,https://sites.google.com/view/youthleague-7/,Google sites上のスプレッドシートにて結果・順位管理
第7地区,第7地区ユースリーグ,2025,全部,https://sites.google.com/view/youthleague-7/,https://sites.google.com/view/youthleague-7/,Googleサイト（スプレッドシート埋め込み）,,A・B・Cの表記あり,確認済み,https://sites.google.com/view/youthleague-7/,Google sites上のスプレッドシートにて結果・順位管理
第7地区,第7地区ユースリーグ,2026,全部,https://sites.google.com/view/youthleague-7/,https://sites.google.com/view/youthleague-7/,Googleサイト（スプレッドシート埋め込み）,,A・B・Cの表記あり,確認済み,https://sites.google.com/view/youthleague-7/,Google sites上のスプレッドシートにて結果・順位管理
第8地区,8地区ユースリーグ,2024,2部・3部等,,,不明,,A・B・Cの表記あり,SNSのみで確認,https://x.com/fussa_fc,X（@fussa_fc）や各校公式ページにて言及あり・専用集約URL未発見
第8地区,8地区ユースリーグ,2025,2部・3部等,,,不明,,A・B・Cの表記あり,SNSのみで確認,https://x.com/fussa_fc,X（@fussa_fc）や各校公式ページにて言及あり・専用集約URL未発見
第8地区,8地区ユースリーグ,2026,2部・3部等,,,不明,,A・B・Cの表記あり,一部確認,https://x.com/fussa_fc,都立東村山高校HP等で言及あり・全体集約URL未発見
```

## Gemini の概要文（要点）

- 第3地区: 1部・2部（A・B）・3部（A〜D）の多層構造。成立学園C・東京成徳B・都立高島・都立板橋有徳などが所属。地区全体の専用サイトや goalnote は一般公開されていない
- 第4地区: 1部・2部・3部A・3部B。東京実業・青稜・東海大高輪台・二松学舎大附などが参加。全ブロックを網羅するページは未確認
- 第6地区: 1部・2部など。駒場東邦・日大三B・駒澤大高E・野津田などが所属
- 第8地区: 1部・2部A/B・3部A/B など。都立東村山・福生FC などが参加。全体の星取表・順位表の URL は未発見
