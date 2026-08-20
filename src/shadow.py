"""こかげ：影ポリゴンの最小実装（§9-1の20行 + 検証）
依存：shapely / pyproj / pvlib のみ。PLATEAU GIS Converter は不要。
"""
import json, math
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo          # ★ §9-3 落とし穴3：pytz は使わない
from shapely.geometry import Polygon, LineString, shape
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer
import pvlib

LAT, LON = 35.7295, 139.7109           # 池袋駅
TZ = ZoneInfo("Asia/Tokyo")
# EPSG:6677 = 平面直角座標系IX系（関東）。always_xy=True で x=東・y=北
FWD = Transformer.from_crs("EPSG:6668", "EPSG:6677", always_xy=True)

# ---------------------------------------------------------------- ★ここが「20行」
def shadow(poly: Polygon, height: float, alt_deg: float, az_deg: float) -> Polygon:
    """建物フットプリント（平面直角座標・m）→ 影ポリゴン"""
    if alt_deg <= 0:
        return poly
    L = height / math.tan(math.radians(alt_deg))      # 日影倍率 = cot(太陽高度)
    dx = -L * math.sin(math.radians(az_deg))          # 影は太陽の反対へ
    dy = -L * math.cos(math.radians(az_deg))
    moved = transform(lambda x, y, z=None: (x + dx, y + dy), poly)
    parts = [poly, moved]
    c = list(poly.exterior.coords)
    for (x1, y1), (x2, y2) in zip(c[:-1], c[1:]):     # 側面の四角形で掃引を埋める
        parts.append(Polygon([(x1, y1), (x2, y2), (x2 + dx, y2 + dy), (x1 + dx, y1 + dy)]))
    return unary_union(parts)
# ----------------------------------------------------------------------------

def sun(dt):
    sp = pvlib.solarposition.get_solarposition(dt, LAT, LON)
    return float(sp["apparent_elevation"].iloc[0]), float(sp["azimuth"].iloc[0])


def load_buildings(path, min_h=0.0):
    out = []
    for b in json.load(open(path)):
        if b["h"] < min_h or len(b["r"]) < 4:
            continue
        xs, ys = FWD.transform([p[0] for p in b["r"]], [p[1] for p in b["r"]])
        try:
            p = Polygon(zip(xs, ys))
            if not p.is_valid:
                p = p.buffer(0)
            if p.is_empty or p.area < 1:
                continue
        except Exception:
            continue
        out.append((p, b["h"], b))
    return out


def load_links(path):
    gj = json.load(open(path))
    out = []
    for f in gj["features"]:
        g = shape(f["geometry"])
        xs, ys = FWD.transform([c[0] for c in g.coords], [c[1] for c in g.coords])
        out.append((LineString(zip(xs, ys)), f["properties"]))
    return out
