"""高架（brid）のデッキ影。地盤高は ground.json（bldg:lod1Solid 最小z）の最近傍で補正する。"""
import paths
import json, math
import numpy as np
from shapely import STRtree, points
from shapely.geometry import Polygon
from shapely.ops import unary_union, transform
from shadow import FWD

_G = None


def ground_lookup():
    """EPSG:6677 の (x,y) -> 地盤高[m] を返す最近傍関数。
    ［注］scipy.spatial.cKDTree は使いません。shapely 2.x の STRtree.nearest で足ります
    （51,910点の索引構築0.09秒・679件の問い合わせ0.003秒）。依存を増やさないため。"""
    global _G
    if _G is None:
        pts = json.load(open(paths.cache('ground.json')))
        a = np.asarray(pts, dtype=float)
        x, y = FWD.transform(a[:, 0], a[:, 1])
        _G = (STRtree(points(np.asarray(x), np.asarray(y))), a[:, 2])
    tree, z = _G
    def f(px, py):
        return float(z[tree.nearest(points(px, py))])
    return f


def load_decks(min_area=20.0, max_dz=1.5, min_h=3.0):
    """水平・一定面積以上・地盤から min_h 以上の面を「高架デッキ」とみなす。
    戻り値: [(EPSG:6677 の Polygon, 地盤からの高さ[m])]"""
    gz = ground_lookup()
    decks = []
    for b in json.load(open(paths.cache('bridges.json'))):
        for ring in b['r']:
            zs = [p[2] for p in ring]
            if max(zs) - min(zs) > max_dz:
                continue                      # 側面・斜路は除く
            xy = [FWD.transform(p[0], p[1]) for p in ring]
            try:
                poly = Polygon(xy)
            except Exception:
                continue
            if (not poly.is_valid) or poly.area < min_area:
                continue
            c = poly.centroid
            h = sum(zs) / len(zs) - gz(c.x, c.y)
            if h < min_h:
                continue                      # 地表の橋・地覆は影を作らない
            decks.append((poly, h))
    return decks


def deck_shadow(decks, alt_deg, az_deg):
    """デッキ影＝平行移動した面のみ（側面掃引なし。床下は日陰にならないため元の面は含めない）。"""
    if alt_deg <= 0:
        return None
    out = []
    t = math.tan(math.radians(alt_deg))
    sa, ca = math.sin(math.radians(az_deg)), math.cos(math.radians(az_deg))
    for poly, h in decks:
        L = h / t
        dx, dy = -L * sa, -L * ca
        out.append(transform(lambda x, y, z=None, dx=dx, dy=dy: (x + dx, y + dy), poly))
    return unary_union(out) if out else None


def under_deck(decks):
    """デッキ直下（＝常時日陰・屋根あり）の面。"""
    return unary_union([p for p, _ in decks]) if decks else None
