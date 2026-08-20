# -*- coding: utf-8 -*-
"""円近似の偏りを測る：公園の「建物率」と「日陰率」の関係。

★ 測る対象は【ふるいをかける前の全62公園】。
   destination.load_candidates() は 500㎡未満・緑道・建物率50%超を既に落としているので、
   偏りそのものを測るにはこのスクリプトのように生データから読む必要がある。
"""
import paths
import sys, math, json, zipfile, io
import numpy as np
import destination as D
from shapely.geometry import Point
from shadow import FWD


def main(hour=14, wbgt=29.0):
    G, alt, U, FOOT = D._prepare(hour, wbgt, False, 1.0)
    z = zipfile.ZipFile(D.DATA + '13116_toshima-ku_2025_related.zip')
    gj = json.load(io.TextIOWrapper(z.open('13116_toshima-ku_pref_2023_park.geojson'),
                                    encoding='utf-8'))
    rows = []
    for f in gj['features']:
        pr = f['properties']; a = pr.get('供用済面積') or 0
        if a <= 0:
            continue
        lo, la = f['geometry']['coordinates'][:2]
        R = math.sqrt(a / math.pi)
        c = Point(*FWD.transform(lo, la)).buffer(R)
        if FOOT.distance(c) > 150:          # 建物の収録範囲の外は測れない
            continue
        g = c.difference(FOOT)
        if g.area < 1:                      # 円がまるごと建物（東池袋中央公園）
            rows.append((pr['公園名'], a, 1.0, None))
            continue
        rows.append((pr['公園名'], a, 1 - g.area / c.area,
                     U.difference(FOOT).intersection(c).area / g.area))
    usable = [r for r in rows if r[3] is not None]
    arr = np.array([(r[2], r[3]) for r in usable])
    out = dict(hour=hour, n_all=len(gj['features']), n_in_range=len(rows),
               n_measurable=len(usable),
               r=round(float(np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]), 3), bins=[])
    print(f'全公園{out["n_all"]}件 → 建物の収録範囲内 {out["n_in_range"]}件（うち日陰率が測れる {out["n_measurable"]}件）')
    print(f'建物率 vs 日陰率 相関 r = {out["r"]}')
    for lo_, hi in ((0, .15), (.15, .30), (.30, .50), (.50, 1.01)):
        m = (arr[:, 0] >= lo_) & (arr[:, 0] < hi)
        b = dict(lo=lo_, hi=hi, n=int(m.sum()), mean=round(float(arr[m, 1].mean()) * 100, 1))
        out['bins'].append(b)
        print(f'  建物率 {lo_*100:3.0f}–{hi*100:3.0f}%  {b["n"]:2d}件  日陰率 平均 {b["mean"]:5.1f}%')
    out['excluded'] = [dict(name=r[0], area=r[1], bcov=round(r[2], 3))
                       for r in sorted(rows, key=lambda x: -x[2]) if r[2] > D.BLDG_COVER_MAX]
    print('  除外（建物率 > %.0f%%）：' % (D.BLDG_COVER_MAX * 100)
          + '・'.join(f'{e["name"]}公園（{e["bcov"]*100:.0f}%）' for e in out['excluded']))
    json.dump(out, open(paths.out('park_bias.json'), 'w'), ensure_ascii=False, indent=1)
    return out


if __name__ == '__main__':
    main()
