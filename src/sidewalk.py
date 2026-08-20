"""§14b-4 の検証：20行の影計算は「どちら側の歩道か」を実際に区別できるか。
歩行空間NWのリンク × 影ポリゴン → 左右ペアごとの日陰率を比較する。
"""
import paths
import sys, math, json, time
from datetime import datetime
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shadow import load_buildings, load_links, shadow, sun, TZ


def bearing(ls):
    (x1, y1), (x2, y2) = ls.coords[0], ls.coords[-1]
    return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 180.0


def shaded_ratio(ls, tree, polys, step=2.0):
    """リンクを2m刻みでサンプリングし、影に入っている割合を返す"""
    n = max(2, int(ls.length / step) + 1)
    pts = [ls.interpolate(i / (n - 1), normalized=True) for i in range(n)]
    hit = 0
    for p in pts:
        for j in tree.query(p):
            if polys[j].covers(p):
                hit += 1
                break
    return hit / n


def find_pairs(links):
    """rt_struct=1 の歩道リンクから、同一道路の左右ペアを検出（data-sources.md §発見④と同条件）"""
    side = [(i, ls, pr) for i, (ls, pr) in enumerate(links) if str(pr.get('rt_struct')) == '1']
    tree = STRtree([ls for _, ls, _ in side])
    cross = [ls for ls, pr in links if str(pr.get('rt_struct')) == '3']
    ctree = STRtree(cross)
    pairs = []
    seen = set()
    for k, (i, ls, pr) in enumerate(side):
        b1 = bearing(ls)
        for m in tree.query(ls.buffer(50)):
            if m == k:
                continue
            j, ls2, _ = side[m]
            b2 = bearing(ls2)
            d = abs(b1 - b2)
            d = min(d, 180 - d)
            if d > 12:
                continue
            sep = ls.distance(ls2)
            if not (8 <= sep <= 50):
                continue
            # 軸方向のオーバーラップ（互いの中点が相手の投影範囲に入る）
            if ls.interpolate(0.5, normalized=True).distance(ls2) > sep * 1.6:
                continue
            # 横断歩道が両者を繋いでいるか
            linked = any(cross[c].distance(ls) < 3 and cross[c].distance(ls2) < 3
                         for c in ctree.query(ls.buffer(60)))
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((i, j, sep, b1, linked))
    return pairs


def main():
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    print(f'建物 {len(B)} 棟 / リンク {len(L)} 本')

    pairs = find_pairs(L)
    linked = [p for p in pairs if p[4]]
    print(f'左右ペア（ゆるい判定） {len(pairs)} 組 / 横断歩道が繋いでいるもの {len(linked)} 組')

    rows = []
    for hh in [10, 12, 14, 15, 16]:
        dt = pd.DatetimeIndex([datetime(2026, 8, 12, hh, 0, tzinfo=TZ)])
        alt, az = sun(dt)
        S = [shadow(p.simplify(0.3), h, alt, az) for p, h, _ in B]
        tree = STRtree(S)
        cache = {}

        def ratio(i):
            if i not in cache:
                cache[i] = shaded_ratio(L[i][0], tree, S)
            return cache[i]

        diffs = []
        for i, j, sep, b1, ok in linked:
            r1, r2 = ratio(i), ratio(j)
            diffs.append((abs(r1 - r2), r1, r2, sep, b1, i, j))
        arr = np.array([d[0] for d in diffs])
        # 全リンクの日陰率（延長重み）
        tot = sum(l.length for l, _ in L)
        sh = sum(l.length * ratio(k) for k, (l, _) in enumerate(L))
        rows.append((hh, alt, az, sh / tot, arr.mean(), np.median(arr), (arr > 0.2).mean(), (arr > 0.5).mean()))
        print(f'{hh:02d}:00 高度{alt:5.1f}° 方位{az:5.1f}° | NW全体の日陰率 {sh/tot:5.1%} | '
              f'左右差 平均{arr.mean():5.1%} 中央{np.median(arr):5.1%} | '
              f'差20pt超 {(arr>0.2).mean():5.1%} / 差50pt超 {(arr>0.5).mean():5.1%}')
        if hh == 14:
            json.dump([[round(d[0],3),round(d[1],3),round(d[2],3),round(d[3],1),round(d[4],1),d[5],d[6]] for d in diffs],
                      open(paths.out('pairs14.json'),'w'))
    return rows


if __name__ == '__main__':
    main()
