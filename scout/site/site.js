/* 武蔵丘スカウト — 全ページ共通の部品と、ページ種別ごとの組み立て。
   D はページごとに build_site.py が埋め込む。D.page = "hub" | "team" | "self" */
const $ = (sel) => document.querySelector(sel);
const SVGNS = "http://www.w3.org/2000/svg";
function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v; else if (k === "html") e.innerHTML = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
function s(tag, attrs = {}, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
  if (text != null) e.textContent = text;
  return e;
}
const pct = (p, d = 0) => (p == null ? "―" : (p * 100).toFixed(d) + "%");
const B = D.brief;
const NEXT_ROUND = { "1回戦": "2回戦へ", "2回戦": "ブロック決勝へ", "ブロック決勝": "2次予選へ" };
const nameOf = (k) => (B[k] ? B[k].display : k);
const hrefOf = (slug) => D.links[slug];
const linkAttrs = (slug) => ({ href: hrefOf(slug), target: D.linkTarget || null, rel: D.linkTarget ? "noopener" : null });
const eloLink = () => h("a", { href: hrefOf("index") + "#elo", target: D.linkTarget || null, rel: D.linkTarget ? "noopener" : null }, "点数のしくみ");
const tip = h("div", { class: "tip", hidden: "" });
document.body.append(tip);
function showTip(ev, html) { tip.innerHTML = html; tip.hidden = false; const x = Math.min(ev.clientX + 16, innerWidth - tip.offsetWidth - 8); tip.style.left = x + "px"; tip.style.top = ev.clientY + 16 + "px"; }
function hideTip() { tip.hidden = true; }

/* ---------- 共通: ヘッダー ---------- */
function renderTopbar() {
  const nav = h("nav", { class: "pages", "aria-label": "ページ" });
  for (const g of D.nav) {
    const grp = h("div", { class: "grp" }, g.label ? h("span", { class: "lab" }, g.label) : null);
    for (const it of g.items) {
      grp.append(h("a", { ...linkAttrs(it.slug), class: [it.cls || "", it.out ? "out" : ""].join(" ").trim() || null, "aria-current": it.slug === D.slug ? "page" : null, title: it.title || null }, it.label));
    }
    nav.append(grp);
  }
  document.body.prepend(h("header", { class: "topbar" }, h("div", { class: "in" },
    h("a", { class: "brand", ...linkAttrs("index") }, h("i", { class: "dot", "aria-hidden": "true" }), h("b", {}, "武蔵丘スカウト"), h("span", {}, "SENSHUKEN 2026")),
    nav)));
}

/* ---------- 共通: 左のサイドパネル（PC。ページの地図と、このページの見出し） ---------- */
const slugKey = Object.fromEntries(Object.entries(D.keyToSlug || {}).map(([k, v]) => [v, k]));
function renderSidenav() {
  const side = h("aside", { class: "sidenav", "aria-label": "サイトの地図" });
  side.append(h("a", { class: "sn-brand", ...linkAttrs("index") }, h("i", { class: "dot", "aria-hidden": "true" }), h("span", {}, h("b", {}, "武蔵丘スカウト"), h("small", {}, "選手権 2026 東京都予選"))));
  const item = (it) => {
    const k = slugKey[it.slug], br = k && B[k];
    const meta = it.slug === "seeds" ? null : br && k !== D.me && br.alive === false ? "敗退" : br && k !== D.me && br.vsMe != null ? pct(br.vsMe) : null;
    return h("li", {}, h("a", { ...linkAttrs(it.slug), class: "sn-link" + (it.cls === "me" ? " me" : ""), "aria-current": it.slug === D.slug ? "page" : null, title: meta && it.slug !== "seeds" ? `武蔵丘が勝つ見込み ${meta}` : null },
      h("span", { class: "sn-t" }, it.label), meta ? h("span", { class: "sn-m num" }, meta) : null));
  };
  const tree = h("nav", { class: "sn-tree" });
  // 振り分けは phase で決める。ラベルの文字列で判定すると、文言を変えたときに
  // 片方が空のグループになって展開できなくなる（2026-09-24）
  const first = D.nav.filter((g) => g.phase !== 2), second = D.nav.filter((g) => g.phase === 2).map((g) => ({ ...g, label: "" }));
  const grp = (title, sub, groups) => h("details", { class: "sn-grp", open: "" }, h("summary", {}, h("span", {}, title), sub ? h("small", {}, sub) : null),
    h("ul", {}, groups.flatMap((g) => g.label
      ? [h("li", { class: "sn-round" }, h("span", { class: "sn-lab" }, g.label === "決勝" ? "ブロック決勝" : g.label), h("ul", {}, g.items.map(item)))]
      : g.items.map(item))));
  tree.append(grp("1次予選", D.blockLabel ? D.blockLabel.replace(/^.*?(【\d+】).*$/, "$1ブロック") : "", first));
  if (second.some((g) => g.items.length)) tree.append(grp("2次予選", "10/3〜", second));
  side.append(tree);
  const toc = h("nav", { class: "sn-toc", "aria-label": "このページの見出し" }, h("div", { class: "sn-h" }, "このページ"), h("ol", {}));
  side.append(toc, h("div", { class: "sn-foot" }, h("span", {}, "強さの点数は目安です。"), h("a", { href: hrefOf("index") + "#elo", target: D.linkTarget || null }, "点数のしくみ")));
  document.body.prepend(side);
  document.body.classList.add("has-side");
}
function fillToc() {
  const ol = document.querySelector(".sn-toc ol");
  if (!ol) return;
  const heads = [...document.querySelectorAll("#app h2")].filter((e) => !e.closest("details.seed, .kpis, details.more"));
  heads.forEach((e, i) => { if (!e.id) e.id = `h-${i}`; });
  const links = heads.map((e) => {
    const li = h("li", {}, h("a", { href: `#${e.id}`, onclick: (ev) => { ev.preventDefault(); e.scrollIntoView({ behavior: "smooth", block: "start" }); history.replaceState(null, "", `#${e.id}`); } }, e.textContent.trim()));
    if (D.page === "seeds" && e.closest("#each")) {
      li.append(h("details", { class: "sn-sub" }, h("summary", {}, `${D.seeds.seeds.length}校を表示`),
        h("ol", {}, D.seeds.seeds.map((t) => h("li", {}, h("a", { href: `#s-${t.rank}`, onclick: () => openSeed(t.rank) }, h("span", { class: "num sn-rk" }, t.rank), t.display))))));
    }
    ol.append(li);
    return [e, li];
  });
  if (!links.length) { ol.closest("nav").hidden = true; return; }
  let tick = false;
  const spy = () => {
    tick = false;
    let cur = links[0];
    for (const pair of links) if (pair[0].getBoundingClientRect().top < 140) cur = pair;
    links.forEach(([, li]) => li.classList.toggle("on", li === cur[1]));
  };
  addEventListener("scroll", () => { if (!tick) { tick = true; requestAnimationFrame(spy); } }, { passive: true });
  spy();
}

/* ---------- 共通: トーナメント表 ---------- */
function bracketSVG() {
  const svg = s("svg", { class: "bracket", viewBox: "0 0 380 400", role: "group", "aria-label": `${D.blockLabel}のトーナメント表` });
  const K = D.block, Y = (i) => 32 + i * 46, X0 = 142, X1 = 188, X2 = 252, X3 = 318, X4 = 366;
  const decided = {};
  for (const d of D.decided) { decided[d.a] = d; decided[d.b] = d; }
  const sch = Object.fromEntries(D.schedule.filter((m) => m.no).map((m) => [m.no, m]));
  const line = (x1, y1, x2, y2, cls) => svg.append(s("line", { x1, y1, x2, y2, class: "ln" + (cls ? " " + cls : "") }));
  K.forEach((k, i) => {
    const t = B[k], y = Y(i), slug = D.keyToSlug[k];
    const g = s(slug ? "a" : "g", slug ? { href: hrefOf(slug), target: D.linkTarget || null, class: (k === D.me ? "me" : "") + (!t.alive ? " out" : ""), "aria-label": `${t.display}のページを開く` } : { class: "out" });
    g.append(s("rect", { class: "hit", x: 0, y: y - 21, width: X0 - 6, height: 42, rx: 6 }));
    g.append(s("text", { class: "slot", x: 8, y: y + 4 }, String(D.slots[k])));
    g.append(s("text", { class: "nm", x: 32, y: y - 2 }, t.display));
    g.append(s("text", { class: "pct", x: 32, y: y + 14 }, t.alive ? `山を勝ち抜く ${pct(t.blockWin)}` : `${t.outcome ? t.outcome.round : ""}で敗退`));
    svg.append(g);
    line(X0, y, X1, y, decided[k] && decided[k].winner === k ? "win" : k === D.me ? "path" : "");
  });
  const mids = [];
  [[0, 1, 31], [2, 3, 32], [4, 5, null], [6, 7, null]].forEach(([a, b, no]) => {
    const ya = Y(a), yb = Y(b), ym = (ya + yb) / 2; mids.push(ym);
    const d = decided[K[a]];
    const wa = d && d.winner === K[a], wb = d && d.winner === K[b];
    const meA = K[a] === D.me, meB = K[b] === D.me;
    line(X1, ya, X1, ym, wa ? "win" : meA ? "path" : ""); line(X1, ym, X1, yb, wb ? "win" : meB ? "path" : ""); line(X1, ym, X2, ym, wa || wb ? "win" : meA || meB ? "path" : "");
    if (no && !d) {
      svg.append(s("text", { class: "mno", x: X1 + 7, y: ym - 7 }, `【${no}】`));
      svg.append(s("text", { class: "mlab", x: X1 + 7, y: ym + 15 }, `${sch[no].date} ${sch[no].time}`));
    } else if (d) {
      svg.append(s("text", { class: "score", x: X1 + 7, y: ym - 7 }, d.score));
      svg.append(s("text", { class: "mlab", x: X1 + 7, y: ym + 15 }, "終了"));
    }
  });
  const mids2 = [];
  [[0, 1, 149], [2, 3, 150]].forEach(([a, b, no]) => {
    const ya = mids[a], yb = mids[b], ym = (ya + yb) / 2; mids2.push(ym);
    const mine = no === 149;
    line(X2, ya, X2, yb, ""); line(X2, ym, X3, ym, mine ? "path" : "");
    if (mine) line(X2, yb, X2, ym, "path");
    svg.append(s("text", { class: "mno", x: X2 + 7, y: ym - 7 }, `【${no}】`));
    svg.append(s("text", { class: "mlab", x: X2 + 7, y: ym + 15 }, `${sch[no].date} ${sch[no].time}`));
  });
  const yf = (mids2[0] + mids2[1]) / 2;
  line(X3, mids2[0], X3, mids2[1], ""); line(X3, mids2[0], X3, yf, "path"); line(X3, yf, X4, yf, "path");
  svg.append(s("text", { class: "mno", x: X3 + 7, y: yf - 24 }, "【208】"));
  svg.append(s("text", { class: "mlab", x: X3 + 7, y: yf - 9 }, sch[208].date));
  svg.append(s("text", { class: "mlab", x: X3 + 7, y: yf + 17 }, sch[208].time));
  line(X4, yf, X4, 24, "path");
  svg.append(s("text", { class: "dest", x: X4, y: 16, "text-anchor": "end" }, "→ 2次予選【10】"));
  return svg;
}

function scheduleList() {
  const box = h("div", { class: "sched" });
  for (const m of D.schedule) {
    const nm = (k) => (B[k] ? B[k].display : k);
    box.append(h("div", { class: "r" + (m.a === D.me || m.b === D.me ? " mine" : "") },
      h("span", { class: "m" }, m.no ? `【${m.no}】` : m.round),
      m.no && !m.winner ? h("span", { class: "dt" }, `${m.date}(${m.dow}) ${m.time}`) : h("span", { class: "done" }, `${m.score} 終了`),
      h("span", {}, `${nm(m.a)} 対 ${nm(m.b)}`, m.venue ? h("span", { class: "where" }, m.venue + (m.timeNote ? `・${m.timeNote}` : "")) : null)));
  }
  return box;
}

/* ---------- 共通: 強さの点数の推移（折れ線） ---------- */
function eloChart(series) {
  // series: [{name, hist, color, dash}]  2本まで。線の端に名前を直接書き、色だけに頼らない
  const W = 620, H = 260, L = 44, R = 110, TOP = 18, BOT = 34;
  const years = ["2022", "2023", "2024", "2025", "2026"];
  const vals = series.flatMap((sr) => years.map((y) => sr.hist[y]).filter((v) => v != null));
  const lo = Math.floor((Math.min(...vals, 1500) - 30) / 50) * 50, hi = Math.ceil((Math.max(...vals, 1500) + 30) / 50) * 50;
  const x = (i) => L + (i * (W - L - R)) / (years.length - 1), y = (v) => TOP + ((hi - v) * (H - TOP - BOT)) / (hi - lo);
  const svg = s("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "強さの点数の年度ごとの推移" });
  const g = s("g", { class: "grid" });
  for (let v = lo; v <= hi; v += 50) { g.append(s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v) })); svg.append(s("text", { x: L - 8, y: y(v) + 4, "text-anchor": "end" }, v)); }
  svg.append(g);
  svg.append(s("line", { x1: L, x2: W - R, y1: y(1500), y2: y(1500), stroke: "var(--muted)", "stroke-dasharray": "2 4", "stroke-width": 1 }));
  svg.append(s("text", { x: L + 4, y: y(1500) - 5 }, "全体の平均 1500"));
  years.forEach((yr, i) => svg.append(s("text", { x: x(i), y: H - 10, "text-anchor": "middle" }, `${yr}年度`)));
  const ends = [];
  for (const sr of series) {
    const pts = years.map((yr, i) => [x(i), sr.hist[yr]]).filter((p) => p[1] != null).map(([px, v]) => [px, y(v), v]);
    svg.append(s("polyline", { points: pts.map((p) => p[0] + "," + p[1]).join(" "), fill: "none", stroke: sr.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-dasharray": sr.dash ? "6 4" : null }));
    pts.forEach((p, i) => svg.append(s("circle", { cx: p[0], cy: p[1], r: i === pts.length - 1 ? 5 : 4, fill: sr.color, stroke: "var(--surface)", "stroke-width": 2 })));
    const last = pts[pts.length - 1];
    ends.push({ y: last[1], v: last[2], name: sr.name });
  }
  ends.sort((a, b) => a.y - b.y);
  if (ends.length === 2 && ends[1].y - ends[0].y < 34) { const m = (ends[0].y + ends[1].y) / 2; ends[0].y = m - 17; ends[1].y = m + 17; }
  for (const e of ends) { svg.append(s("text", { x: W - R + 12, y: e.y - 2, class: "lab-ja" }, e.name)); svg.append(s("text", { x: W - R + 12, y: e.y + 14, class: "val" }, e.v)); }
  const cross = s("line", { y1: TOP, y2: H - BOT, stroke: "var(--muted)", "stroke-width": 1, visibility: "hidden" });
  svg.append(cross);
  const hit = s("rect", { x: L, y: TOP, width: W - L - R, height: H - TOP - BOT, fill: "transparent" });
  hit.addEventListener("mousemove", (ev) => {
    const r = svg.getBoundingClientRect(), px = ((ev.clientX - r.left) * W) / r.width;
    const i = Math.max(0, Math.min(years.length - 1, Math.round((px - L) / ((W - L - R) / (years.length - 1)))));
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
    showTip(ev, `${years[i]}年度の終わり<br>` + series.map((sr) => `${sr.name} <b>${sr.hist[years[i]] ?? "―"}</b>`).join("<br>"));
  });
  hit.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
  svg.append(hit);
  return svg;
}

/* ---------- 共通: 表 ---------- */
// 勝ちと負けは形で分ける（○ と ×）。PK戦は「PK勝 4-3」と勝敗を文字でも書く
const RES = { "勝": ["w", "○"], "負": ["l", "×"], "PK勝": ["pkw", "○"], "PK負": ["pkl", "×"], "分": ["d", "△"] };
const resCell = (res, pk) => {
  const [cls, glyph] = RES[res] || ["", ""];
  return h("span", { class: "res " + cls }, h("b", { class: "g", "aria-hidden": "true" }, glyph), res + (pk ? ` ${pk}` : ""));
};
const scoreText = (g) => `${g.gf}-${g.ga}` + (g.et ? "（延長）" : "");
function isPast(when) {
  const a = (D.asOf.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})/) || []).slice(1).map(Number);
  const m = /^(\d{2})\/(\d{2})/.exec(when || "");
  return !!(m && a.length === 3 && Number(m[1]) * 100 + Number(m[2]) < a[1] * 100 + a[2]);
}
function leagueSection(t, isMe) {
  const sec = h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "今季のリーグ戦"), h("p", {}, "2026年。Tリーグ・地区リーグ")));
  if (!t.leagues || !t.leagues.length) {
    sec.append(h("p", { class: "empty" }, "今季のリーグ戦の記録はまだ見つかっていません。所属リーグの結果ページが分かれば追加できます。"));
    return sec;
  }
  for (const lg of t.leagues) {
    const games = lg.games.slice().sort((a, b) => (a.when === "日付未登録" ? "" : a.when).localeCompare(b.when === "日付未登録" ? "" : b.when));
    const played = games.filter((g) => g.res);
    const cnt = (r) => played.filter((g) => g.res === r).length;
    const gf = played.reduce((a, g) => a + g.gf, 0), ga = played.reduce((a, g) => a + g.ga, 0);
    const row = lg.table.find((r) => r.team === lg.teamName);
    const head = h("div", { class: "sec-head" },
      h("div", { class: "chips" }, h("strong", {}, lg.league),
        row ? h("span", { class: "chip " + (isMe ? "us" : "them") }, `${row.rank}位 / ${lg.table.length}チーム`) : null,
        h("span", { class: "chip num" }, `${played.length}試合 ${cnt("勝")}勝${cnt("分")}分${cnt("負")}敗・得${gf} 失${ga}`)),
      h("span", { class: "formstrip", "aria-label": "勝敗の並び（古い順）" }, played.map((g) => h("span", { class: LRES[g.res], title: `${g.when} ${g.opp} ${g.gf}-${g.ga}` }, g.res))));
    const gt = h("div", { class: "tbl" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "日付"), h("th", {}, "場所"), h("th", {}, "相手"), h("th", { class: "n" }, "スコア"), h("th", {}, "結果"))),
      h("tbody", {}, games.map((g) => h("tr", {}, h("td", { class: "n" }, g.when), h("td", {}, g.home ? "ホーム" : "アウェー"), h("td", {}, g.opp),
        h("td", { class: "n" }, g.res ? `${g.gf}-${g.ga}` : isPast(g.when) ? "結果なし" : "未実施"), h("td", {}, g.res ? resCell(g.res) : ""))))));
    const parts = [head, gt];
    if (lg.table.length) {
      parts.push(h("div", { class: "tbl" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", { class: "n" }, "順位"), h("th", {}, "チーム"), h("th", { class: "n" }, "試合"), h("th", { class: "n" }, "勝点"), h("th", { class: "n" }, "得失点"))),
        h("tbody", {}, lg.table.map((r) => h("tr", { class: r.team === lg.teamName ? (isMe ? "hl us" : "hl") : null }, h("td", { class: "n" }, r.rank), h("td", {}, r.team), h("td", { class: "n" }, r.gp), h("td", { class: "n" }, r.pts), h("td", { class: "n" }, (r.gd > 0 ? "+" : "") + r.gd)))))));
    }
    parts.push(h("p", { class: "small muted" }, "出典: ", h("a", { href: lg.source, target: "_blank", rel: "noopener" }, lg.source)));
    sec.append(h("div", { class: "stack" }, parts));
  }
  return sec;
}
const LRES = { "勝": "w", "分": "d", "負": "l" };

function stagesSection(t) {
  return h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "大会ごとの成績"), h("p", {}, "2022〜2026年度。○ 勝ち　× 負け。PK戦は「PK勝 4-3」のように書いています")),
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", { class: "n" }, "年度"), h("th", {}, "大会・段階"), h("th", {}, "最終到達"), h("th", {}, "勝ち上がり"))),
      h("tbody", {}, t.stages.map((st) => h("tr", {}, h("td", { class: "n" }, st.year), h("td", {}, `${st.series} ${st.stage}`), h("td", {}, st.reach), h("td", { style: "min-width:18em" }, st.path)))))));
}

function gamesSection(t) {
  const sec = h("section", { class: "sec" });
  const filt = h("div", { class: "filters", role: "group", "aria-label": "大会で絞り込む" });
  const box = h("div", { class: "tbl" });
  let cur = "すべて";
  const draw = () => {
    const rows = t.games.filter((g) => cur === "すべて" || g.series === cur).slice().reverse();
    box.replaceChildren(h("table", {}, h("thead", {}, h("tr", {}, h("th", { class: "n" }, "年度"), h("th", {}, "大会・段階"), h("th", {}, "ラウンド"), h("th", {}, "相手"), h("th", { class: "n" }, "スコア"), h("th", {}, "結果"), h("th", {}, "出典"))),
      h("tbody", {}, rows.map((g) => h("tr", {}, h("td", { class: "n" }, g.year), h("td", {}, `${g.series} ${g.stage}`), h("td", {}, g.round), h("td", {}, g.opp), h("td", { class: "n" }, scoreText(g)), h("td", {}, resCell(g.res, g.pk)), h("td", {}, h("a", { href: g.src, target: "_blank", rel: "noopener" }, "PDF")))))));
    filt.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.s === cur ? "true" : "false"));
  };
  for (const sr of ["すべて", "選手権", "総体", "新人戦", "関東"]) filt.append(h("button", { type: "button", "data-s": sr, onclick: () => { cur = sr; draw(); } }, sr));
  sec.append(h("div", { class: "sec-head" }, h("h2", {}, "全試合"), filt), box);
  draw();
  return sec;
}

function factsList(facts) {
  const dl = h("dl", { class: "facts" });
  for (const f of facts) dl.append(h("div", {}, h("dt", {}, f.label), h("dd", {}, f.value, h("span", { class: "src" }, /^https?:/.test(f.src) ? h("a", { href: f.src, target: "_blank", rel: "noopener" }, f.src.replace(/^https?:\/\//, "")) : f.src))));
  return dl;
}

function fiveYearKV(S, R) {
  return h("dl", { class: "kv" },
    h("dt", {}, "試合"), h("dd", {}, `${S.n}`),
    h("dt", {}, "勝敗"), h("dd", {}, `${S.w}勝 ${S.pkw}PK勝 ${S.pkl}PK負 ${S.l}敗`),
    h("dt", {}, "1試合平均"), h("dd", {}, `得点 ${S.gfPer} ／ 失点 ${S.gaPer}`),
    h("dt", {}, "無失点 ／ 無得点"), h("dd", {}, `${S.cleanSheets} ／ ${S.scoreless} 試合`),
    h("dt", {}, "1点差の決着"), h("dd", {}, `${S.oneGoal} 試合`),
    h("dt", {}, "延長"), h("dd", {}, `${S.et} 試合`),
    h("dt", {}, "2025年度以降"), h("dd", {}, R && R.n ? `${R.n}試合 ${R.w}勝 ${R.pkw}PK勝 ${R.pkl}PK負 ${R.l}敗` : "―"));
}

function pager() {
  const i = D.order.indexOf(D.slug);
  const prev = D.order[i - 1], next = D.order[i + 1];
  const cell = (slug, cls, lab) => slug ? h("a", { ...linkAttrs(slug), class: cls }, h("span", { class: "l" }, lab), h("b", {}, D.titles[slug])) : h("span", {});
  return h("nav", { class: "pager", "aria-label": "前後のページ" }, cell(prev, "prev", "← 前"), cell(next, "next", "次 →"));
}

/* ---------- ブロック全体（入口） ---------- */
function renderHub() {
  const root = $("#app");
  const nm = D.next;
  root.append(h("div", { class: "masthead" },
    h("div", { class: "eyebrow" }, D.blockLabel),
    h("h1", {}, h("span", { class: "us" }, nameOf(D.me)), D.over ? " の1次予選を振り返る" : D.nextOpp && D.final ? " の勝ち筋を描く" : " の勝ち上がりを読む"),
    h("p", { class: "lead" }, (() => {
      const alive = D.block.filter((k) => B[k].alive);
      const mine = B[D.me].outcome;
      if (D.over) {
        return `第105回選手権の東京都1次予選は、3試合を戦って2勝1敗で終わりました。`
          + `過去5年の公式戦 ${D.totalMatches.toLocaleString()} 試合と今季のリーグ戦から、3試合それぞれを振り返ります。`;
      }
      const nx = D.nextOpp && B[D.nextOpp];
      if (nx && D.final) {
        return `${mine.round}は${mine.opp.replace("都・", "")}に ${mine.score} で勝ち、残るは${alive.length}校。`
          + `次に勝てば2次予選です。過去5年の公式戦 ${D.totalMatches.toLocaleString()} 試合と今季のリーグ戦、それに観戦記事から、`
          + `${nx.display.replace("都・", "")}をできる限り調べて、勝ち筋をまとめました。`;
      }
      return (mine ? `${mine.round}は${mine.opp.replace("都・", "")}に ${mine.score} で${mine.won ? "勝ちました" : "負けました"}。` : "")
        + `残るは${alive.length}校です。過去5年の公式戦 ${D.totalMatches.toLocaleString()} 試合と今季のリーグ戦から、相手ごとに分析しています。学校名を選ぶと、その学校のページが開きます。`;
    })())));

  if (nm) {
    root.append(h("section", { class: "nextmatch", "aria-label": "次の試合" },
      h("div", { class: "when" }, h("div", { class: "d" }, `${nm.date}(${nm.dow}) ${nm.time}`), h("div", { class: "v" }, `${nm.round}【${nm.no}】・${nm.venue}`)),
      h("div", { class: "vs" }, h("span", { class: "t us" }, nameOf(D.me)), h("span", { class: "x" }, "vs"), h("a", { class: "t", ...linkAttrs(D.keyToSlug[nm.opp]) }, nameOf(nm.opp))),
      h("div", { class: "odds" }, h("div", { class: "p" }, pct(B[nm.opp].vsMe)), h("div", { class: "l" }, "武蔵丘が勝つ見込み。過去5年の大会と今季のリーグ戦からの目安です"))));
  }

  root.append(...planSections({ verdict: true }));
  if (D.over) { for (const f of [thisYearSection, journeySection, outsideSection]) { const s = f(); if (s) root.append(s); } }
  const gk = upsetsSection();
  if (gk) root.append(gk);

  // ここまでの結果（決着した試合）。回戦ごとに区切る
  if (D.decided && D.decided.length) {
    const nm2 = (k) => (B[k] ? B[k].display.replace("都・", "") : k);
    const rounds = [...new Set(D.decided.map((d) => d.round || "1回戦"))];
    const rows = [];
    for (const r of rounds) {
      if (rounds.length > 1) rows.push(h("li", { class: "rlab" }, r));
      for (const d of D.decided.filter((x) => (x.round || "1回戦") === r)) {
        const w = d.winner;
        rows.push(h("li", { class: d.a === D.me || d.b === D.me ? "mine" : null },
          h("span", { class: "t" + (w === d.a ? " win" : "") }, nm2(d.a)),
          h("b", { class: "num sc" }, d.score),
          h("span", { class: "t" + (w === d.b ? " win" : "") }, nm2(d.b)),
          h("span", { class: "small muted" }, `${nm2(w)}が${NEXT_ROUND[r] || "次へ"}`)));
      }
    }
    root.append(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, "ここまでの結果"), h("p", {}, rounds.join("・"))),
      h("ul", { class: "done-list" }, rows)));
  }


  const road = h("div", { class: "road" });
  for (const st of D.road) {
    const col = h("div", { class: "step" }, h("div", { class: "step-h" }, h("span", { class: "n" }, st.n), h("span", { class: "r" }, st.round), h("span", { class: "d" }, st.when)));
    if (st.result) {
      const won = st.result.winner === D.me;
      col.append(h("div", { class: "result-banner" + (won ? " won" : "") }, h("span", { class: "res " + (won ? "w" : "l") }, h("b", { class: "g", "aria-hidden": "true" }, won ? "○" : "×"), won ? "勝ち" : "負け"),
        h("b", { class: "num" }, st.result.score), h("span", { class: "small muted" }, "終了")));
    }
    const settled = st.bd && st.bd.opps.length === 1 && st.bd.reach >= 0.9995;
    if (st.bd && st.bd.before && !settled) col.append(meetBar(st));
    for (const k of st.teams) {
      const t = B[k];
      col.append(h("a", { class: "team-card" + (t.alive ? "" : " out"), ...linkAttrs(D.keyToSlug[k]) },
        h("div", { class: "nm" }, h("b", {}, t.display), h("span", { class: "go" }, "分析を見る →")),
        h("div", { class: "sub" }, t.area ? `第${t.area.area}地区・${t.area.city}・${t.area.kind}` : ""),
        t.leagueLine ? h("div", { class: "form" }, t.leagueLine) : null,
        t.alive && !D.over ? h("dl", {}, h("div", {}, h("dt", {}, "武蔵丘が勝つ見込み"), h("dd", { class: "us" }, pct(t.vsMe))), h("div", {}, h("dt", {}, "当たる確率"), h("dd", {}, pct(t.meetProb))))
          : h("div", { class: "out-note" }, t.alive ? `${B[D.me].outcome.round}で武蔵丘に勝利` : `${t.outcome ? t.outcome.round : ""}で敗退`)));
    }
    road.append(col);
  }
  root.append(h("section", { class: "sec", id: "road" }, h("div", { class: "sec-head" }, h("h2", {}, D.over ? "歩いた道" : "勝ち上がりの道"), h("p", {}, D.over ? "3試合それぞれのページへ" : `${D.doneNote}。灰色は敗退した学校`)), road,
    D.over ? null : h("p", { class: "small muted prose" }, "「当たる確率」は、武蔵丘と相手の両方がその試合まで勝ち上がる見込みです。武蔵丘がその前に負けるとどちらとも当たらないため、候補2校を足すと「武蔵丘がその回戦まで進む見込み」になり、100%にはなりません。帯グラフの斜線がその差（武蔵丘がその前に負ける場合）です。")));

  const left = h("div", { class: "stack" },
    h("div", { class: "card" }, h("div", { class: "sec-head" }, h("h2", {}, "ブロックの山"), h("p", {}, "赤線は勝ち上がり。点線は武蔵丘の道")), bracketSVG()),
    h("div", { class: "card" }, h("h2", {}, "日程と会場"), scheduleList()));
  const right = h("div", { class: "stack lg" }, D.over ? null : outlookSection(),
    h("section", { class: "sec" }, h("h2", {}, "過去の実績と今季の調子"), h("ul", { class: "points" }, D.formNote.map((t) => h("li", {}, t)))));
  root.append(h("div", { class: "split rev" }, left, right));

  root.append(eloSection());
  root.append(h("div", {},
    h("details", { class: "more" }, h("summary", {}, "リーグの階層"), h("div", { class: "body" },
      h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "階層"), h("th", {}, "構成"), h("th", {}, "この山の学校"))),
        h("tbody", {}, D.pyramid.map((p) => h("tr", {}, h("td", { style: "white-space:nowrap;font-weight:700" }, p.tier), h("td", {}, p.desc), h("td", {}, p.teams.join("、"))))))),
      h("p", { class: "small muted" }, D.pyramidNote))),
    h("details", { class: "more" }, h("summary", {}, "数字の読み方"), h("div", { class: "body" }, h("ul", { class: "method" }, D.method.map((m) => h("li", {}, m)))))));
}

/* 当たる確率の内訳: 100% を「A と当たる／B と当たる／武蔵丘がその前に負ける」に分ける */
function meetBar(st) {
  const bd = st.bd, final = st.round !== "2回戦";
  const meWin = final ? "武蔵丘が2回戦まで勝つ" : "武蔵丘が1回戦に勝つ";
  const oppWin = (nm) => (final ? `${nm}が決勝に来る` : `${nm}が1回戦に勝つ`);
  const cols = ["var(--them)", "color-mix(in srgb, var(--them) 45%, var(--surface))"];
  const lose = 1 - bd.reach;
  const bar = h("div", { class: "meetbar", role: "img", "aria-label": bd.opps.map((o) => `${nameOf(o.key)}と当たる ${pct(o.meet)}`).join("、") + `、${bd.before} ${pct(lose)}` },
    bd.opps.map((o, i) => h("span", { style: `flex:${o.meet};background:${cols[i]}` })), h("span", { class: "lose", style: `flex:${lose}` }));
  return h("div", { class: "meet" },
    h("div", { class: "small muted" }, "この回戦の100%の内訳"), bar,
    h("ul", { class: "meetlist" },
      bd.opps.map((o, i) => h("li", {}, h("i", { style: `background:${cols[i]}` }), h("span", {}, h("b", {}, `${nameOf(o.key)}と当たる ${pct(o.meet)}`),
        h("small", {}, `＝ ${meWin} ${pct(bd.reach)} × ${oppWin(nameOf(o.key))} ${pct(o.share)}`)))),
      lose > 0.0005 ? h("li", {}, h("i", { class: "lose" }), h("span", {}, h("b", {}, `武蔵丘が${bd.before.replace("負ける", "")}負け、どちらとも当たらない ${pct(lose)}`))) : null));
}

/* 強さの点数のしくみ（入口ページ） */
const winP = (d) => 1 / (1 + Math.pow(10, -d / 400));
function eloSection() {
  const E = D.elo;
  const sec = h("section", { class: "sec", id: "elo" },
    h("div", { class: "sec-head" }, h("h2", {}, "強さの点数のしくみ"), h("p", {}, "Elo（イロ）レーティング")),
    h("p", { class: "prose" }, "チェスなどで使われる Elo レーティングを、高校サッカー向けに少し変えた計算です。全校を同じ物差しで並べ、試合の勝ち負けから少しずつ点数を動かします。",
      h("b", {}, "設定は、2022〜2026年度の大会の試合を試合前の点数でどれだけ当てられたかで選びました（2025・26年度の大会で、見込みの高い側が勝った割合 80.3%）。"), "それでも過去の試合からの目安です。"));
  const steps = [
    ["はじまりは全校 " + E.base + " 点", "データの最初（2022年度）の試合から数え始めます。リーグ戦で初めて出てくる控え（B・C…）は、その学校の点数から B は100点・C は200点…引いた点数で始めます。"],
    ["試合の前に「勝つ見込み」を出す", "見込み ＝ 1 ÷（1 ＋ 10 の（−点数の差 ÷ 400）乗）。差が 0 点なら 50%、100 点なら約 64%、200 点なら約 76%。"],
    ["試合の後に点数を動かす", `変化 ＝ ${E.k} × 試合の重み × 点差の倍率 ×（結果 − 見込み）。重みは大会 1・リーグ戦 ${E.leagueWeight}。結果は勝ち 1、負け 0、PK戦 0.5（引き分け扱い）。勝った側が増えた分だけ、負けた側が減ります。`],
    ["大差の勝ちほど大きく動かす", "点差の倍率は、1点差以内 1倍、2点差 1.5倍、3点差以上は（11 ＋ 点差）÷ 8 倍（3点差 1.75倍、5点差 2倍）。"],
    E.carry >= 1 ? ["年度が変わっても点数は戻さない", "部員は入れ替わっても、学校ごとの強さ（指導や部員の集まり方）は続きます。平均へ戻す計算と比べて、戻さないほうが当たりました。"]
      : ["年度が変わったら平均へ少し戻す", `年度の終わりに ${E.base} 点との差を ${Math.round((1 - E.carry) * 100)}% 縮めます。`],
    ["大会とリーグ戦を日付順に数える", `高体連のトーナメント表にある ${D.totalMatches.toLocaleString()} 試合（総体・選手権・新人戦・関東予選）に、Tリーグ・プリンスリーグ関東・地区リーグの試合を足します。控えやクラブは学校とは別のチームとして数え、控えの負けで学校の点数は下がりません。試合数の少ないチームとの試合では、学校の点数を動かしません。`],
  ];
  const ol = h("ol", { class: "steps" }, steps.map(([t, b]) => h("li", {}, h("b", {}, t), h("span", {}, b))));
  const ex = E.example;
  const exBox = h("div", { class: "card" }, h("h3", {}, "計算の例"),
    h("p", { class: "small" }, `${ex.me} ${ex.meElo} 点 対 ${ex.opp} ${ex.oppElo} 点 → 差 ${ex.diff > 0 ? "+" : ""}${ex.diff} 点 → ${ex.me}が勝つ見込み ${pct(ex.p)}`),
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "武蔵丘から見た結果"), h("th", { class: "n" }, ex.me), h("th", { class: "n" }, ex.opp))),
      h("tbody", {}, ex.cases.map((c) => h("tr", {}, h("td", { style: "white-space:nowrap" }, c.label),
        h("td", { class: "n" }, `${c.delta > 0 ? "+" : c.delta < 0 ? "−" : "±"}${Math.abs(c.delta)} → ${c.me}`),
        h("td", { class: "n" }, `${c.delta < 0 ? "+" : c.delta > 0 ? "−" : "±"}${Math.abs(c.delta)} → ${c.opp}`)))))),
    h("p", { class: "small muted" }, "見込みの高い側が勝っても点数はあまり動かず、見込みの低い側が勝つと大きく動きます。PK戦は勝敗にかかわらず引き分けとして計算します。"));
  sec.append(h("div", { class: "split" }, h("div", { class: "stack" }, ol, curveFigure()), h("div", { class: "stack" }, exBox,
    h("div", { class: "card" }, h("h3", {}, "このサイトの数字の出し方"), h("ul", { class: "points" }, E.uses.map((u) => h("li", {}, u)))),
    h("div", { class: "card" }, h("h3", {}, "確かめたことと弱点"), h("ul", { class: "points" }, E.caveats.map((u) => h("li", {}, u)))))));
  return sec;
}

function curveFigure() {
  // 点数の差（武蔵丘 − 相手）と、武蔵丘が勝つ見込みの関係。この山の相手の位置を点で示す
  const W = 620, H = 250, L = 44, R = 20, TOP = 16, BOT = 40, X0 = -250, X1 = 250;
  const x = (d) => L + ((d - X0) * (W - L - R)) / (X1 - X0), y = (p) => TOP + (1 - p) * (H - TOP - BOT);
  const svg = s("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "点数の差と勝つ見込みの関係" });
  for (const p of [0, 0.25, 0.5, 0.75, 1]) { svg.append(s("line", { x1: L, x2: W - R, y1: y(p), y2: y(p), stroke: "var(--rule)" })); svg.append(s("text", { x: L - 8, y: y(p) + 4, "text-anchor": "end" }, Math.round(p * 100) + "%")); }
  for (let d = X0; d <= X1; d += 50) svg.append(s("text", { x: x(d), y: H - 20, "text-anchor": "middle" }, (d > 0 ? "+" : "") + d));
  svg.append(s("text", { x: (L + W - R) / 2, y: H - 3, "text-anchor": "middle" }, "点数の差（武蔵丘 − 相手）"));
  svg.append(s("line", { x1: x(0), x2: x(0), y1: TOP, y2: H - BOT, stroke: "var(--rule-strong)", "stroke-dasharray": "2 4" }));
  const pts = [];
  for (let d = X0; d <= X1; d += 5) pts.push(`${x(d)},${y(winP(d))}`);
  svg.append(s("polyline", { points: pts.join(" "), fill: "none", stroke: "var(--ink-2)", "stroke-width": 2 }));
  const opps = D.elo.opponents.slice().sort((a, b) => a.diff - b.diff);
  opps.forEach((o, i) => {
    const cx = x(Math.max(X0, Math.min(X1, o.diff))), cy = y(winP(o.diff));
    svg.append(s("circle", { cx, cy, r: 5, fill: "var(--them)", stroke: "var(--surface)", "stroke-width": 2 }));
    const above = i % 2 === 0;
    svg.append(s("text", { x: cx, y: above ? cy - 12 : cy + 20, "text-anchor": "middle", class: "lab-ja" }, `${o.name} ${pct(winP(o.diff))}`));
    const hit = s("circle", { cx, cy, r: 14, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => showTip(ev, `${o.name}<br>点数の差 <b>${o.diff > 0 ? "+" : ""}${o.diff}</b><br>武蔵丘が勝つ見込み <b>${pct(winP(o.diff))}</b>`));
    hit.addEventListener("mouseleave", hideTip);
    svg.append(hit);
  });
  return h("div", { class: "figure" }, h("div", { class: "cap" }, h("h3", {}, "点数の差と勝つ見込み"), h("div", { class: "legend" }, h("span", {}, h("i", { class: "box", style: "background:var(--them)" }), "この山の相手"))), svg);
}

function outlookSection() {
  const alive = D.block.filter((k) => B[k].alive).sort((a, b) => B[b].blockWin - B[a].blockWin);
  const W = 640, L = 118, R = 64, TOP = 6, rowH = 36, AX = TOP + alive.length * rowH + 2;
  const max = Math.ceil(Math.max(...alive.map((k) => B[k].blockWin)) * 10 + 0.5) / 10;
  const x = (v) => L + (v / max) * (W - L - R);
  const svg = s("svg", { class: "chart", viewBox: `0 0 ${W} ${AX + 26}`, role: "img", "aria-label": "この山を勝ち抜く見込みの棒グラフ" });
  for (let v = 0; v <= max + 1e-9; v += 0.1) {
    svg.append(s("line", { x1: x(v), x2: x(v), y1: TOP, y2: AX, stroke: "var(--rule)" }));
    svg.append(s("text", { x: x(v), y: AX + 18, "text-anchor": "middle" }, Math.round(v * 100) + "%"));
  }
  svg.append(s("line", { x1: L, x2: L, y1: TOP, y2: AX, class: "base" }));
  alive.forEach((k, i) => {
    const yv = TOP + i * rowH + 7, v = B[k].blockWin, me = k === D.me, w = Math.max(3, x(v) - L);
    svg.append(s("text", { x: L - 10, y: yv + 15, "text-anchor": "end", class: "lab-ja", style: me ? "fill:var(--us)" : null }, nameOf(k)));
    svg.append(s("path", { d: `M${L},${yv} h${w - 4} a4,4 0 0 1 4,4 v14 a4,4 0 0 1 -4,4 h${-(w - 4)} z`, fill: me ? "var(--us)" : "var(--rule-strong)" }));
    svg.append(s("text", { x: x(v) + 8, y: yv + 15, class: "val" }, pct(v, 1)));
    const hit = s("rect", { x: 0, y: yv - 7, width: W, height: rowH, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => showTip(ev, `${nameOf(k)}<br>山を勝ち抜く見込み <b>${pct(v, 1)}</b><br>強さの点数 <b>${B[k].elo}</b>`));
    hit.addEventListener("mouseleave", hideTip);
    svg.append(hit);
  });
  return h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "この山を勝ち抜く見込み"), h("p", {}, `残り${alive.length}校。強さの点数から計算`)), svg,
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "学校"), h("th", { class: "n" }, "強さの点数"), h("th", { class: "n" }, "山を勝ち抜く"), h("th", { class: "n" }, "武蔵丘が勝つ"), h("th", { class: "n" }, "当たる確率"))),
      h("tbody", {}, D.block.map((k) => {
        const played = (D.decided || []).find((d) => (d.a === k && d.b === D.me) || (d.b === k && d.a === D.me));
        const sc = played && (played.a === D.me ? played.score : played.score.split("-").reverse().join("-"));
        const vsMe = k === D.me ? "―" : played ? `${played.winner === D.me ? "勝ち" : "負け"} ${sc}` : B[k].alive ? pct(B[k].vsMe, 1) : "―";
        return h("tr", { class: k === D.me ? "hl us" : null },
          h("td", {}, D.keyToSlug[k] ? h("a", linkAttrs(D.keyToSlug[k]), nameOf(k)) : nameOf(k)),
          h("td", { class: "n" }, B[k].elo),
          h("td", { class: "n" }, B[k].alive ? pct(B[k].blockWin, 1) : "敗退"),
          h("td", { class: "n" }, vsMe),
          h("td", { class: "n" }, k === D.me || !B[k].alive ? "―" : pct(B[k].meetProb, 1)));
      })))));
}

/* ---------- 相手校のページ ---------- */
function renderTeam() {
  const t = D.team, k = t.key, root = $("#app"), br = B[k];
  const lg = (t.leagues || [])[0];
  const row = lg && lg.table.find((r) => r.team === lg.teamName);
  root.append(h("div", { class: "masthead" },
    h("div", { class: "crumb" }, h("a", linkAttrs("index"), "ブロック全体"), h("span", { "aria-hidden": "true" }, "›"),
      h("span", {}, br.round)),
    h("div", { class: "chips" },
      h("span", { class: "chip " + (br.alive ? "them" : "out") }, br.alive ? `${br.round}${br.candidate ? "で当たる可能性" : "の相手"}` : `${br.round}で敗退`),
      br.area ? h("span", { class: "chip" }, `第${br.area.area}地区・${br.area.city}・${br.area.kind}`) : null,
      lg ? h("span", { class: "chip" }, lg.league) : null),
    h("h1", {}, t.display),
    br.outcome ? h("p", { class: "lead" }, `${br.outcome.round}は${br.outcome.opp.replace("都・", "")}に ${br.outcome.score} で${br.outcome.won ? "勝ち" : "負け"}。`,
      br.alive ? "" : "この山からは敗退しました。以下は対戦前に作った分析と、5年間の記録です。") : null,
    t.info.summary ? h("p", { class: "lead" }, t.info.summary) : null));

  root.append(h("div", { class: "kpis" },
    br.alive
      ? h("div", { class: "kpi" }, h("span", { class: "k" }, "武蔵丘が勝つ見込み"), h("span", { class: "v us" }, pct(br.vsMe)), h("span", { class: "note" }, "過去5年の大会成績と今季のリーグ戦から"))
      : h("div", { class: "kpi" }, h("span", { class: "k" }, `${br.round}の結果`), h("span", { class: "v" }, br.outcome ? br.outcome.score : "―"), h("span", { class: "note" }, br.outcome ? `${br.outcome.opp.replace("都・", "")}に${br.outcome.won ? "勝ち" : "負け"}・敗退` : "")),
    br.alive
      ? h("div", { class: "kpi" }, h("span", { class: "k" }, "武蔵丘と当たる確率"), h("span", { class: "v" }, pct(br.meetProb)), h("span", { class: "note" }, br.candidate ? `${br.round}。武蔵丘と${t.display}の両方が勝ち上がる見込み（武蔵丘が途中で負ける場合を含むので、候補2校を足しても100%にならない）。` : br.round, br.candidate ? h("a", { ...linkAttrs("index"), href: hrefOf("index") + "#road" }, " 内訳") : null))
      : h("div", { class: "kpi" }, h("span", { class: "k" }, "対戦前の見込み"), h("span", { class: "v muted" }, pct(br.vsMe)), h("span", { class: "note" }, "武蔵丘が勝つ見込みとして出していた値（結果と見比べる用）")),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "強さの点数"), h("span", { class: "v" }, t.elo, h("small", {}, `${t.eloRank}位`)), h("span", { class: "note" }, `${D.nTeamsRated}校中。武蔵丘は ${B[D.me].elo}。`, eloLink())),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "今季のリーグ"), h("span", { class: "v them" }, row ? `${row.rank}位` : "―", row ? h("small", {}, `/${lg.table.length}`) : null), h("span", { class: "note" }, lg ? lg.league : "結果ページ未確認"))));

  const main = h("div", { class: "stack lg" });
  const pts = h("ul", { class: "points" }, (t.autoPoints || []).map((p) => h("li", { html: p })));
  const scout = h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "スカウティングの要点"), h("p", {}, "数字から読めること")), pts);
  if (t.style) {
    scout.append(h("h3", {}, "戦い方（観戦記事から）"), h("ul", { class: "points" }, t.style.points.map((p) => h("li", {}, p))),
      t.style.caveat ? h("p", { class: "small muted" }, t.style.caveat) : null,
      h("p", { class: "small" }, ...t.style.sources.flatMap((sr, i) => [i ? "　" : "", h("a", { href: sr.url, target: "_blank", rel: "noopener" }, sr.label)])));
  } else {
    scout.append(h("p", { class: "small muted" }, D.styleNone));
  }
  const rv = reviewSection(k);
  if (rv) main.append(rv);
  if (k === "城東") {
    const pm = postmortemSection();
    if (pm) main.append(pm);
    main.append(...planSections({ myths: true, style: true, clock: true, keys: true, risks: true, conditions: true }));
  }
  main.append(scout, leagueSection(t, false));
  main.append(h("section", { class: "sec" }, h("div", { class: "figure" },
    h("div", { class: "cap" }, h("h2", {}, "強さの点数の推移"), h("div", { class: "legend" }, h("span", {}, h("i", { style: "border-color:var(--us)" }), nameOf(D.me)), h("span", {}, h("i", { class: "dash", style: "border-color:var(--them)" }), t.display))),
    eloChart([{ name: nameOf(D.me), hist: D.meHistory, color: "var(--us)" }, { name: t.display, hist: t.eloHistory, color: "var(--them)", dash: true }]),
    h("p", { class: "small muted" }, "各年度の終わりの点数。部員が入れ替わるので、年度が変わるたびに平均へ少し戻して計算しています。"))));
  main.append(stagesSection(t), gamesSection(t));

  const side = h("aside", { class: "stack side" });
  const cmp = h("div", { class: "card" }, h("h2", {}, "武蔵丘との比較"));
  if (t.headToHead.length) cmp.append(h("p", {}, "直接対戦: ", t.headToHead.map((g) => `${g.year}年度 ${g.series} ${g.round} 武蔵丘 ${scoreText(g)}（${g.res}）`).join("、")));
  else cmp.append(h("p", { class: "empty" }, "2022年度以降の直接対戦はありません。"));
  if (t.common.length) {
    cmp.append(h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "共通の相手"), h("th", {}, "武蔵丘"), h("th", {}, t.display))),
      h("tbody", {}, t.common.map((c) => h("tr", {}, h("td", {}, c.common), h("td", {}, c.me.map((g) => `${g.year} ${scoreText(g)} ${g.res}`).join(" / ")), h("td", {}, c.them.map((g) => `${g.year} ${scoreText(g)} ${g.res}`).join(" / "))))))));
  } else cmp.append(h("p", { class: "empty" }, "共通の対戦相手もありません（地区が違うため）。比べるときは強さの点数を目安にしてください。"));
  side.append(cmp,
    h("div", { class: "card" }, h("h2", {}, "5年間の数字"), fiveYearKV(t.summary, t.recent)),
    (t.info.facts || []).length ? h("div", { class: "card" }, h("h2", {}, "公開情報"), factsList(t.info.facts)) : null);
  root.append(h("div", { class: "split" }, main, side));
}

/* つながりの糸口: 直接戦っていない相手とも、試合をたどるとつながる */
function connectionsSection(t, opt = {}) {
  const C = t.connections, n = opt.n || 6;
  const sec = h("section", { class: "sec" }, h("div", { class: "sec-head" }, h(opt.tag || "h2", {}, opt.title || "つながりの糸口"), opt.tag ? null : h("p", {}, "直接の対戦がなくても、試合をたどるとつながる相手")));
  if (!C || !C.summary.n) { sec.append(h("p", { class: "empty" }, "3段以内でつながる試合は見つかりませんでした。")); return sec; }
  const S = C.summary, tot = S.up + S.even + S.down;
  const seg = (n, col, lab) => (n ? h("span", { style: `flex:${n};background:${col}`, title: `${lab} ${n}本` }) : null);
  sec.append(h("div", { class: "conn-sum" },
    h("div", { class: "conn-bar", role: "img", "aria-label": `武蔵丘が上とみる ${S.up}本、互角 ${S.even}本、下とみる ${S.down}本` }, seg(S.up, "var(--us)", "武蔵丘が上"), seg(S.even, "var(--rule-strong)", "互角"), seg(S.down, "var(--them)", "相手が上")),
    h("div", { class: "legend" },
      h("span", {}, h("i", { class: "box", style: "background:var(--us)" }), `武蔵丘が上とみる ${S.up}本`),
      h("span", {}, h("i", { class: "box", style: "background:var(--rule-strong)" }), `互角 ${S.even}本`),
      h("span", {}, h("i", { class: "box", style: "background:var(--them)" }), `${t.display}が上とみる ${S.down}本`)),
    h("p", { class: "small" }, `つながり ${S.n}本（直接 ${S.direct}・2段 ${S.two}・3段 ${S.three}）。新しい試合と短いつながりを重く見た平均は `, h("b", { class: "num" }, `${S.weighted > 0 ? "+" : ""}${S.weighted}点差`), `（プラスなら武蔵丘が上）。`)));
  const MK = { "勝": "○", "PK勝": "○", "負": "×", "PK負": "×", "分": "△" };
  const list = h("ol", { class: "chains" });
  for (const c of C.top.slice(0, n)) {
    const row = h("div", { class: "chain" });
    c.path.forEach((nm, i) => {
      row.append(h("span", { class: "node" + (i === 0 ? " me" : i === c.path.length - 1 ? " opp" : "") }, nm));
      if (i < c.legs.length) {
        const lg = c.legs[i];
        const pk = lg.pk ? ` ${lg.res} ${lg.pk}` : "";
        row.append(h("span", { class: "edge " + (lg.res.includes("勝") ? "w" : lg.res.includes("負") ? "l" : "") },
          h("b", {}, `${MK[lg.res]} ${lg.gf}-${lg.ga}${pk}`), h("small", {}, `${lg.year} ${lg.series}`)));
      }
    });
    list.append(h("li", {}, h("span", { class: "imp num " + (c.implied > 0 ? "up" : c.implied < 0 ? "down" : "") }, `${c.implied > 0 ? "+" : ""}${c.implied}`), row));
  }
  sec.append(h("div", { class: "stack", style: "gap:8px" }, opt.tag ? null : h("h3", {}, "重みの大きいつながり"), list),
    opt.tag ? null : h("p", { class: "small muted" }, "左の数字は、各試合の得点差を足した目安（PK戦は0）。「AがBに勝ち、BがCに勝った」からといって「AはCより強い」とは限らないので、弱い手がかりとして見てください。全件は data/connections/ の CSV にあります。"));
  return sec;
}

/* ---------- 2次予選の強豪（1次予選の免除校）のページ ---------- */
const SERIES = [["関東", "関東予選"], ["総体", "総体"], ["選手権", "選手権"], ["新人戦", "新人戦（地区）"]];
const lgText = (c) => (c.rank ? `${c.league} ${c.rank}位` : c.league);
const signed = (v, d = 2) => (v == null ? "―" : `${v > 0 ? "+" : ""}${v.toFixed(d)}`);
function renderSeeds() {
  const X = D.seeds, root = $("#app"), list = X.seeds, W = X.weights;
  root.append(h("div", { class: "masthead" },
    h("div", { class: "crumb" }, h("a", linkAttrs("index"), "ブロック全体"), h("span", { "aria-hidden": "true" }, "›"), h("span", {}, "2次予選")),
    h("div", { class: "chips" }, h("span", { class: "chip them" }, "2次予選から出てくる学校"), h("span", { class: "chip warn" }, X.status.split("（")[0]), h("span", { class: "chip" }, `${list.length}校`)),
    h("h1", {}, "2次予選の強豪 ", h("span", { class: "num" }, list.length), "校"),
    h("p", { class: "lead" }, "1次予選を免除され、2次予選から出てくる学校です。今季のリーグの位置、過去5年の大会の成績、武蔵丘との試合のつながりをまとめ、強豪の中での順位をつけました。")));

  const top = list[0], best = [...list].sort((a, b) => b.vsMe - a.vsMe)[0];
  const avg = Math.round(list.reduce((s, t) => s + t.elo, 0) / list.length);
  root.append(h("div", { class: "kpis" },
    h("div", { class: "kpi" }, h("span", { class: "k" }, "総合1位"), h("span", { class: "v them" }, top.display), h("span", { class: "note" }, `総合点 ${top.scores.total}・${lgText(top.league.cur)}`)),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "強豪の強さの点数（平均）"), h("span", { class: "v" }, avg), h("span", { class: "note" }, `武蔵丘は ${X.meElo}。`, eloLink())),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "武蔵丘が勝つ見込み"), h("span", { class: "v us" }, `${pct(Math.min(...list.map((t) => t.vsMe)))}〜${pct(best.vsMe)}`), h("span", { class: "note" }, "強豪の中での幅（1試合あたり）")),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "組み合わせ"), h("span", { class: "v" }, "9/23", h("small", {}, "ごろ")), h("span", { class: "note" }, "1次予選の後に抽選。決まったら当たる学校に絞ります"))));
  root.append(h("nav", { class: "toc", "aria-label": "このページの中" }, [["why", "免除の理由"], ["rank", "強豪の順位"], ["each", "学校ごとの分析"], ["tl", "Tリーグ全チーム"], ["first", `1次予選の全${X.nFirst}校`]].map(([id, lab]) => h("a", { href: `#${id}` }, lab))));
  root.append(whySection(X));

  // ランキング表（見出しで並べ替え）
  const cols = [
    { k: "rank", lab: "順位", n: true, val: (t) => t.rank, fmt: (t) => t.rank },
    { k: "name", lab: "学校", val: (t) => t.display },
    { k: "total", lab: "総合点", n: true, val: (t) => -t.scores.total, fmt: (t) => h("div", { class: "totcell" }, h("span", { class: "num" }, t.scores.total.toFixed(1)), h("div", { class: "meter them" }, h("i", { style: `width:${t.scores.total}%` }))) },
    { k: "elo", lab: "強さの点数", n: true, val: (t) => -t.elo, fmt: (t) => [t.elo, h("small", { class: "muted" }, ` ${t.eloRank}位`)] },
    { k: "league", lab: "今季のリーグ", val: (t) => t.league.cur.pos, fmt: (t) => lgText(t.league.cur) + (t.league.cur.n ? `/${t.league.cur.n}` : "") },
    { k: "conn", lab: "つながり", n: true, val: (t) => t.conn.summary.weighted ?? 99, fmt: (t) => signed(t.conn.summary.weighted) },
    { k: "vs", lab: "武蔵丘が勝つ見込み", n: true, val: (t) => -t.vsMe, fmt: (t) => pct(t.vsMe) },
    { k: "sotai", lab: "2026 総体", val: (t) => t.rank, fmt: (t) => (t.tourn[2026] && t.tourn[2026]["総体"] ? t.tourn[2026]["総体"].text : "―") },
    { k: "why", lab: "免除の根拠", val: (t) => t.rank, fmt: (t) => h("span", { class: "tags" }, t.exempt.tags.map((g) => h("span", { class: "tag " + (g.tag === "その他" ? "warn" : "") }, g.tag))) },
  ];
  let sortKey = "rank";
  const tbody = h("tbody");
  const headRow = h("tr");
  const fill = () => {
    const c = cols.find((x) => x.k === sortKey);
    const rows = [...list].sort((a, b) => (c.val(a) > c.val(b) ? 1 : c.val(a) < c.val(b) ? -1 : a.rank - b.rank));
    tbody.replaceChildren(...rows.map((t) => h("tr", {}, cols.map((col) => col.k === "name"
      ? h("td", { class: "nm" }, h("a", { href: `#s-${t.rank}`, onclick: () => openSeed(t.rank) }, t.display))
      : h("td", { class: col.n ? "n" : null }, col.fmt(t))))));
    headRow.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === sortKey)));
  };
  for (const c of cols) {
    headRow.append(h("th", { class: c.n ? "n" : null, "aria-sort": null },
      c.k === "name" || c.k === "sotai" || c.k === "why" ? c.lab : h("button", { class: "sort", "data-k": c.k, type: "button", onclick: () => { sortKey = c.k; fill(); } }, c.lab)));
  }
  fill();
  root.append(h("section", { class: "sec", id: "rank" }, h("div", { class: "sec-head" }, h("h2", {}, "強豪の中での順位"), h("p", {}, "見出しを押すと並べ替え。学校名で詳しい分析へ")),
    h("div", { class: "tbl" }, h("table", { class: "rank" }, h("thead", {}, headRow), tbody)),
    h("details", { class: "more" }, h("summary", {}, "順位のつけ方と、免除校の決め方"),
      h("div", { class: "body" },
        h("ol", { class: "steps" },
          h("li", {}, h("b", {}, `強さの点数（${W.elo * 100}%）`), h("span", {}, "過去5年の公式戦から計算した点数。大きいほど強い。")),
          h("li", {}, h("b", {}, `今季のリーグの位置（${W.league * 100}%）`), h("span", {}, "プリンスリーグ関東1部 → T1 → … → T5 → 地区リーグの順に上。同じリーグの中は順位で比べる。地区リーグの学校は順位が分からないので、いちばん下に置く。")),
          h("li", {}, h("b", {}, `武蔵丘とのつながり（${W.conn * 100}%）`), h("span", {}, "武蔵丘との試合のつながりから出した「目安の点差」。マイナスが大きいほど、武蔵丘より上とみる。")),
          h("li", {}, h("b", {}, "総合点"), h("span", {}, "3つを、強豪の中でいちばん上を100・いちばん下を0に直してから、上の割合で平均する。"))),
        h("p", { class: "small muted" }, "この順位のつけ方は Claude Code が置いたもので、当たり具合はまだ確かめていません。0点の学校も、強豪の中でいちばん下というだけで、武蔵丘より強い見込みです。"),
        h("p", { class: "small muted" }, "免除校の決め方は、上の「免除の理由」を見てください。")))));

  // 学校ごと
  const box = h("div", { class: "stack" }, h("div", { class: "sec-head" }, h("h2", {}, "学校ごとの分析"), h("p", {}, "総合点の順。押すと開きます")));
  for (const t of list) box.append(seedCard(t));
  root.append(h("section", { class: "sec", id: "each" }, box), tleagueSection(X), firstRoundSection(X));
  const openFromHash = () => { const m = location.hash.match(/^#s-(\d+)$/); if (m) openSeed(+m[1]); };
  addEventListener("hashchange", openFromHash); openFromHash();
}
/* なぜ免除か: 過去の組み合わせから割り出した決まりと、その当てはまり具合 */
function whySection(X) {
  const E = X.evidence, Y = E.years, cur = Y[Y.length - 1];
  const past = Y.filter((y) => !y.estimated);
  const so2Past = past.reduce((a, y) => [a[0] + y.so2Exempt, a[1] + y.so2], [0, 0]);
  const t12Rows = Y.filter((y) => y.t12 != null);
  const nm = (k) => (X.seeds.find((t) => t.key === k) || {}).display || k;
  const rules = [
    { h: "総体の二次トーナメントに出た学校", conf: "確実に近い", ok: true, past: `2022〜2025年度の${so2Past[1]}校すべてが免除（例外なし）`, now: `2026年度は ${cur.so2} 校` },
    { h: "Tリーグの T1・T2 にトップチームがいる学校", conf: "高い", ok: true, past: t12Rows.map((y) => `${y.year}年度 ${y.t12Exempt}/${y.t12}校`).join("、") + " が免除（例外なし）", now: `2026年度は ${cur.t12} 校（総体二次と重ならないのは ${cur.t12Only} 校）` },
    { h: "上のどちらでもない学校", conf: "決まり不明", ok: false, past: "毎年1〜7校。関東予選や新人戦の成績が関係しそうだが、決まりは分からない", now: `2026年度は ${cur.other.map(nm).join("・") || "なし"}` },
  ];
  const L = E.lower;
  const notRules = [
    `関東予選に出ただけでは免除にならない。2026年度の関東予選 ${E.kantoN} 校のうち ${E.kantoInFirst.length} 校は1次予選に出ている（${E.kantoInFirst.join("・")}）。早大学院は関東予選でベスト8まで進んでも1次予選から。`,
    `T3〜T5 にいるだけでも免除にならない。1次予選に出ているのは T3 ${L.T3.inFirst}/${L.T3.n}校、T4 ${L.T4.inFirst}/${L.T4.n}校、T5 ${L.T5.inFirst}/${L.T5.n}校。`,
  ];
  return h("section", { class: "sec", id: "why" },
    h("div", { class: "sec-head" }, h("h2", {}, "なぜ1次予選が免除されたのか"), h("p", {}, "過去の組み合わせ表から割り出した決まり")),
    h("p", { class: "prose" }, `2026年度の1次予選に出る ${X.nFirst} 校の中に名前が無い強豪が、2次予選から出てきます。高体連は免除の決まりを公開していない（大会ページ・組み合わせ表・報道で見つからなかった）ため、2022〜2026年度の組み合わせ表と照らし合わせて決まりを割り出しました。`),
    h("div", { class: "rules" }, rules.map((r, i) => h("div", { class: "rule" + (r.ok ? "" : " open") },
      h("div", { class: "rh" }, h("span", { class: "no num" }, i + 1), h("b", {}, r.h), h("span", { class: "chip " + (r.ok ? "them" : "warn") }, r.conf)),
      h("p", { class: "small" }, r.past), h("p", { class: "small muted" }, r.now)))),
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", { class: "n" }, "年度"), h("th", { class: "n" }, "1次予選"), h("th", { class: "n" }, "免除"), h("th", { class: "n" }, "① 総体二次"), h("th", { class: "n" }, "② T1・T2（①以外）"), h("th", {}, "③ どちらでもない"))),
      h("tbody", {}, [...Y].reverse().map((y) => h("tr", { class: y.estimated ? "hl" : null }, h("td", { class: "n" }, y.year + (y.estimated ? "（推定）" : "")), h("td", { class: "n" }, `${y.fromFirst}校`), h("td", { class: "n" }, `${y.exempt}校`),
        h("td", { class: "n" }, `${y.so2Exempt}/${y.so2}`), h("td", { class: "n" }, y.t12Only == null ? "記録なし" : `${y.t12Only}校`),
        h("td", {}, y.otherKnown ? (y.other.join("・") || "―") : h("span", { class: "muted" }, `${y.other.length}校（T1・T2 の記録が無く①以外をまとめて表示）: ${y.other.join("・")}`))))))),
    h("h3", {}, "免除にならないもの"),
    h("ul", { class: "points" }, notRules.map((r) => h("li", {}, r))),
    h("p", { class: "small muted" }, "①は4年とも、②は2年とも例外が無いので、今年も当てはまるとみています。③の決まりは分からないので、2次予選の組み合わせ（9/23ごろ）で確かめます。"));
}

const TLS = { seed: "免除", first: "1次", club: "クラブ", sub: "控え" };
function tleagueSection(X) {
  const cnt = (st) => X.tleague.reduce((a, g) => a + g.rows.filter((r) => r.status === st).length, 0);
  return h("section", { class: "sec", id: "tl" },
    h("div", { class: "sec-head" }, h("h2", {}, "Tリーグ 2026 全チーム"), h("p", {}, "T1〜T5。選手権での扱い")),
    h("div", { class: "legend" }, h("span", {}, h("span", { class: "tag" }, "免除"), ` 2次予選から（${cnt("seed")}）`), h("span", {}, h("span", { class: "tag first" }, "1次【N】"), ` 1次予選のブロック（${cnt("first")}）`),
      h("span", {}, h("span", { class: "tag club" }, "クラブ"), ` 選手権に出ない（${cnt("club")}）`), h("span", {}, h("span", { class: "tag club" }, "控え"), ` B・Cチームなど。選手権は学校で1チーム（${cnt("sub")}）`)),
    h("div", { class: "tlgrid" }, X.tleague.map((g) => h("div", { class: "card tlc" },
      h("h3", {}, g.league, g.block ? h("small", {}, ` ${g.block}`) : null),
      h("ol", { class: "tl" }, g.rows.map((r) => h("li", { class: r.status },
        h("span", { class: "rk num" }, r.rank), h("span", { class: "tm" }, r.team),
        h("span", { class: "tag " + (r.status === "seed" ? "" : r.status === "first" ? "first" + (r.key === D.me ? " me" : "") : "club") }, r.label))))))));
}

function firstRoundSection(X) {
  const alive = X.firstRound.reduce((a, b) => a + b.teams.filter((t) => !t.out).length, 0);
  return h("section", { class: "sec", id: "first" },
    h("div", { class: "sec-head" }, h("h2", {}, `1次予選 全${X.firstRound.length}ブロック・${X.nFirst}校`), h("p", {}, `各ブロックの勝者（計${X.firstRound.length}校）が2次予選へ。取り消し線は敗退（現在 ${alive} 校が勝ち残り）`)),
    h("div", { class: "frgrid" }, X.firstRound.map((b) => h("div", { class: "card frb" + (b.no === X.myBlock ? " mine" : "") },
      h("div", { class: "frh" }, h("b", { class: "num" }, `【${b.no}】`), b.no === X.myBlock ? h("span", { class: "chip us" }, "武蔵丘の山") : null, h("span", { class: "small muted" }, b.winner ? `勝者 ${b.winner}` : `${b.played}/${b.matches}試合終了`)),
      h("ul", {}, b.teams.map((t) => h("li", { class: (t.out ? "out" : "") + (t.key === D.me ? " me" : "") }, t.key, t.tl ? h("span", { class: "tag first" }, t.tl) : null)))))),
    h("p", { class: "small muted" }, "学校名は名寄せ後の表記。T1〜T5 の印はトップチームの所属。結果は高体連の組み合わせ表（取得時点）による。"));
}

function openSeed(rank) { const d = document.getElementById(`s-${rank}`); if (d) { d.open = true; d.scrollIntoView({ block: "start" }); } }

function seedCard(t) {
  const c = t.league.cur, S = t.scores;
  const meter = (lab, v, r) => h("div", { class: "part" }, h("span", { class: "k" }, lab), h("div", { class: "meter them" }, h("i", { style: `width:${v ?? 0}%` })), h("span", { class: "num" }, v == null ? "―" : `${Math.round(v)}`), h("span", { class: "r muted" }, r ? `${r}位` : ""));
  const head = h("summary", {},
    h("span", { class: "rk num" }, t.rank),
    h("span", { class: "nm" }, h("b", {}, t.display), h("span", { class: "sub small muted" }, [t.area ? `第${t.area.area}地区・${t.area.city}` : null, lgText(c) + (c.n ? `/${c.n}` : "")].filter(Boolean).join("　"))),
    h("span", { class: "tot num" }, S.total.toFixed(1), h("small", {}, "点")),
    h("span", { class: "vs num" }, pct(t.vsMe), h("small", {}, "勝つ見込み")));
  const body = h("div", { class: "seed-body" });
  const ex = t.exempt;
  const why = h("div", { class: "exwhy" },
    h("div", { class: "rh" }, h("b", {}, "1次予選が免除された理由"), h("span", { class: "tags" }, ex.tags.map((g) => h("span", { class: "tag " + (g.tag === "その他" ? "warn" : "") }, g.tag)))),
    h("ul", { class: "points" }, ex.tags.map((g) => h("li", {}, g.text)), ex.facts.map((f) => h("li", { class: "muted" }, f))));
  // 左: 糸口・大会の成績
  const left = h("div", { class: "stack" },
    h("div", { class: "stack", style: "gap:8px" }, h("h3", {}, "攻略の糸口"), h("ul", { class: "points us" }, t.clues.map((p) => h("li", { html: p })))),
    h("div", { class: "stack", style: "gap:8px" }, h("h3", {}, "大会の成績"),
      h("div", { class: "tbl" }, h("table", { class: "tourn" }, h("thead", {}, h("tr", {}, h("th", {}, "年度"), SERIES.map(([, lab]) => h("th", {}, lab)))),
        h("tbody", {}, Object.entries(t.tourn).sort((a, b) => b[0] - a[0]).map(([y, row]) => h("tr", {}, h("td", { class: "n" }, y),
          SERIES.map(([s]) => { const v = row[s]; return h("td", { class: v && v.top ? "top" : null, title: v ? v.path : null }, v ? v.text : "―", v && v.exempt ? h("span", { class: "ex" }, "1次免除") : null); }))))))),
    t.h2h.length ? h("p", { class: "small" }, "武蔵丘との直接対戦: ", t.h2h.map((g) => `${g.year}年度 ${g.series} ${g.round} 武蔵丘 ${scoreText(g)}（${g.res}）`).join("、")) : null);
  // 右: 点数・リーグ・つながり
  const L = t.league;
  const lgBox = h("div", { class: "card" }, h("h3", {}, "今季のリーグ"),
    h("dl", { class: "kv" },
      h("dt", {}, "今季"), h("dd", {}, c.rank ? `${c.league} ${c.rank}位/${c.n}（${c.w}勝${c.d}分${c.l}敗・得${c.gf} 失${c.ga}）` : c.league),
      L.last ? [h("dt", {}, "昨季"), h("dd", {}, `${L.last.league} ${L.last.rank}位/${L.last.n}`)] : null,
      L.reserves.length ? [h("dt", {}, "控え"), h("dd", {}, L.reserves.join("、"))] : null),
    L.form.length ? h("div", { class: "small" }, "直近の試合 ", h("span", { class: "formstrip", "aria-label": L.form.map((g) => g.res).join("") }, L.form.map((g) => h("span", { class: LRES[g.res], title: `${g.date} ${g.opp} ${g.gf}-${g.ga}` }, g.res)))) : null);
  const right = h("div", { class: "stack" },
    h("div", { class: "card" }, h("h3", {}, "総合点の内訳"),
      meter("強さの点数", S.elo, t.partRank.elo), meter("今季のリーグ", S.league, t.partRank.league), meter("つながり", S.conn, t.partRank.conn),
      h("p", { class: "small muted" }, `強さの点数 ${t.elo}（${D.seeds.nTeamsRated}校中 ${t.eloRank}位）。右の数字は強豪${D.seeds.seeds.length}校の中での順位。`)),
    lgBox);
  body.append(left, right);
  const conn = connectionsSection({ connections: t.conn, display: t.display }, { tag: "h3", title: "武蔵丘とのつながり", n: 3 });
  return h("details", { class: "seed", id: `s-${t.rank}` }, head, h("div", { class: "seed-in" }, why, body, conn));
}

/* ---------- 武蔵丘のページ ---------- */
function renderSelf() {
  const t = D.self, root = $("#app"), br = B[D.me];
  const lg = (t.leagues || [])[0];
  const row = lg && lg.table.find((r) => r.team === lg.teamName);
  root.append(h("div", { class: "masthead" },
    h("div", { class: "crumb" }, h("a", linkAttrs("index"), "ブロック全体"), h("span", { "aria-hidden": "true" }, "›"), h("span", {}, "自チームの分析")),
    h("div", { class: "chips" }, h("span", { class: "chip us" }, "自チーム"), br.area ? h("span", { class: "chip" }, `第${br.area.area}地区・${br.area.city}・${br.area.kind}`) : null, lg ? h("span", { class: "chip" }, lg.league) : null),
    h("h1", {}, h("span", { class: "us" }, t.display), " を知る"),
    h("p", { class: "lead" }, D.selfLead)));

  const S = t.summary;
  root.append(h("div", { class: "kpis" },
    h("div", { class: "kpi" }, h("span", { class: "k" }, "強さの点数"), h("span", { class: "v us" }, t.elo, h("small", {}, `${t.eloRank}位`)), h("span", { class: "note" }, `${D.nTeamsRated}校中。`, eloLink())),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "この山を勝ち抜く見込み"), h("span", { class: "v us" }, pct(br.blockWin)), h("span", { class: "note" }, "2次予選【10】へ")),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "5年間の勝ち（PK勝を含む）"), h("span", { class: "v" }, pct((S.w + S.pkw) / S.n), h("small", {}, `${S.w + S.pkw}/${S.n}`)), h("span", { class: "note" }, `${S.w}勝 ${S.pkw}PK勝 ${S.pkl}PK負 ${S.l}敗`)),
    h("div", { class: "kpi" }, h("span", { class: "k" }, "今季のリーグ"), h("span", { class: "v us" }, row ? `${row.rank}位` : "―", row ? h("small", {}, `/${lg.table.length}`) : null), h("span", { class: "note" }, lg ? lg.league : ""))));

  root.append(h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "数字で見る武蔵丘"), h("p", {}, "2022〜2026年度の公式戦 28試合から")),
    h("div", { class: "insights" }, D.insights.map((it) => h("div", { class: "insight" }, h("div", { class: "fig" }, it.fig), h("div", { class: "h" }, it.head), h("div", { class: "b" }, it.body))))));

  const main = h("div", { class: "stack lg" });
  main.append(bandSection(), goalsChartSection(t));
  main.append(h("section", { class: "sec" }, h("div", { class: "figure" },
    h("div", { class: "cap" }, h("h2", {}, "強さの点数の推移"), h("div", { class: "legend" }, h("span", {}, h("i", { style: "border-color:var(--us)" }), t.display))),
    eloChart([{ name: t.display, hist: t.eloHistory, color: "var(--us)" }]))));
  main.append(leagueSection(t, true), stagesSection(t), gamesSection(t));

  const side = h("aside", { class: "stack side" });
  const opp = h("div", { class: "card" }, h("h2", {}, "この山の相手"), h("p", { class: "small muted" }, "当たる順。学校名で分析ページへ"));
  for (const st of D.road) {
    opp.append(h("div", { class: "stack", style: "gap:5px" }, h("div", { class: "eyebrow" }, `${st.round}・${st.when}`),
      ...st.teams.map((k) => h("div", { style: "display:flex;justify-content:space-between;gap:8px;align-items:baseline" },
        h("a", linkAttrs(D.keyToSlug[k]), nameOf(k)), h("span", { class: "num small" }, `勝つ見込み ${pct(B[k].vsMe)}・当たる ${pct(B[k].meetProb)}`)))));
  }
  side.append(opp, h("div", { class: "card" }, h("h2", {}, "5年間の数字"), fiveYearKV(t.summary, t.recent)));
  root.append(h("div", { class: "split" }, main, side));
}

function bandSection() {
  const rows = D.bands;
  return h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", {}, "相手の強さ別の成績"), h("p", {}, "試合の時点の強さの点数で比べ、差が50点を超える相手を格上・格下としています")),
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "相手"), h("th", { class: "n" }, "試合"), h("th", { class: "n" }, "勝"), h("th", { class: "n" }, "PK勝"), h("th", { class: "n" }, "PK負"), h("th", { class: "n" }, "負"), h("th", { style: "width:34%" }, "勝ちの割合（PK勝を含む）"))),
      h("tbody", {}, rows.map((r) => h("tr", {}, h("td", { style: "font-weight:700" }, r.band), h("td", { class: "n" }, r.n), h("td", { class: "n" }, r.w), h("td", { class: "n" }, r.pkw), h("td", { class: "n" }, r.pkl), h("td", { class: "n" }, r.l),
        h("td", {}, h("div", { style: "display:grid;grid-template-columns:1fr 3.2em;gap:8px;align-items:center" }, h("div", { class: "meter" }, h("i", { style: `width:${r.n ? ((r.w + r.pkw) / r.n) * 100 : 0}%` })), h("span", { class: "num" }, r.n ? pct((r.w + r.pkw) / r.n) : "―")))))))),
    h("p", { class: "small muted" }, D.bandNote));
}

function goalsChartSection(t) {
  const years = Object.keys(t.byYear).sort();
  const W = 620, H = 250, L = 40, R = 16, TOP = 16, BOT = 34;
  const vmax = Math.ceil(Math.max(...years.flatMap((y) => [t.byYear[y].gfPer, t.byYear[y].gaPer])) + 0.5);
  const band = (W - L - R) / years.length, bw = Math.min(28, band * 0.28);
  const y = (v) => TOP + ((vmax - v) * (H - TOP - BOT)) / vmax;
  const svg = s("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "年度ごとの1試合平均の得点と失点" });
  for (let v = 0; v <= vmax; v += 1) { svg.append(s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: v === 0 ? "var(--rule-strong)" : "var(--rule)" })); svg.append(s("text", { x: L - 8, y: y(v) + 4, "text-anchor": "end" }, v)); }
  years.forEach((yr, i) => {
    const cx = L + band * i + band / 2, d = t.byYear[yr];
    const bar = (x0, v, col) => (v < 0.15 ? s("g") : s("path", { d: `M${x0},${y(0)} V${y(v) + 4} a4,4 0 0 1 4,-4 h${bw - 8} a4,4 0 0 1 4,4 V${y(0)} z`, fill: col }));
    const xa = cx - bw - 1, xb = cx + 1;
    svg.append(bar(xa, d.gfPer, "var(--us)"), bar(xb, d.gaPer, "var(--them)"));
    svg.append(s("text", { x: xa + bw / 2, y: y(d.gfPer) - 6, "text-anchor": "middle", class: "val" }, d.gfPer.toFixed(1)));
    svg.append(s("text", { x: xb + bw / 2, y: y(d.gaPer) - 6, "text-anchor": "middle" }, d.gaPer.toFixed(1)));
    svg.append(s("text", { x: cx, y: H - 12, "text-anchor": "middle" }, `${yr}年度`));
    const hit = s("rect", { x: cx - band / 2, y: TOP, width: band, height: H - TOP - BOT, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => showTip(ev, `${yr}年度（${d.n}試合）<br>得点 <b>${d.gfPer}</b>／試合<br>失点 <b>${d.gaPer}</b>／試合<br>${d.w}勝 ${d.pkw}PK勝 ${d.pkl}PK負 ${d.l}敗`));
    hit.addEventListener("mouseleave", hideTip);
    svg.append(hit);
  });
  return h("section", { class: "sec" }, h("div", { class: "figure" },
    h("div", { class: "cap" }, h("h2", {}, "年度ごとの得点と失点"), h("div", { class: "legend" }, h("span", {}, h("i", { class: "box", style: "background:var(--us)" }), "1試合平均の得点"), h("span", {}, h("i", { class: "box", style: "background:var(--them)" }), "1試合平均の失点"))),
    svg, h("p", { class: "small muted" }, "2026年度は総体の2試合だけです。")));
}

/* ---------- 起動 ---------- */
renderTopbar();
renderSidenav();
if (D.page === "hub") renderHub(); else if (D.page === "team") renderTeam(); else if (D.page === "seeds") renderSeeds(); else if (D.page === "second") renderSecond(); else renderSelf();
$("#app").prepend(pager());  // 前後のページはページの上に置く（下まで読まないと次へ進めない、という指摘を受けて）
fillToc();
document.body.append(h("footer", { class: "foot" }, `データ: ${D.asOf}。強さの点数と見込みは過去の公式戦から計算した目安です。`));

/* ---------- ブロック決勝の分析（城東戦） ---------- */
function planSections(opts) {
  const F = D.final, out = [];
  if (!F) return out;
  const src = (u, label) => (u ? h("a", { href: u, target: "_blank", rel: "noopener", class: "srclink" }, label || "出典") : null);

  if (opts.verdict) {
    out.push(h("section", { class: "sec verdict" },
      h("div", { class: "sec-head" }, h("h2", {}, "結論から"), h("p", {}, D.over ? "1次予選 総括" : "ブロック決勝 9/22(火) 12:00")),
      h("p", { class: "vline" }, F.verdict.line),
      h("p", { class: "prose" }, F.verdict.body)));
  }

  if (opts.myths) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, "城東の数字を解剖する"), h("p", {}, "印象と実態のずれ")),
      h("div", { class: "myths" }, F.myths.map((m) => h("div", { class: "myth" },
        h("div", { class: "mh" }, h("span", { class: "tag warn" }, "よく言われる"), h("b", {}, m.claim)),
        h("div", { class: "mr" }, h("span", { class: "num big" }, m.num), h("b", {}, m.reality)),
        h("p", { class: "small" }, m.body))))));
  }

  if (opts.style && F.style) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, F.style.title), h("p", {}, "観戦記事に残っている記述から")),
      h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, ""), h("th", {}, "要点"), h("th", {}, "根拠"))),
        h("tbody", {}, F.style.points.map((p) => h("tr", {},
          h("td", {}, h("b", {}, p.k)),
          h("td", {}, p.v, h("span", { class: "yr" }, p.year)),
          h("td", { class: "q" }, p.q, " ", src(p.src))))))),
      h("p", { class: "small muted prose" }, F.style.caveat)));
  }

  if (opts.clock && F.clock) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, F.clock.title), h("p", {}, "いつ点が入るか")),
      h("p", { class: "prose" }, F.clock.lead),
      h("ul", { class: "clock" }, F.clock.rows.map((r) => h("li", {},
        h("b", { class: "num" }, r.when), h("span", {}, r.what), h("span", { class: "small muted" }, r.note)))),
      h("p", { class: "prose hi" }, F.clock.conclusion),
      h("p", { class: "small" }, src(F.clock.src, "得点時間の出典: 城東サッカー部 公式サイト"))));
  }

  if (opts.keys) {
    out.push(h("section", { class: "sec", id: "plan" },
      h("div", { class: "sec-head" }, h("h2", {}, "武蔵丘の勝ち筋"), h("p", {}, `${F.keys.length}つ`)),
      h("ol", { class: "plan" }, F.keys.map((k) => h("li", {},
        h("span", { class: "no num" }, k.n),
        h("div", {}, h("b", {}, k.title), h("p", { class: "small" }, k.body),
          h("ul", { class: "ev" }, k.ev.map((e) => h("li", {}, e)))))))));
  }

  if (opts.risks) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, "警戒すること"), h("p", {}, "都合のいい話だけではない")),
      h("div", { class: "risks" }, F.risks.map((r) => h("div", { class: "risk" }, h("b", {}, r.title), h("p", { class: "small" }, r.body))))));
  }

  if (opts.conditions && F.conditions) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, "試合の条件"), h("p", {}, F.conditions.headline)),
      h("div", { class: "tbl" }, h("table", {}, h("tbody", {}, F.conditions.items.map((it) => h("tr", {},
        h("td", {}, h("b", {}, it.k)), h("td", {}, it.v, h("span", { class: "small muted blk" }, it.note, " ", src(it.src))))))))
      , h("p", { class: "small muted prose" }, F.conditions.caution)));
  }

  if (opts.edge && F.ourEdge) {
    out.push(h("section", { class: "sec" },
      h("div", { class: "sec-head" }, h("h2", {}, "武蔵丘が握っているもの"), h("p", {}, "同じ物差しで並べる")),
      h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, ""), h("th", { class: "n" }, "武蔵丘"), h("th", { class: "n" }, "城東"), h("th", {}, ""))),
        h("tbody", {}, F.ourEdge.map((e) => h("tr", {}, h("td", {}, h("b", {}, e.k)), h("td", { class: "n us" }, e.us), h("td", { class: "n" }, e.them), h("td", { class: "small muted" }, e.note))))))));
  }
  return out;
}

/* ---------- 終わった試合の総評 ---------- */
function reviewSection(key) {
  const r = D.final && D.final.reviews && D.final.reviews[key];
  if (!r) return null;
  return h("section", { class: "sec review" },
    h("div", { class: "sec-head" }, h("h2", {}, "総評"), h("p", {}, r.when)),
    h("p", { class: "vline" }, r.title),
    ...r.body.split(/\n{2,}/).map((x) => h("p", { class: "prose" }, x)),
    h("ul", { class: "points" }, r.points.map((p) => h("li", {}, p))));
}

/* ---------- ジャイアントキリングランキング（1次予選） ---------- */
function upsetsSection() {
  const U = D.upsets;
  if (!U || !U.upsets) return null;
  const list = U.upsets.filter((x) => !x.thin);
  const solo = list.filter((x) => !x.pk);
  const myIdx = solo.findIndex((x) => x.winner === D.me);
  const nm = (k) => (B[k] ? B[k].display.replace("都・", "") : k);
  const row = (x, i, rank) => h("li", { class: x.winner === D.me ? "mine" : null },
    h("b", { class: "rk num" }, rank),
    h("span", { class: "p num" }, pct(x.p, 1)),
    h("span", { class: "vs" }, h("b", {}, nm(x.winner)), h("small", { class: "num" }, x.winnerElo),
      h("i", { class: "sc num" }, x.score), h("span", {}, nm(x.loser)), h("small", { class: "num" }, x.loserElo)),
    h("span", { class: "small muted" }, `${x.round}・点差 ${-x.gap}${x.pk ? "・PK戦" : ""}`));
  const top = solo.slice(0, 10).map((x, i) => row(x, i, i + 1));
  if (myIdx >= 10) top.push(h("li", { class: "gapline" }, "…"), row(solo[myIdx], myIdx, myIdx + 1));
  const pks = list.filter((x) => x.pk).slice(0, 5);
  return h("section", { class: "sec", id: "gk" },
    h("div", { class: "sec-head" }, h("h2", {}, "ジャイアントキリング番付"), h("p", {}, "第105回 選手権 東京 1次予選")),
    h("p", { class: "prose" }, `試合前の「勝つ見込み」が低かった側が勝った試合を、見込みの低い順に並べました。90分で決着したものが${solo.length}件。`
      + (myIdx >= 0 ? `武蔵丘の学習院戦は${myIdx + 1}位です。` : "")),
    D.final && D.final.upsetsHighlight ? h("p", { class: "prose hi" }, D.final.upsetsHighlight) : null,
    h("ol", { class: "gk" }, top),
    pks.length ? h("details", { class: "more" }, h("summary", {}, `PK戦で決まった番狂わせ（${list.filter((x) => x.pk).length}件）`),
      h("div", { class: "body" }, h("ol", { class: "gk" }, pks.map((x, i) => row(x, i, i + 1))))) : null,
    h("p", { class: "small muted prose" }, D.final && D.final.upsetsNote));
}

/* ---------- ブロック決勝の答え合わせ ---------- */
function postmortemSection() {
  const P = D.final && D.final.postmortem;
  if (!P) return null;
  const mark = (v) => h("span", { class: "vd " + (v === "×" ? "no" : v === "△" ? "half" : v === "—" ? "na" : "yes") }, v);
  return h("section", { class: "sec", id: "pm" },
    h("div", { class: "sec-head" }, h("h2", {}, P.title), h("p", {}, "立てたプランと、実際")),
    h("p", { class: "prose" }, P.lead),
    h("p", { class: "vline" }, P.verdictLine),
    h("ul", { class: "pmlist" }, P.keys.map((k) => h("li", {},
      mark(k.v), h("div", {}, h("b", {}, `${k.n}. ${k.t}`), h("p", { class: "small" }, k.r))))),
    h("h3", {}, "外した読み"),
    h("div", { class: "myths" }, P.missed.map((m) => h("div", { class: "myth" },
      h("div", { class: "mh" }, h("span", { class: "tag warn" }, "こう読んだ"), h("b", {}, m.claim)),
      h("div", { class: "mr" }, h("b", {}, m.fact))))),
    h("h3", {}, "当たった読み"),
    h("div", { class: "risk hit" }, h("b", {}, P.hit.claim), h("p", { class: "small" }, P.hit.fact)),
    h("div", { class: "card model" }, h("h3", {}, P.model.title),
      h("p", { class: "prose" }, P.model.body), h("p", { class: "prose" }, P.model.why)));
}

/* ---------- 武蔵丘の5年 ---------- */
function journeySection() {
  const J = D.final && D.final.journey;
  if (!J) return null;
  const W = J.walls;
  return h("section", { class: "sec", id: "journey" },
    h("div", { class: "sec-head" }, h("h2", {}, J.title), h("p", {}, "2022年度からの公式戦31試合")),
    h("p", { class: "prose" }, J.lead),
    h("ol", { class: "years" }, J.years.map((y) => h("li", {},
      h("b", { class: "num yr2" }, y.y),
      h("div", {}, h("div", { class: "yhead" }, h("span", { class: "num elo" }, y.elo), h("span", { class: "small muted" }, y.rec)),
        h("p", { class: "small" }, y.note))))),
    h("h3", {}, W.title),
    h("p", { class: "prose" }, W.body),
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "年度"), h("th", {}, "舞台"), h("th", {}, "結果"), h("th", { class: "n" }, "相手との点差"))),
      h("tbody", {}, W.rows.map((r) => h("tr", { class: r.y === "2026" ? "hl us" : null },
        h("td", { class: "n" }, r.y), h("td", {}, r.s), h("td", {}, r.r), h("td", { class: "n" }, r.gap)))))),
    h("p", { class: "prose hi" }, W.sting),
    h("h3", {}, J.bright.title),
    h("ul", { class: "points us" }, J.bright.points.map((p) => h("li", { html: p }))));
}

/* ---------- 数字で見る今大会 ---------- */
function thisYearSection() {
  const T = D.final && D.final.thisYear;
  if (!T) return null;
  return h("section", { class: "sec" },
    h("div", { class: "sec-head" }, h("h2", {}, T.title), h("p", {}, "第105回 選手権 東京都1次予選")),
    h("div", { class: "tbl" }, h("table", {}, h("tbody", {}, T.rows.map((r) => h("tr", {},
      h("td", {}, h("b", {}, r.k)), h("td", { class: "n big2" }, r.v), h("td", { class: "small muted" }, r.n)))))));
}

/* ---------- 外から見た武蔵丘（記事・掲示板・SNS） ---------- */
function outsideSection() {
  const O = D.final && D.final.outside;
  if (!O || !(O.items || []).length) return null;
  return h("section", { class: "sec", id: "outside" },
    h("div", { class: "sec-head" }, h("h2", {}, O.title), h("p", {}, "外の記録に残っていたこと")),
    O.lead ? h("p", { class: "prose" }, O.lead) : null,
    h("div", { class: "tbl" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "出どころ"), h("th", {}, "分かったこと"))),
      h("tbody", {}, O.items.map((x) => h("tr", {},
        h("td", {}, h("b", {}, x.k), x.date ? h("span", { class: "small muted blk" }, x.date) : null),
        h("td", {}, x.v, x.src ? h("span", { class: "small blk" }, h("a", { href: x.src, target: "_blank", rel: "noopener" }, "出典")) : null)))))),
    O.none ? h("p", { class: "small muted prose" }, O.none) : null);
}

/* ---------- 2次予選（都大会）のトーナメント ---------- */
function renderSecond() {
  const S = D.second, root = $("#app");
  const nm = (k) => k.replace("都・", "");
  root.append(h("div", { class: "masthead" },
    h("div", { class: "eyebrow" }, "第105回全国高校サッカー選手権 東京大会 2次予選"),
    h("h1", {}, "都大会の", h("span", { class: "us" }, `${S.nTeams}校`), " を読む"),
    h("p", { class: "lead" }, `1次予選を勝ち上がった34校と、1次予選を免除された33校。合わせて${S.nTeams}校が10月から都大会を戦います。`
      + "武蔵丘はここに届きませんでしたが、倒した相手と倒された相手がどこまで行くのかは、この表で追えます。"),
    h("p", { class: "lead" }, "強さの点数から、1試合ずつの勝つ見込みを掛け合わせて、山を勝ち抜く確率と優勝確率を出しました。")));

  const top = S.teams.slice(0, 3);
  root.append(h("div", { class: "kpis" },
    ...top.map((t, i) => h("div", { class: "kpi" },
      h("span", { class: "k" }, `優勝確率 ${i + 1}位`),
      h("span", { class: "v" + (i ? "" : " us") }, pct(t.title, 1)),
      h("span", { class: "note" }, `${nm(t.key)}（点数 ${t.elo}・${t.blockName}）`))),
    (() => { const j = S.teams.find((x) => x.key === "城東"); if (!j) return null;
      return h("div", { class: "kpi" }, h("span", { class: "k" }, "武蔵丘を倒した城東"),
        h("span", { class: "v them" }, `${j.rank}位`, h("small", {}, `/${S.nTeams}`)),
        h("span", { class: "note" }, `点数 ${j.elo}・${j.blockName}。山を勝ち抜く見込みは ${pct(j.blockWin, 2)}で、同じ山に実践学園と帝京がいる`)); })()));

  const main = h("div", { class: "stack lg" });

  // 公式トーナメント表 ＋ 勝ち上がり予想の赤線
  main.append(h("section", { class: "sec", id: "bracket" },
    h("div", { class: "sec-head" }, h("h2", {}, "トーナメント表と勝ち上がり予想"), h("p", {}, "高体連の組み合わせ表に、予想の勝ち上がりを赤で重ねた")),
    h("p", { class: "prose" }, "赤い線は「強さの点数で見込みの高いほうが勝つ」とたどった経路です。"
      + `この読みでいくと、4つの山を抜けるのは ${S.predWinners.map(nm).join("・")} になります。`),
    h("figure", { class: "bracket-img" },
      h("a", { href: D.assets.pdf, target: "_blank", rel: "noopener" },
        h("img", { src: D.assets.png, alt: "第105回選手権 東京大会 2次予選のトーナメント表。予想の勝ち上がりを赤線で重ねたもの", loading: "lazy" })),
      h("figcaption", { class: "small muted" }, "高体連 2026/9/23 版の組み合わせ表に赤線を重ねたもの。画像を押すと同じ内容のPDFが開きます。",
        h("a", { href: "https://tokyosoccer-u18.com/SEN26/sen26_2j.pdf", target: "_blank", rel: "noopener" }, " 公式PDF"))),
    h("p", { class: "small muted prose" }, "11/15 のブロック決勝の横線だけは、PDFの線をうまく読み取れず赤を引けていません。"
      + "そこまでの勝ち上がりは赤でたどれます。")));

  // 出場校ランキング
  const max = S.teams[0].title;
  main.append(h("section", { class: "sec", id: "rank" },
    h("div", { class: "sec-head" }, h("h2", {}, "出場校ランキング"), h("p", {}, `${S.nTeams}校を強さの点数の順に`)),
    h("div", { class: "tbl" }, h("table", { class: "rank" },
      h("thead", {}, h("tr", {}, h("th", { class: "n" }, "#"), h("th", {}, "学校"), h("th", { class: "n" }, "点数"),
        h("th", {}, "山"), h("th", {}, "山を勝ち抜く"), h("th", { class: "n" }, "優勝"))),
      h("tbody", {}, S.teams.map((t) => h("tr", { class: t.key === "城東" ? "hl" : null },
        h("td", { class: "n" }, t.rank),
        h("td", { class: "nm" }, nm(t.key), t.key === "城東" ? h("span", { class: "tag" }, "武蔵丘を破った") : null),
        h("td", { class: "n" }, t.elo),
        h("td", { class: "small" }, t.blockName || t.block),
        h("td", {}, h("div", { class: "totcell" }, h("span", { class: "num" }, pct(t.blockWin, 1)),
          h("div", { class: "meter them" }, h("i", { style: `width:${Math.min(100, t.blockWin * 100)}%` })))),
        h("td", { class: "n" }, t.title >= 0.001 ? pct(t.title, 1) : "―")))))),
    h("p", { class: "small muted prose" }, "「山を勝ち抜く」はその4分の1の山で勝ち残る見込み、「優勝」は準決勝・決勝まで勝ち切る見込みです。"
      + "1試合ごとの見込みを掛け合わせたもので、組み合わせの運がそのまま数字に出ます。点数が高くても山が厳しければ優勝確率は下がります。")));

  // ブロックごとの1回戦
  const byBlock = {};
  for (const p of S.firstRound) (byBlock[p.block] = byBlock[p.block] || []).push(p);
  main.append(h("section", { class: "sec", id: "draw" },
    h("div", { class: "sec-head" }, h("h2", {}, "1回戦の組み合わせ"), h("p", {}, "4つの山・左の数字はその校が勝つ見込み")),
    h("div", { class: "blocks" }, Object.keys(byBlock).map((b) => h("div", { class: "blk" },
      h("h3", {}, byBlock[b][0].blockName || `第${b}ブロック`),
      h("ul", { class: "draw" }, byBlock[b].map((p) => h("li", { class: p.a === "城東" || p.b === "城東" ? "mine" : null },
        p.b
          ? [h("span", { class: "t" + (p.p >= 0.5 ? " win" : "") }, nm(p.a)), h("b", { class: "num" }, pct(p.p)),
             h("span", { class: "t" + (p.p < 0.5 ? " win" : "") }, nm(p.b))]
          : [h("span", { class: "t win" }, nm(p.a)), h("b", { class: "num" }, "―"), h("span", { class: "small muted" }, "1回戦なし")]))))))));

  const side = h("aside", { class: "stack side" });
  const blkTop = {};
  for (const t of S.teams) if (!blkTop[t.block] || t.blockWin > blkTop[t.block].blockWin) blkTop[t.block] = t;
  side.append(h("div", { class: "card" }, h("h2", {}, "山ごとの本命"),
    h("dl", { class: "kv" }, Object.keys(blkTop).flatMap((b) => [h("dt", {}, blkTop[b].blockName || `第${b}ブロック`), h("dd", {}, `${nm(blkTop[b].key)} ${pct(blkTop[b].blockWin, 1)}`)]))));
  side.append(h("div", { class: "card" }, h("h2", {}, "この数字の読み方"),
    h("ul", { class: "points" },
      h("li", {}, "強さの点数は、過去5年の公式戦4,040試合と今季のリーグ戦から計算したもの。2次予選に出る67校は、1次予選を戦った学校より試合数が多く、点数の精度も高い"),
      h("li", {}, "優勝確率を足すと100%になります。山の組み合わせを1試合ずつ掛け合わせているためです"),
      h("li", {}, "会場・日程・けが人・当日のメンバーは入っていません。あくまで過去の結果からの目安です"),
      h("li", {}, h("b", {}, "狛江はなぜ1次予選にいないのか"), "。1次予選を免除された33校の1つです。ただし免除の条件として割り出せた2つ"
        + "（その年の総体二次トーナメントに出た／TリーグのT1・T2に所属）のどちらにも当てはまりません。狛江は今季T3で、総体は一次トーナメントのブロック決勝で創価に0-1。"
        + "毎年1〜7校いる「条件では説明のつかない免除校」の1つで、高体連は免除の決まりを公開していません。強さの点数は1926で全体34位と高く、実力で選ばれた可能性はあります"))));
  root.append(h("div", { class: "split" }, main, side));
}
