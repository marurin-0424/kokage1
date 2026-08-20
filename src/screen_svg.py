"""こかげ v0 の地図をインラインSVGとして生成する。
matplotlib のPNGではなくSVGにする理由：単一HTMLに埋め込め、拡大しても劣化せず、
1600×900のキャプチャで文字が潰れないため。
"""
import paths
import sys, json, math
from datetime import datetime
import pandas as pd
from shapely.geometry import box, Point, LineString, Polygon
from shapely.ops import unary_union
from shadow import load_buildings, load_links, shadow, sun, TZ, FWD
import bridge

W, H = 720, 540
PAL = dict(bldg='#f1f0ed', bldg_edge='#dcdbd4', shadow='#98a0a8',
           deck='#4a3aa7', link='#d8d7d0', sun='#eb6834', shade='#2a78d6',
           ink='#0b0b0b', muted='#898781', surface='#fcfcfb')
_GEO = {}


def geo(hour):
    if hour in _GEO:
        return _GEO[hour]
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    dt = pd.DatetimeIndex([datetime(2026, 8, 12, hour, 0, tzinfo=TZ)])
    alt, az = sun(dt)
    decks = bridge.load_decks()
    _GEO[hour] = dict(
        alt=alt, az=az,
        B=[(p, h) for p, h, _ in B],
        S=[shadow(p.simplify(0.5), h, alt, az) for p, h, _ in B],
        BR=[g for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)) if g],
        L=[ls for ls, _ in L])
    return _GEO[hour]


def _fmt(v):
    return f'{v:.0f}'


class Canvas:
    def __init__(self, cx, cy, span):
        self.cx, self.cy, self.span = cx, cy, span
        self.k = W / span
        self.box = box(cx - span / 2, cy - span * H / W / 2,
                       cx + span / 2, cy + span * H / W / 2)
        self.parts = []

    def px(self, x, y):
        return ((x - self.cx) * self.k + W / 2, H / 2 - (y - self.cy) * self.k)

    def poly(self, g, **a):
        gs = list(g.geoms) if hasattr(g, 'geoms') else [g]
        d = []
        for p in gs:
            if p.is_empty or p.geom_type != 'Polygon':
                continue
            for ring in [p.exterior] + list(p.interiors):
                c = list(ring.coords)
                if len(c) < 3:
                    continue
                pts = [self.px(x, y) for x, y in c]
                d.append('M' + ' L'.join(f'{_fmt(a_)},{_fmt(b_)}' for a_, b_ in pts) + 'Z')
        if d:
            at = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in a.items())
            self.parts.append(f'<path d="{"".join(d)}" {at} fill-rule="evenodd"/>')

    def line(self, ls, **a):
        gs = list(ls.geoms) if hasattr(ls, 'geoms') else [ls]
        d = []
        for p in gs:
            c = list(p.coords)
            if len(c) < 2:
                continue
            pts = [self.px(x, y) for x, y in c]
            d.append('M' + ' L'.join(f'{_fmt(a_)},{_fmt(b_)}' for a_, b_ in pts))
        if d:
            at = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in a.items())
            self.parts.append(f'<path d="{"".join(d)}" fill="none" {at}/>')

    def svg(self, title=''):
        return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{title}" '
                f'style="display:block;background:{PAL["surface"]}">' + ''.join(self.parts) + '</svg>')


def scalebar(c):
    m = 100 if c.span > 500 else 50
    L = m * c.k
    x0, y0 = 16, H - 18
    c.parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0+L:.1f}" y2="{y0}" stroke="{PAL["ink"]}" stroke-width="2.5"/>'
        f'<text x="{x0+L/2:.1f}" y="{y0-6}" text-anchor="middle" font-size="11" fill="{PAL["ink"]}">{m} m</text>')


def north(c):
    x, y = W - 26, 30
    c.parts.append(
        f'<path d="M{x},{y-14} L{x-6},{y+6} L{x},{y+1} L{x+6},{y+6} Z" fill="{PAL["ink"]}"/>'
        f'<text x="{x}" y="{y+20}" text-anchor="middle" font-size="10" fill="{PAL["muted"]}">N</text>')


def build_case(cs):
    """1ケース分の地図SVG"""
    g = geo(cs['hour'])
    ox, oy = cs['origin_xy']
    dx, dy = cs['main'].get('xy', [ox, oy])
    pts = [(ox, oy), (dx, dy)]
    for s in cs['segs']:
        pts += [tuple(p) for p in s['xy']]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs) + 200, (max(ys) - min(ys) + 200) * W / H, 520)
    c = Canvas(cx, cy, span)

    # ★ 影 → 建物 の順に描く。shadow() の戻り値はフットプリントを含むので、
    #   建物を後から重ねないと「影だけの部分」が見分けられない。
    sh = unary_union([s for s in g['S'] if s.intersects(c.box)])
    c.poly(sh.intersection(c.box).simplify(2.0), fill=PAL['shadow'], opacity='0.60', stroke='none')
    for b in g['BR']:
        if b.intersects(c.box):
            c.poly(b.intersection(c.box).simplify(1.5), fill=PAL['deck'], opacity='0.22', stroke='none')
    for p, h in g['B']:
        if h >= 5 and p.area >= 60 and p.intersects(c.box):
            c.poly(p.intersection(c.box).simplify(1.2), fill=PAL['bldg'],
                   stroke='#dedcd6', stroke_width='0.5')
    for ls in g['L']:
        if ls.intersects(c.box):
            c.line(ls.intersection(c.box).simplify(1.0), stroke=PAL['link'], stroke_width='1.6', stroke_linecap='round')

    # 行き先の円（面積から半径を近似）
    r = cs['main'].get('radius', 25.0)
    px, py = c.px(dx, dy)
    c.parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r*c.k:.1f}" fill="#1baf7a" opacity="0.18" '
                   f'stroke="#1baf7a" stroke-width="1.5" stroke-dasharray="4 3"/>')

    # 経路：日陰率で2値に分けて描く（凡例で明示）
    for s in cs['segs']:
        col = PAL['shade'] if s['shade'] >= 0.5 else PAL['sun']
        c.line(LineString(s['xy']), stroke='#ffffff', stroke_width='7', stroke_linecap='round')
    for s in cs['segs']:
        col = PAL['shade'] if s['shade'] >= 0.5 else PAL['sun']
        c.line(LineString(s['xy']), stroke=col, stroke_width='4.5', stroke_linecap='round')

    # L3の直線区間。★ 経路が1ノードで終わる（＝実経路が無い）ときは出発地から直接引く。
    #   これを忘れると、L3の行き先で地図に線が1本も出なくなる（2026-08-12 修正）。
    if cs['main'].get('gap', 0) > 0:
        lx, ly = cs['segs'][-1]['xy'][-1] if cs['segs'] else (ox, oy)
        c.line(LineString([(lx, ly), (dx, dy)]), stroke=PAL['muted'], stroke_width='3',
               stroke_dasharray='7 5', stroke_linecap='round')

    def label(x, y, fill, lab, sub, above=False):
        X, Y = c.px(x, y)
        anc, off = ('start', 13) if X < W * 0.55 else ('end', -13)
        if above:
            anc, off = 'middle', 0
        c.parts.append(
            f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="8" fill="{fill}" stroke="#fff" stroke-width="2.5"/>'
            f'<text x="{X+off:.1f}" y="{Y-2+(-32 if above else 0):.1f}" text-anchor="{anc}" font-size="14" font-weight="700" '
            f'fill="{PAL["ink"]}" paint-order="stroke" stroke="#fff" stroke-width="4.5">{lab}</text>'
            f'<text x="{X+off:.1f}" y="{Y+14+(-31 if above else 0):.1f}" text-anchor="{anc}" font-size="11.5" '
            f'fill="{PAL["muted"]}" paint-order="stroke" stroke="#fff" stroke-width="4.5">{sub}</text>')
    label(dx, dy, '#1baf7a', cs['main']['name'], '行き先', above=True)
    label(ox, oy, PAL['ink'], cs['origin_label'], '出発')
    scalebar(c); north(c)
    return c.svg(f'{cs["origin_label"]}から{cs["main"]["name"]}への経路')


def build_outrange():
    """地下鉄 雑司が谷駅：歩行NWの収録範囲の外にあることを見せる"""
    L = [ls for ls, _ in load_links(paths.raw('ikebukuro_link.geojson'))]
    cover = unary_union([ls.buffer(70) for ls in L]).buffer(30).buffer(-30).simplify(12)
    sx, sy = FWD.transform(139.715050, 35.720537)      # 地下鉄 雑司が谷駅
    tx, ty = FWD.transform(139.717760, 35.724081)      # 都電雑司ヶ谷駅
    px, py = FWD.transform(139.71642, 35.71859)        # 雑司が谷公園（related.zip の座標）
    xs = [sx, tx, px] + [cover.bounds[0], cover.bounds[2]]
    ys = [sy, ty, py] + [cover.bounds[1], cover.bounds[3]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs) + 300, (max(ys) - min(ys) + 300) * W / H)
    c = Canvas(cx, cy, span)
    c.poly(cover, fill='#2a78d6', opacity='0.10', stroke='#2a78d6', stroke_width='2', stroke_dasharray='6 4')
    for ls in L:
        c.line(ls.simplify(2.0), stroke='#8fb8e8', stroke_width='1.2')
    c.line(LineString([(sx, sy), (px, py)]), stroke='#d03b3b', stroke_width='2.5', stroke_dasharray='6 4')

    def mark(x, y, col, lab, sub, anc='start', ddx=14, ddy=-3, r=8):
        X, Y = c.px(x, y)
        c.parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r}" fill="{col}" stroke="#fff" stroke-width="2.5"/>'
                       f'<text x="{X+ddx:.1f}" y="{Y+ddy:.1f}" text-anchor="{anc}" font-size="14" '
                       f'font-weight="700" fill="{PAL["ink"]}" paint-order="stroke" stroke="#fff" '
                       f'stroke-width="5">{lab}</text>'
                       f'<text x="{X+ddx:.1f}" y="{Y+ddy+15:.1f}" text-anchor="{anc}" font-size="11.5" '
                       f'fill="{PAL["muted"]}" paint-order="stroke" stroke="#fff" stroke-width="5">{sub}</text>')
    mark(tx, ty, '#0ca30c', '都電雑司ヶ谷駅', '収録範囲の中（8m）', 'start', 14, -3)
    mark(sx, sy, '#d03b3b', '地下鉄 雑司が谷駅', '収録範囲の外（442m）', 'end', -14, -3)
    mark(px, py, '#1baf7a', '雑司が谷公園', '1,346㎡', 'start', 13, 6, 7)
    mx, my = c.px((sx + px) / 2, (sy + py) / 2)
    c.parts.append(f'<text x="{mx-14:.1f}" y="{my+5:.1f}" text-anchor="end" font-size="13" font-weight="700" '
                   f'fill="#d03b3b" paint-order="stroke" stroke="#fff" stroke-width="5">徒歩3分・172m</text>')
    scalebar(c); north(c)
    return c.svg('地下鉄雑司が谷駅は歩行空間ネットワークの収録範囲の外')


if __name__ == '__main__':
    data = json.load(open(paths.out('screen_cases.json')))
    svgs = {}
    for k, cs in data['cases'].items():
        svgs[k] = build_case(cs)
        print(k, len(svgs[k]) // 1024, 'KB', flush=True)
    svgs['outrange'] = build_outrange()
    print('outrange', len(svgs['outrange']) // 1024, 'KB')
    json.dump(svgs, open(paths.cache('screen_svgs.json'), 'w'), ensure_ascii=False)
    print('DONE')
