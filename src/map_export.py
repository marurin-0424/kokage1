# -*- coding: utf-8 -*-
"""B-2 ④：ブラウザで地図を描くための素材を書き出す（2026-08-21 新設）

出力（すべて EPSG:6677 の平面直角座標。単位 m）
  out/map_links.json    リンク形状（経路のポリライン）
  out/map_foot.json     建物フットプリント（下地）
  out/map_shadow.json   影ポリゴン（時刻別）★ 時刻ごとに分割ファイルも出す
  out/map_parks.json    公園ポリゴン（行き先の形）

★ 影は 2026-08-12 の太陽位置。日付を増やすときはここを引数にする。
"""
import json, gzip, os
import pandas as pd
from datetime import datetime
from shapely.ops import unary_union
from shapely.geometry import Point
from shadow import load_buildings, load_links, shadow, sun, TZ, FWD
import bridge, lod2, destination as D, paths
import math

HOURS = (11, 12, 13, 14, 15, 16)
SHADOW_TOL = 2.0
FOOT_TOL = 1.0


def rings(g, prec=1):
    """1ポリゴンにつき [外周, 穴1, 穴2...] を返す。
    ★ 穴を落とすと中庭・ビルの内側まで日陰として塗ってしまう（2026-08-21 修正）。"""
    out = []
    if g is None or g.is_empty:
        return out
    for p in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        rs = [[[round(x, prec), round(y, prec)] for x, y in p.exterior.coords]]
        for h in p.interiors:
            if h.length > 4:
                rs.append([[round(x, prec), round(y, prec)] for x, y in h.coords])
        out.append(rs)
    return out


def dump(obj, name):
    p = paths.out(name)
    s = json.dumps(obj, separators=(',', ':'))
    open(p, 'w').write(s)
    gz = gzip.compress(s.encode(), 9)
    open(p + '.gz', 'wb').write(gz)
    print(f'   {name:<22} {len(s)/1024:>7.0f} KB / gzip {len(gz)/1024:>6.0f} KB')


def main():
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    gl = bridge.ground_lookup()
    decks = bridge.load_decks()
    print('■ 書き出し')

    # --- リンク形状（start_id/end_id つき。エンジンのエッジと突き合わせる） ---
    links = []
    for ls, pr in L:
        links.append(dict(a=str(pr.get('start_id')), b=str(pr.get('end_id')),
                          c=[[round(x, 1), round(y, 1)] for x, y in ls.coords]))
    dump(links, 'map_links.json')

    # --- 建物フットプリント ---
    foot = unary_union([p.simplify(0.5) for p, _h, _b in B]).simplify(FOOT_TOL)
    dump(rings(foot), 'map_foot.json')

    # --- 公園ポリゴン ---
    cands, _h, _m = D.load_candidates()
    parks = {}
    for kind, nm, lo, la, area, indoor in cands:
        if indoor:
            continue
        c, _g = D.park_polygon(lo, la, area)
        if c is None:
            c = Point(*FWD.transform(lo, la)).buffer(math.sqrt(area / math.pi))
        parks[nm] = rings(c.simplify(1.0))
    dump(parks, 'map_parks.json')

    # --- 影（時刻別） ---
    allh = {}
    for h in HOURS:
        dt = pd.DatetimeIndex([datetime(2026, 8, 12, h, 0, tzinfo=TZ)])
        alt, az = sun(dt)
        L2 = lod2.shadows(alt, az, gl)
        S = [shadow(p.simplify(0.3), ht, alt, az) for p, ht, bb in B if bb['id'] not in L2]
        S += list(L2.values())
        for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)):
            if g is not None:
                S += list(g.geoms) if hasattr(g, 'geoms') else [g]
        U = unary_union(S).simplify(SHADOW_TOL)
        r = rings(U)
        allh[h] = r
        dump(r, f'map_shadow_{h}.json')
        print(f'   {h}:00  太陽高度 {float(alt.iloc[0] if hasattr(alt,"iloc") else alt):.1f}°  '
              f'方位 {float(az.iloc[0] if hasattr(az,"iloc") else az):.1f}°  {len(r)}面')
    dump(allh, 'map_shadow.json')
    print('DONE')


if __name__ == '__main__':
    main()
