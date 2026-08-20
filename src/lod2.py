# -*- coding: utf-8 -*-
"""LOD2（実形状）の影。

★ なぜ要るか（2026-08-13）
  LOD1 は「底面 × measuredHeight の箱」。低層部と高層タワーが1つのIDにまとまっている
  複合施設で、影を大きく過大評価する。
  ［事実］サンシャインシティは LOD1 では 30,255㎡ × 234.1m の1つの箱だが、
         LOD2 の頂点標高は 26.2〜286.6m に分布し、大半は 40〜100m の帯にある。
  ［事実］この箱の高さを 234.1m→60m にすると、こかげの1位が3ケースすべてで変わった。

考え方は bridge.py と同じで、それを一般化しただけ。
  「面の頂点を1つずつ、その高さぶんだけ太陽の反対へずらす」
  → 立体のすべての面についてこれをやり、和を取ると、地面に落ちる影になる。
"""
import paths
import json, gzip, math
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shadow import FWD

PATH = paths.cache('lod2_faces.json.gz')
_F = None


def load_faces(path=PATH):
    """建物ID → 面のリスト。面は [経度, 緯度, 標高] の頂点列（平面直角に投影済み）"""
    global _F
    if _F is None:
        raw = json.load(gzip.open(path, 'rt', encoding='utf-8'))
        out = {}
        for k, faces in raw.items():
            ff = []
            for f in faces:
                xs, ys = FWD.transform([p[0] for p in f], [p[1] for p in f])
                ff.append(list(zip(xs, ys, [p[2] for p in f])))
            out[k] = ff
        _F = out
    return _F


def building_shadow(faces, alt_deg, az_deg, z0, simplify=0.4):
    """1棟ぶんの影。z0 はその建物の地盤高（標高）"""
    if alt_deg <= 0:
        return None
    t = math.tan(math.radians(alt_deg))
    sa = math.sin(math.radians(az_deg)); ca = math.cos(math.radians(az_deg))
    parts = []
    for f in faces:
        pts = []
        for x, y, z in f:
            L = max(z - z0, 0.0) / t
            pts.append((x - L * sa, y - L * ca))
        if len(pts) < 4:
            continue
        try:
            p = Polygon(pts)
            if not p.is_valid:
                p = p.buffer(0)
            if p.is_empty or p.area < 0.5:
                continue
            parts.append(p)
        except Exception:
            continue
    if not parts:
        return None
    g = unary_union(parts)
    return g.simplify(simplify) if simplify else g


def shadows(alt_deg, az_deg, ground_of):
    """LOD2 を持つ全建物の影。ground_of(x, y) は地盤高を返す関数"""
    out = {}
    for bid, faces in load_faces().items():
        x0, y0, _ = faces[0][0]
        g = building_shadow(faces, alt_deg, az_deg, ground_of(x0, y0))
        if g is not None and not g.is_empty:
            out[bid] = g
    return out
