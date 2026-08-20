# -*- coding: utf-8 -*-
"""公園の日陰率を、現地実測と突き合わせるための診断（2026-08-14 新設）

★ なぜ要るか
  2026-08-14 8:30・9:00 の現地確認で、高田の2公園の建物影が大きく過大に出た
  （高田一丁目児童遊園：モデル41.6% vs 実測1割）。原因を切り分けるために、
  ① どの建物が影を作っているか ② 地盤高の差は効いているか
  ③ 上階のセットバック（斜線制限）を入れると実測に寄るか
  を1本で出せるようにした。data-sources.md §1d-4 の数字はすべてこれで再生成できる。

使い方
  python3 park_diag.py            # 既定（高田の2公園・8:30/9:00）
  python3 park_diag.py 12 14 16   # 時刻を指定

［注］地盤高（takada_dem.json）が無い場合、地盤の節はスキップする。
"""
import paths
import sys, json, math
from datetime import datetime
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shadow import load_buildings, shadow, sun, TZ, FWD

# 公園の点は豊島区の公共施設一覧の座標（＝ luse ポリゴンを引き当てるための種）
PARKS = [('山吹の里公園',        139.71806, 35.71413, 603.0),
         ('高田一丁目児童遊園',  139.71724, 35.71547, 447.0)]
LUSE_R, LUSE_LO, LUSE_HI = 80.0, 0.5, 2.0     # destination.park_polygon と同条件
FLOOR_H = 2.85                                 # 階高の仮定［推測］
DIRS = ['北','北北東','北東','東北東','東','東南東','南東','南南東',
        '南','南南西','南西','西南西','西','西北西','北西','北北西']


def solar(y, m, d, hh, mm=0):
    return sun(pd.DatetimeIndex([datetime(y, m, d, hh, mm, tzinfo=TZ)]))


def to_plane(ring):
    xs, ys = FWD.transform([p[0] for p in ring], [p[1] for p in ring])
    return list(zip(xs, ys))


def load_luse():
    out = []
    for x in json.load(open(paths.cache('luse_open_space.json'))):
        try:
            q = Polygon(x['ring'], x.get('holes') or [])
            if not q.is_valid:
                q = q.buffer(0)
            if q.is_empty:
                continue
            gm = Polygon(to_plane(list(q.exterior.coords))).buffer(0)
            out.append((q, gm))
        except Exception:
            pass
    return out


def park_polygon(luse, lo, la, area):
    pt = Point(lo, la); d = LUSE_R / 111000.0
    ok = [(q, gm) for q, gm in luse
          if q.distance(pt) < d and LUSE_LO <= gm.area / area <= LUSE_HI]
    if not ok:
        return None
    ins = [t for t in ok if t[0].contains(pt)]
    return (max(ins, key=lambda t: t[1].area) if ins
            else min(ok, key=lambda t: t[0].distance(pt)))[1]


def ground_lookup():
    """DEM（takada_dem.json）から地盤高を返す関数。無ければ None"""
    try:
        D = json.load(open(paths.cache('takada_dem.json')))
    except FileNotFoundError:
        return None
    import numpy as np
    from scipy.spatial import cKDTree
    xs, ys = FWD.transform([p[0] for p in D], [p[1] for p in D])
    X = np.column_stack([xs, ys]); Z = np.array([p[2] for p in D])
    T = cKDTree(X)

    def gz(x, y, k=6):
        dist, idx = T.query([x, y], k=k)
        w = 1 / np.maximum(dist, 0.3)
        return float((Z[idx] * w).sum() / w.sum())
    return gz


def shade_union(near, alt, az, setback=0.0, nfloor=1, floor_h=FLOOR_H, dz=None):
    """近傍建物の影。setback>0 なら最上 nfloor 層を setback[m] 内側に下げた立体として扱う。
    dz(p) が与えられれば「建物の地盤高 − 公園の地盤高」を足して影を伸縮させる。"""
    parts = []
    for p, h, _ in near:
        p = p.simplify(0.4)
        hh = h + (dz(p) if dz else 0.0)
        if setback <= 0 or hh < floor_h * (nfloor + 1):
            parts.append(shadow(p, max(hh, 0.1), alt, az)); continue
        parts.append(shadow(p, hh - floor_h * nfloor, alt, az))
        up = p.buffer(-setback)
        for g in (up.geoms if hasattr(up, 'geoms') else [up]):
            if not g.is_empty and g.area > 1:
                parts.append(shadow(g, hh, alt, az))
    return unary_union(parts)


def main(hours):
    B = load_buildings(paths.cache('takada_bldg_lod0.json'))
    FOOT = unary_union([p.simplify(0.4) for p, h, _ in B])
    luse = load_luse()
    gz = ground_lookup()
    PP = {nm: park_polygon(luse, lo, la, ar) for nm, lo, la, ar in PARKS}
    for nm, gm in PP.items():
        print(f'{nm}: ポリゴン {gm.area:.1f}㎡'
              + (f' ／ 地盤 {gz(gm.centroid.x, gm.centroid.y):.2f}m' if gz else ''))

    for hh, mm in hours:
        alt, az = solar(2026, 8, 14, hh, mm)
        print(f'\n=== {hh:02d}:{mm:02d}  太陽高度 {alt:.1f}°・方位 {az:.1f}°'
              f'（影は {(az+180)%360:.0f}° へ・日影倍率 {1/math.tan(math.radians(alt)):.2f}）')
        for nm, _, _, _ in PARKS:
            gm = PP[nm]; c = gm.centroid; ground = gm.difference(FOOT)
            near = [(p, h, b) for p, h, b in B if p.distance(gm) < 90]
            zp = gz(c.x, c.y) if gz else 0.0
            f = lambda U: U.difference(FOOT).intersection(gm).area / ground.area
            print(f' ■ {nm}')
            # ① 寄与建物
            rows = []
            for p, h, b in near:
                a = shadow(p.simplify(0.4), h, alt, az).difference(FOOT).intersection(gm).area
                if a > 1:
                    ang = math.degrees(math.atan2(p.centroid.x - c.x, p.centroid.y - c.y)) % 360
                    rows.append((a / ground.area, h, p.area, p.distance(gm),
                                 DIRS[int((ang + 11.25) // 22.5) % 16],
                                 (gz(p.centroid.x, p.centroid.y) - zp) if gz else None))
            rows.sort(reverse=True)
            for r, h, ar, d, dr, dzb in rows[:3]:
                s = f'   寄与{r:6.1%}｜高さ{h:5.1f}m・底面{ar:5.0f}㎡｜公園の{dr}・{d:.1f}m'
                if dzb is not None:
                    s += f'｜地盤差 {dzb:+.2f}m'
                print(s)
            # ② 地盤補正
            base = f(shade_union(near, alt, az))
            line = f'   日陰率 {base:.1%}'
            if gz:
                dz = lambda p: gz(p.centroid.x, p.centroid.y) - zp
                line += f' ／ 地盤補正 {f(shade_union(near, alt, az, dz=dz)):.1%}'
            print(line)
            # ③ 上階セットバックの感度
            for nf in (1, 2):
                vals = [(s, f(shade_union(near, alt, az, setback=s, nfloor=nf))) for s in (1, 2, 3, 4)]
                print(f'   上{nf}層を内側へ： ' + ' / '.join(f'{s}m→{v:.1%}' for s, v in vals))


if __name__ == '__main__':
    hs = [(int(a), 0) for a in sys.argv[1:]] or [(8, 30), (9, 0)]
    main(hs)
