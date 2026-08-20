"""M7：街路樹の影を足すと、歩行ネットワークの日陰率はどれだけ上がるか"""
import paths
import sys, json, time
from datetime import datetime
import pandas as pd, numpy as np
from shapely.strtree import STRtree
from shadow import load_buildings, load_links, shadow, sun, TZ
from sidewalk import shaded_ratio
import bridge, tree

BBOX = (139.690, 35.700, 139.740, 35.745)


def main(hours=(9, 10, 12, 14, 16)):
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    T = tree.load_trees(bbox=BBOX)
    decks = bridge.load_decks()
    tot = sum(l.length for l, _ in L)
    print(f'建物{len(B)} リンク{len(L)} 街路樹{len(T)} デッキ{len(decks)}')

    rows = []
    for hh in hours:
        dt = pd.DatetimeIndex([datetime(2026, 8, 12, hh, 0, tzinfo=TZ)])
        alt, az = sun(dt)
        base = [shadow(p.simplify(0.3), h, alt, az) for p, h, _ in B]
        for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)):
            if g is not None:
                base += list(g.geoms) if hasattr(g, 'geoms') else [g]
        tsh = tree.tree_shadow(T, alt, az)

        out = {}
        for name, S in (('bldg+brid', base), ('+tree', base + tsh)):
            t0 = time.time()
            st = STRtree(S)
            r = [shaded_ratio(l, st, S) for l, _ in L]
            out[name] = np.array(r)
            print(f'  {name:10s} {time.time()-t0:5.1f}s')
        a, b = out['bldg+brid'], out['+tree']
        w = np.array([l.length for l, _ in L])
        s0 = float((a * w).sum() / tot); s1 = float((b * w).sum() / tot)
        d = b - a
        rows.append(dict(hour=hh, alt=round(alt, 1), az=round(az, 1),
                         base=round(s0, 4), withtree=round(s1, 4),
                         gain_pt=round((s1 - s0) * 100, 2),
                         links_up=int((d > 0.001).sum()),
                         links_up20=int((d > 0.20).sum()),
                         max_gain=round(float(d.max()) * 100, 1)))
        print(f'{hh:02d}:00 高度{alt:5.1f}° | 建物+高架 {s0:6.1%} → +街路樹 {s1:6.1%} '
              f'（+{(s1-s0)*100:4.1f}pt） 改善リンク {int((d>0.001).sum())}本 '
              f'/ 20pt超 {int((d>0.20).sum())}本 / 最大 +{d.max()*100:.0f}pt')
        if hh == 14:
            json.dump([[round(float(x), 3), round(float(y), 3)] for x, y in zip(a, b)],
                      open(paths.out('tree_link14.json'), 'w'))
    json.dump(rows, open(paths.out('tree_eval.json'), 'w'), ensure_ascii=False, indent=1)
    return rows


if __name__ == '__main__':
    main()
