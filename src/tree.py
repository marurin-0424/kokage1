"""こかげ：街路樹の影（M7）

東京都建設局「都道の街路樹」の 樹高(m)・枝張(m) を使い、樹冠を球で近似して
地面に落ちる影（円）を出す。

建物と違い、樹冠は地面まで壁が無いので「側面の掃引」も「足元の面」も足さない。
＝ 平行移動した円だけが影になる（低い太陽では足元は日なたに戻る。これは正しい）。

注意：このデータは【都道のみ】。区道の街路樹は入っていない。
"""
import paths
import csv, io, math, json
from shapely.geometry import Point
from shapely.ops import unary_union
from shadow import FWD

CSV = paths.raw('tokyo_gairoju.csv')
# 樹冠半径の下限・上限（m）。データの外れ値を潰す
R_MIN, R_MAX = 0.5, 7.5
H_MIN = 1.5                       # 樹冠中心の最低高さ


def load_trees(bbox=None, path=CSV):
    """(x, y, r, hc, 路線名) のリストを返す。bbox=(lo1, la1, lo2, la2) は経緯度"""
    out = []
    with io.open(path, encoding='cp932', errors='replace') as f:
        for row in csv.DictReader(f):
            try:
                lo = float(row['経度']); la = float(row['緯度'])
                h = float(row['樹高(m)']); w = float(row['枝張(m)'])
            except (TypeError, ValueError):
                continue
            if bbox and not (bbox[0] <= lo <= bbox[2] and bbox[1] <= la <= bbox[3]):
                continue
            r = min(max(w / 2.0, R_MIN), R_MAX)
            hc = max(h - r, H_MIN)            # 樹冠を半径 r の球とみなし、中心の高さ
            x, y = FWD.transform(lo, la)
            out.append((x, y, r, hc, row.get('路線名', '')))
    return out


def tree_shadow(trees, alt_deg, az_deg):
    """樹冠の影（円）のリスト。太陽が沈んでいれば空"""
    if alt_deg <= 0:
        return []
    t = math.tan(math.radians(alt_deg))
    sa = math.sin(math.radians(az_deg)); ca = math.cos(math.radians(az_deg))
    out = []
    for x, y, r, hc, _ in trees:
        L = hc / t
        out.append(Point(x - L * sa, y - L * ca).buffer(r, quad_segs=6))
    return out
