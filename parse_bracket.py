"""tokyosoccer-u18.com のトーナメント表 PDF から、対戦カード・スコア・勝者を抽出する。

PDF の線はすべて細い塗り矩形として描かれている。これを水平・垂直の線分に戻し、
「試合線（2本の枝が集まる線）＋出口の線」の形を探して試合を復元する。
勝ち上がりは赤で塗られており、試合線のうち勝者側の半分だけが赤くなる。

向きは4通り（左→右 / 右→左 / 下→上 / 上→下）あるので、試合ごとに
「根（決勝）へ向かう方向が X' の正方向」になる正規化座標へ写してから読む。
"""

from __future__ import annotations

import argparse
import json
import re

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

THIN = 3.6  # これ以下の厚みの矩形を線とみなす
C_TOL = 1.3  # 同一直線とみなす座標差
GAP = 3.4  # 同一直線上で連結とみなす隙間（出口の線の太さぶん途切れる。2023年度の赤線は約2.9pt）
J_TOL = 2.6  # 交点・端点判定の許容
ZONE_IN = 36.0  # スコアを探す範囲（試合線から枝の側へ）
ZONE_OUT = 16.0  # スコアを探す範囲（試合線から出口の側へ）
ZONE_OUT_RETRY = 26.0  # スコアが1つも見つからない試合だけ、出口の側をここまで広げて探し直す

MATCHNO = re.compile(r"[【\[［]\s*([0-9０-９]+)\s*[】\]］]")
DATE_LINE = re.compile(r"^(?!\d{4}/)[0-9０-９/,，、・\s~〜月日土火水木金祝()（）予]+$")
DATE_HAS = re.compile(r"\d{1,2}/\d{1,2}|\d{1,2}月\d{1,2}")
INT = re.compile(r"^\d+$")
PK_ANY = re.compile(r"^(\d+)\s*(PK|P|K)\s*(\d+)$")
PK_WRAP = re.compile(r"^(\d+)[（(](\d+)PK(\d+)[）)](\d+)$")  # 「2（5PK3）2」
MIXED = re.compile(r"(\d+|[PK延長])")
KICKOFF = re.compile(r"\d{1,2}[:：]\d{2}")
ADVANCE_CODE = re.compile(r"^[東中南西北]\s*\d+$")  # 支部予選の勝者が入る枠（「中1」など）
BOX_CODE = re.compile(r"^([A-ZＡ-Ｚ]|[東中南西北]\s*\d+)$")  # 勝者が入る次の段階の枠
MARK = re.compile(r"^([A-Za-z]|[①-⑳]|[」「.*×・△〇◎●▲□■]|定)$")
HALF_RE = re.compile(r"^(\d+)-(\d+)$")
ZEN = str.maketrans("０１２３４５６７８９－−‐‑–—―ーｰＰＫ", "0123456789" + "-" * 9 + "PK")
NOTE_WORDS = ("延長", "不戦勝", "不戦敗", "棄権", "没収", "抽選", "中止")
SUB_NOTE = re.compile(r"代表$|シード$|推薦$")
LABEL_JUNK = re.compile(r"^(\d+|[A-Za-zＡ-Ｚ]|[A-Za-z]\d+|延長|不戦勝|不戦敗|棄権|代表|シード|[\dPK延長（）()]+|\d{1,2}[:：]\d{2}|[①-⑳]|[△〇◎●▲]|[東中南西北]\s*\d+|\d+-\d+)$")
NAME_TAIL = re.compile(r"(【[^】]*】|＜[^＞]*＞|<[^>]*>|\d+\.\S*|[△〇◎●▲]+|\d+)$")
NAME_HEAD = re.compile(r"^(\d{4}/\d{1,2}/\d{1,2}|\d+[A-Z]?)")  # 表の作成日やシード番号が名前の前に付くことがある
NAME_NOISE = re.compile(r"[＝=：:]|【|】|こと|会場|開始|用意|用紙|確認|注意|^・.{3,}")


def is_red(c) -> bool:
    return c is not None and len(c) >= 3 and c[0] > 0.8 and c[1] < 0.35 and c[2] < 0.35


# ---------------------------------------------------------------- 線分


@dataclass(eq=False)
class Seg:
    o: str  # 'h' 水平 / 'v' 垂直
    c: float  # 水平なら y、垂直なら x
    a0: float  # 軸方向の始点
    a1: float  # 軸方向の終点
    red: list = field(default_factory=list)  # 赤い区間 [(a0, a1)]
    id: int = 0

    def red_frac(self, lo: float, hi: float) -> float:
        lo, hi = min(lo, hi), max(lo, hi)
        if hi - lo < 0.5:
            return 0.0
        cov = sum(max(0.0, min(hi, r1) - max(lo, r0)) for r0, r1 in self.red)
        return cov / (hi - lo)

    def point(self, a: float) -> tuple[float, float]:
        return (a, self.c) if self.o == "h" else (self.c, a)


def raw_segments(page) -> list[Seg]:
    out: list[Seg] = []

    def add_rect(r, red: bool) -> None:
        w, h = r.x1 - r.x0, r.y1 - r.y0
        if min(w, h) > THIN or max(w, h) < 1.0:
            return
        if w >= h:
            out.append(Seg("h", (r.y0 + r.y1) / 2, r.x0, r.x1, [(r.x0, r.x1)] if red else []))
        else:
            out.append(Seg("v", (r.x0 + r.x1) / 2, r.y0, r.y1, [(r.y0, r.y1)] if red else []))

    def add_line(p, q, red: bool) -> None:
        if abs(p.y - q.y) < 0.6:
            a0, a1 = sorted((p.x, q.x))
            out.append(Seg("h", (p.y + q.y) / 2, a0, a1, [(a0, a1)] if red else []))
        elif abs(p.x - q.x) < 0.6:
            a0, a1 = sorted((p.y, q.y))
            out.append(Seg("v", (p.x + q.x) / 2, a0, a1, [(a0, a1)] if red else []))

    for d in page.get_drawings():
        typ = d.get("type") or ""
        items = d["items"]
        if "f" in typ:
            red = is_red(d.get("fill"))
            if items and all(it[0] == "re" for it in items):
                for it in items:
                    add_rect(it[1], red)
            else:
                add_rect(d["rect"], red)
        if "s" in typ:
            red = is_red(d.get("color"))
            for it in items:
                if it[0] == "l":
                    add_line(it[1], it[2], red)
                elif it[0] == "re" and min(it[1].width, it[1].height) <= THIN:
                    add_rect(it[1], red)
                # 太さのある枠線矩形は名前の囲み。枝ではないので捨てる
    return out


def _union(intervals: list, gap: float) -> list:
    res: list = []
    for a0, a1 in sorted(intervals):
        if res and a0 <= res[-1][1] + gap:
            res[-1] = (res[-1][0], max(res[-1][1], a1))
        else:
            res.append((a0, a1))
    return res


def drop_dashes(segs: list[Seg]) -> list[Seg]:
    """日付の列を区切る点線を取り除く。

    点線の断片は同じ長さで等間隔に並ぶ。試合線と同じ位置に重なることがあり、残すと試合線に連結されて形が崩れる。
    """
    drop: set = set()
    for o in "hv":
        ss = sorted((s for s in segs if s.o == o and not s.red), key=lambda s: (round(s.c * 2), s.a0))
        i = 0
        while i < len(ss):
            run = [ss[i]]
            j = i + 1
            while j < len(ss):
                a, b = run[-1], ss[j]
                gap = b.a0 - a.a1
                if abs(b.c - a.c) < 0.6 and 0.3 < gap < 5 and (b.a1 - b.a0) < 12:
                    run.append(b)
                    j += 1
                else:
                    break
            lens = [s.a1 - s.a0 for s in run]
            regular = len(run) >= 3 and max(lens[:-1]) - min(lens[:-1]) < 1.0
            if regular:
                drop.update(id(s) for s in run)
                i = j
            else:
                i += 1
    return [s for s in segs if id(s) not in drop]


def merge_segments(segs: list[Seg]) -> list[Seg]:
    segs = drop_dashes(segs)
    res: list[Seg] = []
    for o in "hv":
        ss = sorted((s for s in segs if s.o == o), key=lambda s: s.c)
        groups: list[list[Seg]] = []
        for s in ss:
            if groups and s.c - groups[-1][-1].c <= C_TOL:
                groups[-1].append(s)
            else:
                groups.append([s])
        for g in groups:
            g.sort(key=lambda s: s.a0)
            run = [g[0]]
            end = g[0].a1
            for s in g[1:] + [None]:
                if s is not None and s.a0 <= end + GAP:
                    run.append(s)
                    end = max(end, s.a1)
                    continue
                wsum = sum(r.a1 - r.a0 + 0.01 for r in run)
                c = sum(r.c * (r.a1 - r.a0 + 0.01) for r in run) / wsum
                reds = _union([iv for r in run for iv in r.red], GAP)
                res.append(Seg(o, c, min(r.a0 for r in run), max(r.a1 for r in run), reds))
                if s is not None:
                    run, end = [s], s.a1
    for i, s in enumerate(res):
        s.id = i
    return res


def _pos(s: Seg, t: float) -> str:
    if abs(t - s.a0) <= J_TOL:
        return "lo"
    if abs(t - s.a1) <= J_TOL:
        return "hi"
    return "mid"


def attachments(segs: list[Seg]) -> dict[int, list]:
    H = [s for s in segs if s.o == "h"]
    V = [s for s in segs if s.o == "v"]
    att: dict[int, list] = {s.id: [] for s in segs}
    for h in H:
        for v in V:
            if v.a0 - J_TOL <= h.c <= v.a1 + J_TOL and h.a0 - J_TOL <= v.c <= h.a1 + J_TOL:
                ph, pv = _pos(h, v.c), _pos(v, h.c)
                att[h.id].append((v, ph, pv))
                att[v.id].append((h, pv, ph))
    return att


# ---------------------------------------------------------------- 文字


@dataclass
class Tok:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    red: bool
    kind: str = "text"  # text / matchno / date

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def page_tokens(page) -> list[Tok]:
    toks: list[Tok] = []
    raw = page.get_text("rawdict")
    for b in raw["blocks"]:
        for line in b.get("lines", []):
            chars = []
            for s in line["spans"]:
                red = is_red(pymupdf.sRGB_to_pdf(s["color"]))
                for ch in s["chars"]:
                    chars.append((ch["c"], ch["bbox"], s["size"], red))
            if not chars:
                continue
            text = "".join(c[0] for c in chars)
            used = [False] * len(chars)

            def mk(cs, kind="text", t=None):
                return Tok(
                    t if t is not None else "".join(c[0] for c in cs),
                    min(c[1][0] for c in cs),
                    min(c[1][1] for c in cs),
                    max(c[1][2] for c in cs),
                    max(c[1][3] for c in cs),
                    max(c[2] for c in cs),
                    any(c[3] for c in cs),
                    kind,
                )

            stripped = text.strip()
            if DATE_HAS.search(stripped) and DATE_LINE.match(stripped):
                toks.append(mk([c for c in chars if not c[0].isspace()], "date", stripped))
                continue
            for mm in MATCHNO.finditer(text):
                i0, i1 = mm.span()
                num = mm.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
                toks.append(mk(chars[i0:i1], "matchno", num))
                for i in range(i0, i1):
                    used[i] = True
            cur: list = []
            for i, ch in enumerate(chars):
                split = used[i] or ch[0].isspace()
                if not split and cur:
                    pb = cur[-1][1]
                    bb = ch[1]
                    gap = max(bb[0] - pb[2], bb[1] - pb[3])
                    # 「2 0」を空白文字なしで並べている表がある。数字どうしは狭い隙間でも切る
                    both_digits = cur[-1][0].isdigit() and ch[0].isdigit()
                    # 隣の列の縦書きの文字が同じ行に入っていることがある。斜めに並ぶ2文字は切る
                    sz = max(ch[2], 1.0)
                    diagonal = abs((bb[1] + bb[3]) - (pb[1] + pb[3])) / 2 > 0.35 * sz and abs((bb[0] + bb[2]) - (pb[0] + pb[2])) / 2 > 0.35 * sz
                    if diagonal or gap > (0.2 if both_digits else 0.6) * sz:
                        toks.append(mk(cur))
                        cur = []
                if split:
                    if cur:
                        toks.append(mk(cur))
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                toks.append(mk(cur))
    toks = [t for t in toks if t.text.strip()]
    for t in toks:
        if t.kind == "text":
            t.text = t.text.translate(ZEN)
    return merge_split_matchno(toks)


def merge_split_matchno(toks: list[Tok]) -> list[Tok]:
    """「【」「34」「】」が別々の文字列になっている試合番号を1つにまとめる。"""
    opens = [t for t in toks if t.kind == "text" and t.text in ("【", "[", "［")]
    drop: set = set()
    add: list[Tok] = []
    for o in opens:
        same = [t for t in toks if t.kind == "text" and id(t) not in drop and abs(t.cy - o.cy) < 2.5 and 0 < t.x0 - o.x0 < 40]
        close = [t for t in same if t.text in ("】", "]", "］")]
        if not close:
            continue
        c = min(close, key=lambda t: t.x0)
        inner = [t for t in same if t.x0 < c.x0 and INT.match(t.text)]
        if len(inner) != 1:
            continue
        n = inner[0]
        add.append(Tok(n.text, o.x0, min(o.y0, n.y0, c.y0), c.x1, max(o.y1, n.y1, c.y1), n.size, n.red, "matchno"))
        drop.update({id(o), id(n), id(c)})
    return [t for t in toks if id(t) not in drop] + add


# ---------------------------------------------------------------- 試合


def norm(orient: str, x: float, y: float) -> tuple[float, float]:
    """根へ向かう方向を X' の正、枝の並ぶ方向を Y' とする座標。"""
    if orient == "LR":
        return x, y
    if orient == "RL":
        return -x, y
    if orient == "BT":
        return -y, x
    return y, x  # TB


@dataclass(eq=False)
class Match:
    bar: Seg
    s1: Seg
    s2: Seg
    stem: Seg
    p1: str
    p2: str
    p0: str
    orient: str
    id: int = 0
    child: dict = field(default_factory=dict)  # slot -> Match
    leaf: dict = field(default_factory=dict)  # slot -> (x, y)
    parent: "Match | None" = None
    parent_slot: int = 0
    tokens: list = field(default_factory=list)

    @property
    def b(self) -> float:  # 試合線の X'
        x, y = self.bar.point(self.bar.a0)
        return norm(self.orient, x, y)[0]

    @property
    def j(self) -> float:  # 出口の Y'
        return self.stem.c


def find_matches(segs: list[Seg], att: dict) -> list[Match]:
    by_key = {}
    for s in segs:
        by_key.setdefault(s.o, []).append(s)

    def closes(o: str, c: float, lo: float, hi: float) -> bool:
        return any(
            abs(t.c - c) <= J_TOL * 1.5 and abs(t.a0 - lo) <= J_TOL * 1.5 and abs(t.a1 - hi) <= J_TOL * 1.5
            for t in by_key.get(o, [])
        )

    out: list[Match] = []
    for B in segs:
        A = att[B.id]
        lo = [a for a in A if a[1] == "lo"]
        hi = [a for a in A if a[1] == "hi"]
        mid = [a for a in A if a[1] == "mid"]
        if len(lo) != 1 or len(hi) != 1 or len(mid) != 1:
            continue
        (S1, _, p1), (S2, _, p2), (S0, _, p0) = lo[0], hi[0], mid[0]
        if "mid" in (p1, p2, p0):
            continue
        side = lambda p: 1 if p == "lo" else -1  # noqa: E731  交点から線分が伸びる向き
        s1, s2, s0 = side(p1), side(p2), side(p0)
        if not (s1 == s2 == -s0):
            continue
        f1 = S1.a1 if p1 == "lo" else S1.a0
        f2 = S2.a1 if p2 == "lo" else S2.a0
        if abs(f1 - f2) <= J_TOL * 2 and closes(B.o, (f1 + f2) / 2, min(S1.c, S2.c), max(S1.c, S2.c)):
            continue  # 4辺が閉じている＝名前の囲み枠
        if B.o == "v":
            orient = "LR" if s0 > 0 else "RL"
        else:
            orient = "TB" if s0 > 0 else "BT"
        out.append(Match(B, S1, S2, S0, p1, p2, p0, orient))
    for i, m in enumerate(out):
        m.id = i
    return out


def link_tree(matches: list[Match]) -> None:
    stem_of = {m.stem.id: m for m in matches}
    for m in matches:
        for slot, S, p in ((1, m.s1, m.p1), (2, m.s2, m.p2)):
            ch = stem_of.get(S.id)
            if ch is not None and ch is not m:
                m.child[slot] = ch
                ch.parent, ch.parent_slot = m, slot
            else:
                far = S.a1 if p == "lo" else S.a0
                m.leaf[slot] = S.point(far)


# ---------------------------------------------------------------- 読み取り


def leaf_candidates(toks: list[Tok], orient: str, F: tuple[float, float], band: tuple[float, float], used: set, reach_in: float = 0.0) -> list:
    """葉の外側（X' が小さい側）で、Y' が帯に入る文字を近い順に返す。

    reach_in > 0 のときは、枝の線の真上・真下（葉から reach_in まで内側）にある文字も候補にする。
    先頭の学校だけ枝が名前の上を通って表の端まで伸びている表があるため。
    """
    fx, fy = norm(orient, *F)
    cands = []
    for t in toks:
        if t.kind != "text" or id(t) in used:
            continue
        _, ty = norm(orient, t.cx, t.cy)
        if not (band[0] <= ty - fy <= band[1]):
            continue
        ex0, _ = norm(orient, t.x0, t.y0)
        ex1, _ = norm(orient, t.x1, t.y1)
        near = max(ex0, ex1)
        if near > fx + 3 + reach_in or fx - near > 240:
            continue
        cands.append((max(0.0, fx - near), fx - min(ex0, ex1), t))
    cands.sort(key=lambda c: c[0])
    return cands


def chain_reach(cands: list, gap: float) -> float | None:
    """葉から文字をたどり、学校名らしい文字が届く深さを返す。番号やシード記号は数えない。"""
    reach = None
    for near_d, far_d, t in cands:
        if reach is None:
            if near_d > 130:
                break
        elif near_d > reach + max(gap, 1.8 * t.size):
            break
        if not LABEL_JUNK.match(t.text.strip()):
            reach = far_d if reach is None else max(reach, far_d)
    return reach


def leaf_label(cands: list, orient: str, depth: float) -> tuple[str, list]:
    picked = [t for near_d, _, t in cands if near_d <= depth + 4]
    # 表の横の注意書きや試合開始時刻が、学校名の欄の近くに置かれていることがある
    picked = [t for t in picked if not NAME_NOISE.search(t.text)]
    good = [t for t in picked if not LABEL_JUNK.match(t.text.strip()) and not t.red]
    if not good:
        good = [t for t in picked if not LABEL_JUNK.match(t.text.strip())]
    if not good:
        return "", picked
    big = max(t.size for t in good)
    # 「関東第一代表」のような出場経路の注記は、学校名から外して sub に残す
    main = [t for t in good if t.size >= 0.72 * big and not SUB_NOTE.search(t.text)]
    if orient in ("BT", "TB"):
        main.sort(key=lambda t: (round(-t.cx / 8), t.cy))  # 縦書きは右の列から読む
    else:
        main.sort(key=lambda t: (round(t.cy / max(big, 1) * 1.5), t.cx))
    name = "".join(t.text for t in main)
    if not NAME_TAIL.sub("", name).strip():
        # 大きな字の注記にまぎれて、学校名が小さな字で書かれていることがある
        rest = [t for t in good if not SUB_NOTE.search(t.text)]
        rest.sort(key=(lambda t: (round(-t.cx / 8), t.cy)) if orient in ("BT", "TB") else (lambda t: (round(t.cy / 4), t.cx)))
        name, main = "".join(t.text for t in rest), rest
    prev = None
    while prev != name:  # 表の注記が名前の前後に付くことがある（「中大杉並【会場】」「2022/5/4学習院」「都・立川国際中等40」）
        prev, name = name, NAME_HEAD.sub("", NAME_TAIL.sub("", name)).strip()
    # 縦書きの「都・」が別の列に置かれ、後ろに回ることがある（「東大和都・」）
    name = re.sub(r"^(.+?)(都・|私・|国・)$", r"\2\1", name)
    sub = [t.text for t in good if t not in main]
    return name, picked + ([Tok(" / ".join(sub), 0, 0, 0, 0, 0, False, "sub")] if sub else [])


def assign_score_tokens(toks: list[Tok], matches: list[Match], used: set) -> None:
    _assign_score_tokens(toks, matches, used)
    # スコアが出口の側に離して書かれている表がある。数字が1つも無い試合だけ範囲を広げる
    taken = {id(t) for m in matches for t in m.tokens} | used
    for m in matches:
        if any(INT.match(t.text.strip()) for t in m.tokens):
            continue
        for t in toks:
            if id(t) in taken or not INT.match(t.text.strip()):
                continue
            tx, _ = norm(m.orient, t.cx, t.cy)
            dx = tx - m.b
            _, e0 = norm(m.orient, t.x0, t.y0)
            _, e1 = norm(m.orient, t.x1, t.y1)
            if ZONE_OUT < dx <= ZONE_OUT_RETRY and m.bar.a0 - 0.5 <= min(e0, e1) and max(e0, e1) <= m.bar.a1 + 0.5:
                m.tokens.append(t)
                taken.add(id(t))


def _assign_score_tokens(toks: list[Tok], matches: list[Match], used: set) -> None:
    for t in toks:
        if id(t) in used or t.kind == "date":
            continue
        best = None
        # 「P4 / K5」は出口の側、次の枠の手前に離して書かれることがある
        zone_out = ZONE_OUT_RETRY if re.fullmatch(r"[PK]\s*\d+", t.text.strip()) else ZONE_OUT
        for m in matches:
            tx, ty = norm(m.orient, t.cx, t.cy)
            lo, hi = m.bar.a0, m.bar.a1
            dx = tx - m.b
            if not (-ZONE_IN <= dx <= zone_out):
                continue
            if dx <= 0:
                if not (lo - 3 <= ty <= hi + 3):
                    continue
            else:
                # 出口の側は、1段下の試合の枝の側と重なる。試合線の幅に完全に収まる文字だけを取る
                _, e0 = norm(m.orient, t.x0, t.y0)
                _, e1 = norm(m.orient, t.x1, t.y1)
                if not (lo - 0.5 <= min(e0, e1) and max(e0, e1) <= hi + 0.5):
                    continue
            cost = abs(dx) * (1.0 if dx <= 0 else 1.15)
            if best is None or cost < best[0]:
                best = (cost, m)
        if best is not None:
            best[1].tokens.append(t)
            continue
        # 選手権二次の準決勝以降は、出口の線の真下に前半・後半・延長前半・延長後半・PK が縦に並び、
        # 通常の範囲より遠くまで続く。前後半や PK の形の文字だけ、出口の真下に限って遠くまで探す
        txt = t.text.strip()
        if HALF_RE.match(txt) or PK_ANY.match(txt) or txt in ("延長", "PK"):
            for m in matches:
                tx, ty = norm(m.orient, t.cx, t.cy)
                dx = tx - m.b
                if abs(ty - m.j) <= 12 and -80 <= dx <= 0 and (best is None or abs(dx) < best[0]):
                    best = (abs(dx), m)
        elif any(w in txt for w in ("棄権", "不戦", "辞退")):
            # 「棄権」は枝の途中に書かれることがある。試合線の幅の中で、枝の側へ遠くまで探す
            for m in matches:
                tx, ty = norm(m.orient, t.cx, t.cy)
                dx = tx - m.b
                if m.bar.a0 - 3 <= ty <= m.bar.a1 + 3 and -130 <= dx <= 26 and (best is None or abs(dx) < best[0]):
                    best = (abs(dx), m)
        if best is not None:
            best[1].tokens.append(t)


def parse_scores(m: Match) -> dict:
    """試合線の周りの文字から、スコア・PK・前後半・注記を読む。

    数字は試合線からの距離ごとに「段」をなす。出口の側（X' が正）に段があればそれが本スコアで、
    枝の側の段は近い順に前半・後半（・延長前半・延長後半）。出口側に段が無ければ最も近い段が本スコア。
    同じ段に数字が2つあれば、Y' の小さいほうが枠1。1つだけなら出口の位置で枠を決める。
    PK は「0P4 / 0K5」「1PK1 / 1PK4」（枠ごと）、「7PK8」（両チーム）、「0 P 3」（分かち書き）がある。
    """
    res = {"score1": None, "score2": None, "pk1": None, "pk2": None, "halves": [], "notes": [], "match_no": None, "kickoff": None, "marks": []}
    rows: list[tuple[float, int | None, int | None]] = []  # (dX, 枠1, 枠2)
    items: list[tuple[float, float, Tok]] = []  # (dX, Y', tok)
    for t in m.tokens:
        tx, ty = norm(m.orient, t.cx, t.cy)
        txt = t.text.strip()
        if t.kind == "matchno":
            res["match_no"] = txt
            continue
        if KICKOFF.search(txt):
            res["kickoff"] = txt
            continue
        if MARK.match(txt) or ADVANCE_CODE.match(txt):
            res["marks"].append(txt)
            continue
        mm = PK_WRAP.match(txt)
        if mm:
            res["score1"], res["pk1"], res["pk2"], res["score2"] = (int(g) for g in mm.groups())
            return res
        # 「0延2」「P3」のような混在文字列は、文字の位置を按分して部品に割る
        if MIXED.fullmatch(txt) is None and re.fullmatch(r"[\dPK延長]+", txt) and re.search(r"\d", txt) and re.search(r"[PK延長]", txt) and not PK_ANY.match(txt):
            parts = MIXED.findall(txt)
            n = len(txt)
            pos = 0
            for part in parts:
                i0 = txt.index(part, pos)
                pos = i0 + len(part)
                f0, f1 = i0 / n, pos / n
                if m.orient in ("LR", "RL") or (t.x1 - t.x0) >= (t.y1 - t.y0):
                    sub = Tok(part, t.x0 + (t.x1 - t.x0) * f0, t.y0, t.x0 + (t.x1 - t.x0) * f1, t.y1, t.size, t.red, "piece")
                else:
                    sub = Tok(part, t.x0, t.y0 + (t.y1 - t.y0) * f0, t.x1, t.y0 + (t.y1 - t.y0) * f1, t.size, t.red, "piece")
                sx, sy = norm(m.orient, sub.cx, sub.cy)
                items.append((sx - m.b, sy, sub))
            continue
        items.append((tx - m.b, ty, t))

    # 注記は1文字ずつ分かれていることがある（「不 戦 勝」）ので、つないでから探す
    words = "".join(t.text.strip() for _, _, t in sorted(items, key=lambda p: (round(p[2].cx / 6), p[2].cy)) if not INT.match(t.text.strip()))
    words += "".join(t.text.strip() for _, _, t in sorted(items, key=lambda p: (round(p[2].cy / 4), p[2].cx)) if not INT.match(t.text.strip()))
    for w in NOTE_WORDS:
        if w in words:
            res["notes"].append(w)
    if "不戦" in words and "不戦勝" not in res["notes"] and "不戦敗" not in res["notes"]:
        res["notes"].append("不戦勝")  # 縦書きの「不戦勝」は末尾の文字が探す範囲から外れることがある
    if "位決定" in words:
        res["notes"].append("3位決定戦")
    # 「3位決定戦」の「3」のように、文字にくっついた数字はスコアではない
    def glued(t: Tok) -> bool:
        for _, _, u in items:
            if u is t or not u.text.strip() or u.text.strip()[0] not in "位回年月日次地組":
                continue
            below = -1.0 <= u.y0 - t.y1 <= 0.6 * t.size and min(t.x1, u.x1) - max(t.x0, u.x0) > 0
            right = -1.0 <= u.x0 - t.x1 <= 0.4 * t.size and min(t.y1, u.y1) - max(t.y0, u.y0) > 0
            if below or right:
                return True
        return False

    items = [p for p in items if not (INT.match(p[2].text.strip()) and glued(p[2]))]
    if "3位決定戦" in res["notes"]:
        items = [p for p in items if not set(p[2].text.strip()) <= set("3位決定戦")]
    items = [p for p in items if not any(w in p[2].text or p[2].text in w for w in NOTE_WORDS)]

    # PK
    pk_toks = [(dx, ty, t, mm) for dx, ty, t in items if (mm := PK_ANY.match(t.text.strip()))]
    pk_main: dict[int, int] = {}
    if len(pk_toks) == 1 and pk_toks[0][3].group(2) == "PK":
        mm = pk_toks[0][3]
        res["pk1"], res["pk2"] = int(mm.group(1)), int(mm.group(3))
    elif pk_toks:
        pk_toks.sort(key=lambda p: p[1])
        for i, (_, ty, t, mm) in enumerate(pk_toks[:2]):
            letter = mm.group(2)
            k = 1 if letter == "P" else 2 if letter == "K" else (i + 1 if len(pk_toks) >= 2 else (1 if ty < m.j else 2))
            pk_main[k] = int(mm.group(1))
            res[f"pk{k}"] = int(mm.group(3))
    items = [p for p in items if not PK_ANY.match(p[2].text.strip())]
    # 分かち書きの「0 P 3」「0 K 5」：文字 P/K の後ろの数字が PK、前の数字が得点
    # 「0延2」「0長0」：延/長 の前が90分のスコア、後ろが延長を含む最終スコア
    et_main: dict[int, int] = {}
    et_reg: dict[int, int] = {}
    # 延/長 は「0延2」を割った部品のときだけ扱う。単独の「延」「長」は縦書きの「延長」の1文字
    for dx, ty, t in [p for p in items if p[2].text.strip() in ("P", "K") or (p[2].text.strip() in ("延", "長") and p[2].kind == "piece")]:
        letter = t.text.strip()
        k = 1 if letter in ("P", "延") else 2
        line = [p for p in items if abs(p[1] - ty) < 3 and INT.match(p[2].text.strip()) and p in items]
        after = [p for p in line if p[0] > dx]
        before = [p for p in line if p[0] < dx]
        a = min(after, key=lambda p: p[0]) if after else None
        b = max(before, key=lambda p: p[0]) if before else None
        if letter in ("P", "K"):
            if a:
                res[f"pk{k}"] = int(a[2].text)
                items.remove(a)
                if b:
                    pk_main[k] = int(b[2].text)
                    items.remove(b)
        else:
            if "延長" not in res["notes"]:
                res["notes"].append("延長")
            if b:
                et_reg[k] = int(b[2].text)
                items.remove(b)
            if a:
                et_main[k] = int(a[2].text)
                items.remove(a)
    items = [p for p in items if p[2].text.strip() not in ("P", "K", "延", "長")]
    if et_reg or et_main:
        if len(et_reg) == 2:
            rows.append((0.0, et_reg[1], et_reg[2]))  # 90分のスコアは前後半の欄に回す
        if len(et_main) == 2:
            pk_main.update(et_main)
        elif len(et_reg) == 2 and not pk_main:
            pk_main.update(et_reg)

    for dx, ty, t in items:
        mm = HALF_RE.match(t.text.strip())
        if mm:
            rows.append((dx, int(mm.group(1)), int(mm.group(2))))
    # 縦向きの表では2つの数字が出口の線をはさんで左右に並ぶ。ちょうど出口の上にある2桁は「2 0」がくっついたもの
    if m.orient in ("BT", "TB"):
        fixed = []
        for dx, ty, t in items:
            txt = t.text.strip()
            same_row = [p for p in items if p[2] is not t and abs(p[0] - dx) <= 3 and INT.match(p[2].text.strip())]
            if INT.match(txt) and len(txt) == 2 and abs(ty - m.j) < 2.0 and not same_row:
                w = (t.x1 - t.x0) / 2
                fixed.append((dx, ty - w / 2, Tok(txt[0], t.x0, t.y0, t.x0 + w, t.y1, t.size, t.red)))
                fixed.append((dx, ty + w / 2, Tok(txt[1], t.x0 + w, t.y0, t.x1, t.y1, t.size, t.red)))
            else:
                fixed.append((dx, ty, t))
        items = fixed
    # 数字を段にまとめる
    ints = sorted((dx, ty, int(t.text)) for dx, ty, t in items if INT.match(t.text.strip()))
    groups: list[list] = []
    for it in ints:
        if groups and it[0] - groups[-1][-1][0] <= 3.0:
            groups[-1].append(it)
        else:
            groups.append([it])
    for g in groups:
        g.sort(key=lambda p: p[1])
        dx = sum(p[0] for p in g) / len(g)
        if len(g) >= 2:
            rows.append((dx, g[0][2], g[-1][2]))
            if len(g) > 2:
                res["notes"].append("extra:" + ",".join(str(p[2]) for p in g[1:-1]))
        else:
            rows.append((dx, g[0][2], None) if g[0][1] < m.j else (dx, None, g[0][2]))
    others = [t.text.strip() for _, _, t in items if not INT.match(t.text.strip()) and not HALF_RE.match(t.text.strip()) and t.text.strip() not in ("-", "－")]
    if others:
        res["notes"].append("text:" + " ".join(others))

    if pk_main:
        res["score1"], res["score2"] = pk_main.get(1), pk_main.get(2)
        res["halves"] = [f"{a}-{b}" for _, a, b in sorted(rows, key=lambda r: abs(r[0]))]
        return res
    if rows:
        out_rows = [r for r in rows if r[0] > 0.5]
        main = min(out_rows, key=lambda r: r[0]) if out_rows else min(rows, key=lambda r: abs(r[0]))
        # 2つの数字が少しずれた段に書かれていることがある。片側ずつの段が近ければ1つにまとめる
        if (main[1] is None) != (main[2] is None):
            need = 1 if main[1] is None else 2
            mates = [r for r in rows if r is not main and r[need] is not None and r[3 - need] is None and abs(r[0] - main[0]) <= 10]
            if mates:
                mate = min(mates, key=lambda r: abs(r[0] - main[0]))
                rows.remove(mate)
                merged = (main[0], mate[1] if need == 1 else main[1], mate[2] if need == 2 else main[2])
                rows[rows.index(main)] = merged
                main = merged
        res["score1"], res["score2"] = main[1], main[2]
        rest = [r for r in rows if r is not main]
        rest.sort(key=lambda r: abs(r[0]))
        res["halves"] = [f"{'' if a is None else a}-{'' if b is None else b}" for _, a, b in rest]
    return res


def winner_slot(m: Match) -> tuple[int | None, float, float]:
    r1 = m.bar.red_frac(m.s1.c, m.j)
    r2 = m.bar.red_frac(m.j, m.s2.c)
    if r1 > 0.5 and r2 <= 0.5:
        return 1, r1, r2
    if r2 > 0.5 and r1 <= 0.5:
        return 2, r1, r2
    return None, r1, r2


def date_tokens_for(toks: list[Tok], orient: str, b: float) -> str | None:
    """試合線の列の日付。見出しは列の区切り（＝試合線の位置）の枝の側に置かれるので、そちらを優先する。

    左右対称の表では、右半分の見出しが左右反転して並ぶ。近さだけで選ぶと隣の列の日付を取ってしまう。
    """
    best = None
    inside = None
    for t in toks:
        if t.kind != "date":
            continue
        a, _ = norm(orient, t.x0, t.y0)
        c, _ = norm(orient, t.x1, t.y1)
        lo, hi = min(a, c), max(a, c)
        d = 0.0 if lo <= b <= hi else min(abs(b - lo), abs(b - hi))
        if d <= 14 and (best is None or d < best[0]):
            best = (d, t.text)
        if hi <= b + 3 and b - hi <= 14 and (inside is None or b - hi < inside[0]):
            inside = (b - hi, t.text)
    if inside:
        return inside[1]
    return best[1] if best else None


def root_label(toks: list[Tok], m: Match, used: set) -> tuple[str, list[Tok]]:
    far = m.stem.a1 if m.p0 == "lo" else m.stem.a0
    fx, fy = norm(m.orient, *m.stem.point(far))
    found = []
    for t in toks:
        if id(t) in used or t.kind == "date":
            continue
        tx, ty = norm(m.orient, t.cx, t.cy)
        txt = t.text.strip()
        if txt in ("P", "K") or PK_ANY.match(txt) or re.fullmatch(r"[PK]\s*\d+", txt):
            continue  # 決勝の PK を箱の名前と取り違えない
        if abs(ty - fy) <= 14 and 1 <= tx - fx <= 60:
            found.append((tx - fx, t))
    found.sort(key=lambda p: p[0])
    ts = [t for _, t in found[:6]]
    joined = "".join(t.text.strip() for t in sorted(ts, key=lambda t: (round(t.cx / 6), t.cy)))
    if "位決" in joined:
        # 3位決定戦の小さな山。出口の先の「3位決定戦」の縦書き（数字の3を含む）を、「位」と同じ列だけ取る
        col = next(t for t in ts if "位" in t.text)
        return "3位決定戦", [t for t in ts if abs(t.cx - col.cx) < 4 or set(t.text.strip()) <= set("3位決定戦")]
    ts = [t for t in ts if t.kind == "matchno" or not INT.match(t.text.strip())][:3]  # 決勝のスコアを箱の名前と取り違えない
    codes = [t for t in ts if t.kind == "matchno" or BOX_CODE.match(t.text.strip())]
    if codes:
        # 行き先の枠の名前（「南1」「A」「【1】」）が見つかれば、最も近い1つだけを使う
        t = codes[0]
        return (f"【{t.text}】" if t.kind == "matchno" else t.text.strip()), [t]
    if not ts:
        # 枠の名前が箱の上端に書かれている表（東支部の A〜I）。上下に広く探し、枠の名前の形の文字だけ拾う
        far_c = []
        for t in toks:
            if id(t) in used or not BOX_CODE.match(t.text.strip()):
                continue
            tx, ty = norm(m.orient, t.cx, t.cy)
            if -5 <= tx - fx <= 60 and abs(ty - fy) <= 90:
                far_c.append((abs(ty - fy) + abs(tx - fx), t))
        if far_c:
            t = min(far_c, key=lambda p: p[0])[1]
            return t.text.strip(), [t]
    return " ".join(f"【{t.text}】" if t.kind == "matchno" else t.text for t in ts), ts


# ---------------------------------------------------------------- ページ単位


def parse_page(page, pno: int) -> dict:
    segs = merge_segments(raw_segments(page))
    att = attachments(segs)
    matches = find_matches(segs, att)
    link_tree(matches)
    toks = page_tokens(page)

    roots = [m for m in matches if m.parent is None]
    tree_of: dict[int, int] = {}
    for ti, r in enumerate(sorted(roots, key=lambda r: (r.bar.point(r.bar.a0)[1], r.bar.point(r.bar.a0)[0]))):
        stack = [r]
        while stack:
            x = stack.pop()
            tree_of[x.id] = ti
            stack.extend(x.child.values())

    # 学校名を拾う帯：上下で隣り合う葉との中間まで（名前欄が同じ列に並ぶ葉どうしで比べる）
    used: set = set()
    leaves = []
    pts = [(m, slot, F) for m in matches for slot, F in m.leaf.items()]
    normed = [(norm(m.orient, *F), m.orient) for m, _, F in pts]
    bands = []
    for (fx, fy), o in normed:
        ys = sorted(ny for (nx, ny), no in normed if no == o and abs(nx - fx) < 80)
        i = ys.index(fy)
        lo = (ys[i - 1] - fy) / 2 if i > 0 else -26.0
        hi = (ys[i + 1] - fy) / 2 if i + 1 < len(ys) else 26.0
        bands.append((max(lo, -26.0), min(hi, 26.0)))
    cands = [leaf_candidates(toks, m.orient, F, bands[i], used) for i, (m, _, F) in enumerate(pts)]
    # 名前欄の深さ：木ごとに、各葉から名前がどこまで届くかの上位を取る。均等割付の縦書きにも効く
    depth_of_tree: dict[int, float] = {}
    for ti in set(tree_of.values()):
        idx = [i for i, (m, _, _) in enumerate(pts) if tree_of[m.id] == ti]
        gap = 45.0 if pts[idx[0]][0].orient in ("BT", "TB") else 16.0
        reaches = sorted(r for i in idx if (r := chain_reach(cands[i], gap)) is not None)
        depth_of_tree[ti] = reaches[min(len(reaches) - 1, int(len(reaches) * 0.9))] if reaches else 60.0
    for i, (m, slot, F) in enumerate(pts):
        name, picked = leaf_label(cands[i], m.orient, depth_of_tree[tree_of[m.id]])
        if not name:
            # 枝の線が名前の上を通っている形。線の長さの範囲で、線に沿った文字を探す
            S = m.s1 if slot == 1 else m.s2
            wide = leaf_candidates(toks, m.orient, F, bands[i], used, reach_in=(S.a1 - S.a0) * 0.6)
            name, picked = leaf_label(wide, m.orient, depth_of_tree[tree_of[m.id]])
        fx = norm(m.orient, *F)[0]
        for t in picked:
            # 学校名は使用済みにする。番号などは、枝の先より外側にあるもの（学校番号）だけ使用済みにし、
            # 枝の線に沿って見つけた数字はスコアとして残す
            if t.kind == "sub" or not LABEL_JUNK.match(t.text.strip()):
                used.add(id(t))
            elif INT.match(t.text.strip()):
                e = max(norm(m.orient, t.x0, t.y0)[0], norm(m.orient, t.x1, t.y1)[0])
                if e < fx + 3:
                    used.add(id(t))
        leaves.append({"match": m.id, "slot": slot, "name": name, "point": F, "sub": [t.text for t in picked if t.kind == "sub"]})

    # 決勝の出口の先にある箱の名前（「南1」「A」「【1】」など）を先に取り、スコア候補から外す
    roots_label: dict[int, str] = {}
    pairs = facing_pairs(matches, toks)
    facing_ids = {m.id for L, R, _, _ in pairs for m in (L, R)}
    for m in matches:
        if m.parent is None and m.id not in facing_ids:
            lab, ts = root_label(toks, m, used)
            roots_label[m.id] = lab
            used.update(id(t) for t in ts)

    assign_score_tokens(toks, matches, used)

    # 列（ラウンド）: 木ごとに試合線の X' をまとめる
    col_of: dict[int, int] = {}
    ncol_of_tree: dict[int, int] = {}
    for ti in set(tree_of.values()):
        ms = [m for m in matches if tree_of[m.id] == ti]
        xs = sorted({round(m.b, 1) for m in ms})
        cols: list[float] = []
        for x in xs:
            if not cols or x - cols[-1] > 6:
                cols.append(x)
        for m in ms:
            col_of[m.id] = min(range(len(cols)), key=lambda i: abs(cols[i] - m.b)) + 1
        ncol_of_tree[ti] = len(cols)

    leaf_name = {(lf["match"], lf["slot"]): lf for lf in leaves}
    out_matches = []
    for m in matches:
        sc = parse_scores(m)
        w, r1, r2 = winner_slot(m)
        ti = tree_of[m.id]
        out_matches.append(
            {
                "id": m.id,
                "tree": ti,
                "orient": m.orient,
                "col": col_of[m.id],
                "ncol": ncol_of_tree[ti],
                "date": date_tokens_for(toks, m.orient, m.b),
                "slot1": {"leaf": leaf_name[(m.id, 1)]["name"]} if 1 in m.leaf else {"from": m.child[1].id},
                "slot2": {"leaf": leaf_name[(m.id, 2)]["name"]} if 2 in m.leaf else {"from": m.child[2].id},
                "leaf_sub1": leaf_name[(m.id, 1)]["sub"] if 1 in m.leaf else [],
                "leaf_sub2": leaf_name[(m.id, 2)]["sub"] if 2 in m.leaf else [],
                "winner_slot": w,
                "red": [round(r1, 2), round(r2, 2)],
                "parent": m.parent.id if m.parent else None,
                "parent_slot": m.parent_slot,
                "bar": [m.bar.o, round(m.bar.c, 1), round(m.bar.a0, 1), round(m.bar.a1, 1)],
                "j": round(m.j, 1),
                "root_label": roots_label.get(m.id),
                "tokens": [f"{t.text}@{t.cx:.0f},{t.cy:.0f}" for t in m.tokens],
                **sc,
                "notes": sc["notes"] + (["3位決定戦"] if roots_label.get(m.id) == "3位決定戦" and "3位決定戦" not in sc["notes"] else []),
            }
        )
    used.update(id(t) for m in matches for t in m.tokens)
    out_matches.extend(facing_finals(pairs, toks, used, len(matches)))
    return {"page": pno, "size": [page.rect.width, page.rect.height], "matches": out_matches, "leaves": leaves}


FACING_SCORE = re.compile(r"^([0-9OＯ]+)\s*-\s*([0-9OＯ]+)$")


def facing_pairs(matches: list[Match], toks: list[Tok]) -> list[tuple]:
    """左右の山の出口が中央で向かい合い、その間にスコアが書かれている組（関東大会予選の決勝）を探す。

    総体の一次トーナメントや支部予選でも左右の出口は向かい合うが、それぞれ別の枠（A と I など）に入るだけで
    試合はしていない。間にスコアがあるかどうかで見分ける。
    """
    roots = [m for m in matches if m.parent is None]
    out = []
    for L in [r for r in roots if r.orient == "LR"]:
        for R in [r for r in roots if r.orient == "RL"]:
            le = L.stem.a1 if L.p0 == "lo" else L.stem.a0
            re_ = R.stem.a0 if R.p0 == "hi" else R.stem.a1
            if not (abs(L.j - R.j) <= 4 and -5 <= re_ - le <= 160):
                continue
            y = (L.j + R.j) / 2
            between = [t for t in toks if le - 5 <= t.cx <= re_ + 5 and abs(t.cy - y) <= 30]
            if any(FACING_SCORE.match(t.text.strip()) for t in between):
                out.append((L, R, le, re_))
    return out


def facing_finals(pairs: list[tuple], toks: list[Tok], used: set, next_id: int) -> list[dict]:
    """向かい合った決勝を試合として足す。

    試合線の形を持たないので、2本の出口の線の端の間にあるスコアから勝者を決める。
    """
    out = []
    for L, R, le, re_ in pairs:
        if True:
            y = (L.j + R.j) / 2
            box = [t for t in toks if id(t) not in used and le - 5 <= t.cx <= re_ + 5 and abs(t.cy - y) <= 30]
            s1 = s2 = None
            for t in box:
                mm = FACING_SCORE.match(t.text.strip())
                if mm:
                    s1, s2 = (int(g.replace("O", "0").replace("Ｏ", "0")) for g in mm.groups())
            if s1 is None:
                ints = sorted((t for t in box if INT.match(t.text.strip())), key=lambda t: t.cx)
                if len(ints) >= 2:
                    s1, s2 = int(ints[0].text), int(ints[-1].text)
            out.append(
                {
                    "id": next_id + len(out),
                    "tree": -1,
                    "orient": "facing",
                    "col": 0,
                    "ncol": 0,
                    "date": None,
                    "slot1": {"from": L.id},
                    "slot2": {"from": R.id},
                    "leaf_sub1": [],
                    "leaf_sub2": [],
                    "winner_slot": None,
                    "red": [0.0, 0.0],
                    "parent": None,
                    "parent_slot": 0,
                    "bar": ["h", round(y, 1), round(le, 1), round(re_, 1)],
                    "j": round((le + re_) / 2, 1),
                    "root_label": "決勝",
                    "score1": s1,
                    "score2": s2,
                    "pk1": None,
                    "pk2": None,
                    "halves": [],
                    "notes": ["facing_final"],
                    "match_no": None,
                    "kickoff": None,
                    "marks": [],
                }
            )
    return out


def resolve_names(matches: list[dict]) -> None:
    """子の試合の勝者を親の枠に流し込み、各試合の対戦校名を確定させる。"""
    by_id = {m["id"]: m for m in matches}
    memo: dict[int, str | None] = {}

    def winner(mid: int) -> str | None:
        if mid in memo:
            return memo[mid]
        memo[mid] = None
        m = by_id[mid]
        w = m["winner_slot"]
        memo[mid] = team(m, w) if w else None
        return memo[mid]

    def team(m: dict, slot: int) -> str | None:
        s = m[f"slot{slot}"]
        return s["leaf"] if "leaf" in s else winner(s["from"])

    for m in matches:
        m["team1"] = team(m, 1)
        m["team2"] = team(m, 2)
        m["winner"] = team(m, m["winner_slot"]) if m["winner_slot"] else None


def score_winner(m: dict) -> int | None:
    s1, s2 = m["score1"], m["score2"]
    if s1 is None or s2 is None:
        return None
    k1 = (s1, m["pk1"] if m["pk1"] is not None else -1)
    k2 = (s2, m["pk2"] if m["pk2"] is not None else -1)
    if k1 == k2:
        return None
    return 1 if k1 > k2 else 2


def fill_winner_from_score(matches: list[dict]) -> None:
    """赤線がまだ引かれていない（スコアだけ先に入っている）試合は、スコアから勝者を決める。"""
    for m in matches:
        m["winner_source"] = "red" if m["winner_slot"] else None
        if m["winner_slot"] is not None:
            continue
        w = score_winner(m)
        if not w:
            continue
        if max(m["red"]) < 0.05:
            m["winner_slot"], m["winner_source"] = w, "score"
        elif min(m["red"]) > 0.5:
            # 試合線が両側とも赤く塗られている（PDF の作図ミス）。スコアで決める
            m["winner_slot"], m["winner_source"] = w, "score_red_both"


def parse_pdf(path: Path) -> dict:
    doc = pymupdf.open(path)
    pages = []
    for pno, page in enumerate(doc):
        p = parse_page(page, pno)
        fill_winner_from_score(p["matches"])
        resolve_names(p["matches"])
        pages.append(p)
    title = ""
    first = doc[0].get_text("text").strip().splitlines()
    if first:
        title = first[0]
    return {"file": path.name, "title_line": title, "pages": pages}


# ---------------------------------------------------------------- 検証用オーバーレイ


def draw_overlay(path: Path, result: dict, out_dir: Path, dpi: int = 150) -> list[Path]:
    doc = pymupdf.open(path)
    outs = []
    for p in result["pages"]:
        page = doc[p["page"]]
        for m in p["matches"]:
            o, c, a0, a1 = m["bar"]
            jx, jy = (m["j"], c) if o == "h" else (c, m["j"])
            ok = m["winner_slot"] is not None
            s1, s2 = m["score1"], m["score2"]
            consistent = True
            if ok and s1 is not None and s2 is not None:
                w1 = (s1, m["pk1"] or 0) > (s2, m["pk2"] or 0)
                w2 = (s2, m["pk2"] or 0) > (s1, m["pk1"] or 0)
                consistent = (m["winner_slot"] == 1 and w1) or (m["winner_slot"] == 2 and w2)
            color = (0, 0.7, 0) if ok and consistent else ((1, 0.55, 0) if not ok else (0.9, 0, 0.9))
            page.draw_circle(pymupdf.Point(jx, jy), 3.2, color=color, fill=color, overlay=True)
            label = f"{s1 if s1 is not None else '?'}-{s2 if s2 is not None else '?'}"
            if m["pk1"] is not None:
                label += f"(PK{m['pk1']}-{m['pk2']})"
            if m["winner"]:
                label += " " + m["winner"]
            page.insert_text(pymupdf.Point(jx + 3, jy - 3), label, fontsize=4.2, fontname="japan", color=(0, 0, 0.85), overlay=True)
        for lf in p["leaves"]:
            x, y = lf["point"]
            page.draw_circle(pymupdf.Point(x, y), 1.8, color=(0, 0.3, 1), fill=(0, 0.3, 1), overlay=True)
            page.insert_text(pymupdf.Point(x + 2, y + 5), lf["name"] or "??", fontsize=4.2, fontname="japan", color=(0, 0.3, 1), overlay=True)
        pix = page.get_pixmap(dpi=dpi)
        out = out_dir / f"{path.stem}_p{p['page']}.png"
        pix.save(out)
        outs.append(out)
    return outs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out/json"))
    ap.add_argument("--overlay", type=Path, default=None, help="オーバーレイ PNG の出力先")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.overlay:
        args.overlay.mkdir(parents=True, exist_ok=True)
    for path in args.pdfs:
        res = parse_pdf(path)
        (args.out / f"{path.stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        if args.overlay:
            draw_overlay(path, res, args.overlay)
        n = sum(len(p["matches"]) for p in res["pages"])
        print(f"{path.name}: {n} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
