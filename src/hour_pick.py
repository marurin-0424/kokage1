# -*- coding: utf-8 -*-
"""「公園を決める前に、時刻をどう薦めるか」を成立させるための実測（2026-08-17）

★ 問い：往復の日なた時間は行き先に依存する。行き先が未定の段階で時刻を薦めると循環する。
★ 案：行き先に依存しない量＝「出発地から歩ける範囲の歩道が、その時刻に何%日陰か」で薦める。
"""
import csv, io, math, os, glob
import route, paths

ORIGIN = (139.71150, 35.72950)   # 池袋駅東口
RADII = (400.0, 800.0, 1200.0)
HOURS = (11, 12, 13, 14, 15, 16, 17)

from pyproj import Transformer
FWD = Transformer.from_crs('EPSG:6668', 'EPSG:6677', always_xy=True)
ox, oy = FWD.transform(*ORIGIN)

print('■ 歩行空間ネットワークの日陰率（延長重み）— 行き先に依存しない量')
print(f"{'時刻':>4}{'全域':>9}{'出発地400m':>12}{'800m':>9}{'1200m':>9}{'全域の総延長':>13}")
rows = {}
for h in HOURS:
    G, alt, az, _ = route.build(h, stroller=False)
    tot = {r: 0.0 for r in RADII}; sh = {r: 0.0 for r in RADII}
    T = S = 0.0
    for u, v, e in G.edges(data=True):
        d, s = e['dist'], e['shade']
        T += d; S += d * s
        mx = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        my = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        dist = math.hypot(mx - ox, my - oy)
        for r in RADII:
            if dist <= r:
                tot[r] += d; sh[r] += d * s
    f = lambda r: (sh[r] / tot[r] * 100) if tot[r] else float('nan')
    print(f"{h:>3}時{S/T*100:>8.1f}%{f(400):>11.1f}%{f(800):>8.1f}%{f(1200):>8.1f}%{T/1000:>11.1f}km")
    rows[h] = dict(all=S/T*100, r400=f(400), r800=f(800), r1200=f(1200), alt=alt, az=az)

print('\n■ 太陽高度・方位（2026-08-12 固定）')
for h in HOURS:
    print(f"  {h}時  高度 {rows[h]['alt']:.1f}°  方位 {rows[h]['az']:.1f}°")

print('\n■ WBGT の時刻別（2025年8月・実測3地点・31日分）')
stats = {}
for p in sorted(glob.glob(os.path.join(paths.ENVWBGT, '*.csv'))):
    name = os.path.basename(p)
    raw = open(p, encoding='utf-8-sig').read()
    for r in csv.DictReader(io.StringIO(raw)):
        try:
            hh = int(r['Time'].split(':')[0]); w = float(r['WBGT'])
        except (ValueError, KeyError, TypeError):
            continue
        stats.setdefault((name, hh), []).append(w)
names = sorted({k[0] for k in stats})
print(f"{'時刻':>4}" + ''.join(f"{n.replace('final_wbgt_','').replace('_202508.csv',''):>10}" for n in names)
      + f"{'3地点の最大':>12}{'≧31の割合':>11}")
for h in HOURS:
    vals = []
    allv = []
    for n in names:
        v = stats.get((n, h), [])
        vals.append(sum(v)/len(v) if v else float('nan')); allv += v
    hi = max(vals)
    p31 = sum(1 for x in allv if x >= 31) / len(allv) * 100 if allv else 0
    print(f"{h:>3}時" + ''.join(f"{x:>9.1f}℃" for x in vals) + f"{hi:>11.1f}℃{p31:>10.1f}%")
