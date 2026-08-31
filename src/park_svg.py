# -*- coding: utf-8 -*-
"""行き先3件の「公園の影の形」を SVG で出す（2026-08-17 新設・C35）

★ なぜ作ったか
  2026-08-17 の設計変更で、行き先は「合計mLの数字」ではなく
  「公園の影の形」を見せて本人に選んでもらう形になった（spec.md M2b）。
  ［事実：ヒアリング1人目］「公園のどこが陰なのか見せてくれるなら、遊具の場所は覚えてる」。
  一方で面平均の日陰率（%）は否定されたので、★ パーセントは出さない。

★ 描いているもの／描いていないもの
  描く  ：建物（LOD2実形状585棟＋LOD1）と高架デッキの影／建物の輪郭／公園のポリゴン／太陽の方位
  描かない：樹木の影（データが無い）。★ そのため画面に「樹木は入っていません」と出すこと
"""
import json, math, sys
from datetime import datetime

from shapely.geometry import box
from shapely.ops import unary_union

import bridge, lod2, paths
import destination as D
from shadow import load_buildings, shadow, sun, TZ

W = H = 460
SPAN = 150.0                      # 図の一辺（m）。公園がはみ出す場合は自動で広げる
HOURS = (11, 12, 13, 14, 15, 16)
DATE = (2026, 8, 12)              # ★ route.py と同じ固定日。spec.md §10-0 の1

PAL = dict(shade='#2a78d6', bldg='#f6f5f2', bldg_line='#dcdbd4',
           park='#1baf7a', sun='#eb6834', ground='#ffffff')


def _paths(g, px):
    gs = list(g.geoms) if hasattr(g, 'geoms') else [g]
    d = []
    for p in gs:
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)
            if len(c) < 3:
                continue
            d.append('M' + ' L'.join('%.1f,%.1f' % px(x, y) for x, y in c) + 'Z')
    return ''.join(d)


def park_svg(name, poly, U, FOOT, B, az):
    cx, cy = poly.centroid.x, poly.centroid.y
    x0, y0, x1, y1 = poly.bounds
    span = max(SPAN, (x1 - x0) * 1.6, (y1 - y0) * 1.6)
    k = W / span
    bx = box(cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2)

    def px(x, y):
        return ((x - cx) * k + W / 2, H / 2 - (y - cy) * k)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'role="img" aria-label="{name}の影の形">',
           f'<rect width="{W}" height="{H}" fill="{PAL["ground"]}"/>']
    # 影（建物＋高架）— 公園の外も描くと位置関係が分かる
    sh = U.intersection(bx)
    if not sh.is_empty:
        out.append(f'<path d="{_paths(sh.simplify(0.5), px)}" fill="{PAL["shade"]}" '
                   f'opacity="0.16" stroke="none" fill-rule="evenodd"/>')
    # 建物の輪郭
    for p, h, _ in B:
        if h >= 3 and p.area >= 25 and p.intersects(bx):
            out.append(f'<path d="{_paths(p.intersection(bx).simplify(0.5), px)}" '
                       f'fill="{PAL["bldg"]}" stroke="{PAL["bldg_line"]}" stroke-width="0.8"/>')
    # 公園の地面（建物を抜く）と、その中の影を濃く
    ground = poly.difference(FOOT)
    gpath = _paths(ground.simplify(0.4), px)
    out.append(f'<path d="{gpath}" fill="#fffdf5" stroke="none" fill-rule="evenodd"/>')
    out.append(f'<path d="{gpath}" fill="{PAL["sun"]}" opacity="0.20" stroke="none" fill-rule="evenodd"/>')
    inside = ground.intersection(U)
    if not inside.is_empty:
        out.append(f'<path d="{_paths(inside.simplify(0.4), px)}" fill="{PAL["shade"]}" '
                   f'opacity="0.62" stroke="none" fill-rule="evenodd"/>')
    # ★ 公園の輪郭は影より上に描く（影に隠れると「どこが公園か」が読めない）
    out.append(f'<path d="{gpath}" fill="none" stroke="{PAL["park"]}" stroke-width="3" '
               f'stroke-linejoin="round" fill-rule="evenodd"/>')
    # 太陽の方位
    X, Y = px(cx, cy)
    ar = math.radians(az); L = W * 0.30
    out.append(f'<line x1="{X:.0f}" y1="{Y:.0f}" x2="{X + L * math.sin(ar):.0f}" '
               f'y2="{Y - L * math.cos(ar):.0f}" stroke="{PAL["sun"]}" stroke-width="2.2" '
               f'stroke-dasharray="7 5" opacity="0.85"/>')
    # スケールバー（20m）
    sb = 20 * k
    out.append(f'<line x1="16" y1="{H-18}" x2="{16+sb:.0f}" y2="{H-18}" stroke="#5b6068" stroke-width="2"/>'
               f'<text x="{16+sb/2:.0f}" y="{H-24}" font-size="11" fill="#5b6068" text-anchor="middle">20m</text>')
    out.append('</svg>')
    return ''.join(out)


def main():
    src = json.load(open(paths.out('screen6.json')))
    wanted = sorted({t['name'] for h in src['hours'].values() for t in h['top']})
    print('対象の公園:', wanted)
    cands = {nm: (lo, la, area) for kind, nm, lo, la, area, indoor in D.load_candidates()[0]
             if not indoor and nm in wanted}
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    FOOT = unary_union([p.simplify(0.3) for p, h, _ in B])
    polys = {}
    for nm, (lo, la, area) in cands.items():
        g, gap = D.park_polygon(lo, la, area, nm)   # ★ 2026-08-31：名前を渡す（都のポリゴンを引く）
        if g is None:
            print('  × ポリゴン無し:', nm); continue
        polys[nm] = g
        print(f"  ○ {nm}: {g.area:.0f}㎡（公称 {area:.0f}㎡）")

    out = {}
    for hour in HOURS:
        dt = datetime(*DATE, hour, tzinfo=TZ)
        alt, az = sun(dt)
        L2 = lod2.shadows(alt, az, bridge.ground_lookup())
        sh = [shadow(p.simplify(0.3), h, alt, az) for p, h, b in B if b['id'] not in L2]
        sh += list(L2.values())
        decks = bridge.load_decks()
        for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)):
            if g is not None:
                sh.append(g)
        U = unary_union(sh)
        out[hour] = {nm: park_svg(nm, p, U, FOOT, B, az) for nm, p in polys.items()}
        print(f"  {hour}時 高度{alt:.1f}° 方位{az:.1f}° → {len(out[hour])}枚")

    json.dump(out, open(paths.out('park_svgs.json'), 'w'), ensure_ascii=False)
    print('DONE -> out/park_svgs.json')


if __name__ == '__main__':
    main()
