"""こかげ：熱ストレスを重みにした経路探索（NetworkX＋ダイクストラ）

エッジコスト＝その区間で子どもに必要になる水分量(mL)。
「合計コスト最小」＝「飲ませる量が最小」の経路が出る。
"""
import paths
import sys, json, math
from datetime import datetime
import pandas as pd
import networkx as nx
from shapely.strtree import STRtree
from shapely.geometry import Point
from shadow import load_buildings, load_links, shadow, sun, TZ, FWD
from sidewalk import shaded_ratio
from hydration import sweat_rate, effective_wbgt, Segment, METS
import bridge

SPEED_M_PER_MIN = 53.1     # ★［事実］3〜5歳を連れた歩行速度の実測値（2026-08-15 更新）。
#   walk-timer.html で n=3・総距離1,420m を計測：51.6／53.8／54.5 m/分。
#   距離加重＝1,420m ÷ 26.76分 ＝ 53.1 m/分。ばらつきは ±3%。
#   ★ 旧値 35.0 は［推測］だった。35→53.1 で **答え（1位の行き先）が入れ替わる**。
#     入れ替わり点は約 38 m/分（how-it-works.md §4）。
#   ★ METs は walk_slow=2.0 のまま。R-09 の区分は「非常に遅い＝53m/分未満」で
#     53.1 はわずかに外れるが、53(2.0)〜67(3.0) の線形補間で 2.007 のため実質2.0。
#   ［参考］抱っこは 108.7 m/分（n=1・歩いたときの2.05倍）。v0では未対応。
SIGNAL_WAIT_SEC = 30.0     # ［推測］信号待ちの平均。サイクルの1/4想定
BW_KG = 15.0

# ベビーカーで通れない条件（data-sources.md §発見①）
def impassable(pr):
    return (str(pr.get('route_type')) == '6'          # 階段
            or str(pr.get('lev_diff')) == '5'          # 段差10cm超
            or str(pr.get('width')) == '1'             # 幅員1m未満
            or str(pr.get('vtcl_slope')) in ('7', '8'))  # 勾配18%超


def build(hour, wbgt_base=29.0, harsh=True, stroller=True, sun_frac=1.0, trees=False, use_lod2=True):
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    N = json.load(open(paths.raw('ikebukuro_node.geojson')))
    dt = pd.DatetimeIndex([datetime(2026, 8, 12, hour, 0, tzinfo=TZ)])
    alt, az = sun(dt)
    # ★ LOD2（実形状）を持つ建物は、箱ではなく実形状で影を作る（lod2.py・2026-08-13）。
    #   LOD1の箱はサンシャインシティで影を41%も過大評価していた（72,992㎡→42,949㎡）。
    L2 = {}
    if use_lod2:
        import lod2
        L2 = lod2.shadows(alt, az, bridge.ground_lookup())
    S = [shadow(p.simplify(0.3), h, alt, az) for p, h, b in B if b['id'] not in L2]
    S += list(L2.values())
    # 高架（首都高5号池袋線など）のデッキ影＋デッキ直下。地盤高は ground.json で場所ごとに補正
    decks = bridge.load_decks()
    for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)):
        if g is not None:
            S += list(g.geoms) if hasattr(g, 'geoms') else [g]
    # 街路樹（M7）。既定は False ＝ 使わない。データが都道のみで、入れると都道だけが
    # 系統的に涼しくなる偏りが出るため（tree_eval.py で測定・roadmap.md §3-3）。
    if trees:
        import tree as _tree
        S += _tree.tree_shadow(_tree.load_trees(bbox=(139.690, 35.700, 139.740, 35.745)), alt, az)
    tree = STRtree(S)

    G = nx.Graph()
    for f in N['features']:
        x, y = FWD.transform(*f['geometry']['coordinates'][:2])
        G.add_node(str(f['properties']['node_id']), x=x, y=y)

    skipped = 0
    for ls, pr in L:
        a, b = str(pr.get('start_id')), str(pr.get('end_id'))
        if a not in G or b not in G:
            skipped += 1
            continue
        if stroller and impassable(pr):
            continue                                   # ＝コスト∞
        sh = shaded_ratio(ls, tree, S)                 # 日陰率 0..1
        crossing = str(pr.get('rt_struct')) in ('3', '4')
        signal = crossing and str(pr.get('tfc_signal')) != '1'
        walk_min = ls.length / SPEED_M_PER_MIN
        wait_min = (SIGNAL_WAIT_SEC / 60.0) if signal else 0.0

        ml = 0.0
        for minutes, mets in ((walk_min, METS['walk_slow']), (wait_min, METS['stand'])):
            if minutes <= 0:
                continue
            for frac, sunlit in ((1 - sh, True), (sh, False)):
                if frac <= 0:
                    continue
                w = effective_wbgt(wbgt_base, Segment('', 0, 'stand', sunlit=sunlit, harsh=harsh), sun_frac)
                ml += sweat_rate(w, mets, BW_KG) * minutes * frac
        G.add_edge(a, b, cost=ml, dist=ls.length, geom=ls,
                   sun_min=(walk_min + wait_min) * (1 - sh),
                   min=walk_min + wait_min, wait=wait_min, shade=sh)
    return G, alt, az, skipped


def nearest(G, lon, lat):
    x, y = FWD.transform(lon, lat)
    return min(G.nodes, key=lambda n: (G.nodes[n]['x'] - x) ** 2 + (G.nodes[n]['y'] - y) ** 2)


def summarize(G, path):
    # sd＝日なたを歩く「距離」。sun_min（時間）は信号待ちを含むので、
    # 画面の「往復距離のうち日なた何m」には使えない（2026-08-15 追加）。
    d = s = t = w = c = sd = 0.0
    for u, v in zip(path[:-1], path[1:]):
        e = G[u][v]
        d += e['dist']; s += e['cost']; t += e['min']; w += e['wait']; c += e['sun_min']
        sd += e['dist'] * (1 - e['shade'])
    return dict(dist=d, ml=s, minutes=t, wait=w, sun_min=c, sun_dist=sd)
