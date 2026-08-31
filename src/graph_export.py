# -*- coding: utf-8 -*-
"""B-2：任意地点から引けるようにするための、ブラウザ配布用バンドルを書き出す（2026-08-21 新設）

★ 考え方
  ・「どのリンクが何時に何%日陰か」「どの公園が何時に何%日陰か」は出発地に依存しない。
    ＝ ここまでを事前計算して配れば、経路探索（ダイクストラ）だけをブラウザで回せる。
  ・mL への換算（hydration.effective_wbgt / sweat_rate）は純粋な算術なので JS に移植できる。
    ＝ 暑さ指数・遊び方・体重は、事前計算せずにブラウザ側で効かせられる（C42 が不要になる）。

出力: out/kokage_graph.json（と .min.json）
"""
import json, math, sys
import networkx as nx
from pyproj import Transformer
import route as R
import destination as D
import paths
from shadow import load_buildings, shadow
import bridge
from shapely.ops import unary_union
from shapely.geometry import Point

HOURS = (11, 12, 13, 14, 15, 16)
WBGT_DUMMY = 29.0          # 日陰率には効かない（mL にしか効かない）
STROLLER = False
ENTRY_R = 60.0        # 公園ポリゴンからこの距離以内のノードを「入口候補」にする
INV = Transformer.from_crs(6677, 4326, always_xy=True)


def main():
    # ---- 1) ノードとエッジ（時刻別の日陰率）----
    node_idx, nodes_lat, nodes_lon, nodes_x, nodes_y, node_ids = {}, [], [], [], [], []
    edges = {}          # (u,v) -> dict
    park_shade = {}     # name -> [6]

    for hi, h in enumerate(HOURS):
        print(f'■ {h}:00 を計算中…', flush=True)
        G, alt, U, FOOT = D._prepare(h, WBGT_DUMMY, STROLLER)
        if hi == 0:
            for n in G.nodes:
                node_idx[n] = len(node_ids)
                x, y = G.nodes[n]['x'], G.nodes[n]['y']
                lon, lat = INV.transform(x, y)
                node_ids.append(n)
                nodes_x.append(round(x, 2)); nodes_y.append(round(y, 2))
                nodes_lat.append(round(lat, 6)); nodes_lon.append(round(lon, 6))
        for u, v, e in G.edges(data=True):
            k = (node_idx[u], node_idx[v])
            r = edges.setdefault(k, dict(dist=round(e['dist'], 2),
                                         wait=round(e['wait'], 4),
                                         shade=[0] * len(HOURS)))
            r['shade'][hi] = int(round(e['shade'] * 1000))

        # ---- 公園の日陰率（出発地に依存しない）----
        cands, _hit, _miss = D.load_candidates()
        for kind, nm, lo, la, area, indoor in cands:
            if indoor:
                park_shade.setdefault(nm, [1000] * len(HOURS))
                continue
            c, gap_poly = D.park_polygon(lo, la, area, nm)   # ★ 2026-08-31：名前を渡す
            geom = 'luse'
            if c is None:
                geom = 'circle'
                c = Point(*R.FWD.transform(lo, la)).buffer(math.sqrt(area / math.pi))
            ground = c.difference(FOOT)
            if ground.area <= 0:
                park_shade.setdefault(nm, [0] * len(HOURS))
                continue
            sh = U.difference(FOOT).intersection(c).area / max(ground.area, 1e-9)
            park_shade.setdefault(nm, [0] * len(HOURS))[hi] = int(round(min(sh, 1.0) * 1000))

    # ---- 2) 候補地のメタ ----
    # ★ 2026-08-22：行き先の終点を「公園の点の最寄りノード」から
    #   「公園ポリゴンの縁に近いノードの中から選ぶ」に変える（tasks.md B3e）。
    #   区の公園データは点＋面積しか無く、形は PLATEAU の土地利用ポリゴンから拾っている。
    #   この2つが最大146mずれており、東池袋中央公園の点はサンシャインシティの建物の中にあった。
    #   ここでは候補ノード（ポリゴンから ENTRY_R 以内）と、その公園までの残り距離を書き出す。
    #   どれを終点にするかは、合計mLが最小のものをブラウザ側で選ぶ。
    cands, _hit, _miss = D.load_candidates()
    G0, alt0, U0, FOOT0 = D._prepare(HOURS[0], WBGT_DUMMY, STROLLER)
    nodes_pt = [(node_ids[i], nodes_x[i], nodes_y[i]) for i in range(len(node_ids))]

    # ★ 2026-08-22：1つの公共空地ポリゴンを2つの公園が掴むことがある。
    #   （南池袋みどり公園 572㎡ と 南池袋第二公園 849㎡ が同じポリゴンを共有していた）
    #   ポリゴンは点がいちばん近い公園に1つだけ割り当て、負けた方は円近似に落とす。
    poly_of = {}
    owner = {}
    for kind, nm, lo, la, area, indoor in cands:
        if indoor:
            continue
        c, _g = D.park_polygon(lo, la, area, nm)   # ★ 2026-08-31：名前を渡す
        if c is None:
            continue
        key = (round(c.centroid.x, 1), round(c.centroid.y, 1))
        d = c.distance(Point(*R.FWD.transform(lo, la)))
        poly_of[nm] = (key, c)
        if key not in owner or d < owner[key][1]:
            owner[key] = (nm, d)
    dropped = [nm for nm, (key, _c) in poly_of.items() if owner[key][0] != nm]
    if dropped:
        print('★ ポリゴンの取り合いで円近似に落とした公園：%s' % '／'.join(dropped))

    parks = []
    for kind, nm, lo, la, area, indoor in cands:
        rec = dict(kind=kind, name=nm, indoor=bool(indoor),
                   lon=round(lo, 6), lat=round(la, 6),
                   area=(round(area) if area else None),
                   shade=park_shade.get(nm, [0] * len(HOURS)))
        poly = None
        if not indoor:
            c, _g = D.park_polygon(lo, la, area, nm)   # ★ 2026-08-31：名前を渡す
            if c is not None and nm in poly_of and owner[poly_of[nm][0]][0] != nm:
                c = None                      # ★ ポリゴンは他の公園のもの
            rec['geom'] = ('tokyo' if D._norm(nm) in D.load_tokyo_parks()
                           or D.PARK_ALIAS.get(D._norm(nm), '') in D.load_tokyo_parks()
                           else 'luse') if c is not None else 'circle'
            if c is None:
                c = Point(*R.FWD.transform(lo, la)).buffer(math.sqrt(area / math.pi))
            rec['bcov'] = round(1.0 - c.difference(FOOT0).area / c.area, 3)
            poly = c
            cen = c.centroid
            rec['cx'] = round(cen.x, 1); rec['cy'] = round(cen.y, 1)   # ラベルはここに置く
        if poly is None:                      # 屋内は建物の点そのもの
            px, py = R.FWD.transform(lo, la)
            poly = Point(px, py)
            rec['cx'] = round(px, 1); rec['cy'] = round(py, 1)
        # 入口候補：ポリゴンから ENTRY_R 以内のノード。gap は歩いて詰める残りの距離
        ent, gaps = [], []
        for i, (nid, x, y) in enumerate(nodes_pt):
            q = Point(x, y)
            d = 0.0 if poly.geom_type != 'Point' and poly.contains(q) else poly.distance(q)
            if d <= ENTRY_R:
                ent.append(i); gaps.append(round(d, 1))
        if not ent:                            # 1つも無ければ最寄り1点だけ入れる
            i = min(range(len(nodes_pt)),
                    key=lambda k: poly.distance(Point(nodes_pt[k][1], nodes_pt[k][2])))
            ent = [i]; gaps = [round(poly.distance(Point(nodes_pt[i][1], nodes_pt[i][2])), 1)]
        rec['entry'] = ent
        rec['entry_gap'] = gaps
        parks.append(rec)
    print('入口候補ノード：1件あたり中央値 %d 個' %
          sorted(len(p['entry']) for p in parks)[len(parks) // 2])

    eu = [k[0] for k in edges]; ev = [k[1] for k in edges]
    bundle = dict(
        meta=dict(hours=list(HOURS), stroller=STROLLER,
                  shade_scale=1000, crs='EPSG:6677',
                  speed_m_per_min=R.SPEED_M_PER_MIN,
                  signal_wait_sec=R.SIGNAL_WAIT_SEC,
                  shadow_date='2026-08-12', entry_r=ENTRY_R,
                  note='shade は 0..1000（‰）。dist は m、wait は分。'),
        nodes=dict(id=node_ids, lat=nodes_lat, lon=nodes_lon, x=nodes_x, y=nodes_y),
        edges=dict(u=eu, v=ev,
                   dist=[edges[k]['dist'] for k in edges],
                   wait=[edges[k]['wait'] for k in edges],
                   shade=[edges[k]['shade'] for k in edges]),
        parks=parks)

    p = paths.out('kokage_graph.json')
    json.dump(bundle, open(p, 'w'), ensure_ascii=False, indent=1)
    pm = paths.out('kokage_graph.min.json')
    json.dump(bundle, open(pm, 'w'), ensure_ascii=False, separators=(',', ':'))
    import os, gzip
    with open(pm, 'rb') as f:
        gz = gzip.compress(f.read(), 9)
    open(paths.out('kokage_graph.min.json.gz'), 'wb').write(gz)
    print(f'\n★ ノード {len(node_ids)} / エッジ {len(edges)} / 候補地 {len(parks)}')
    print(f'   {os.path.getsize(p)/1024:.0f} KB (indent) / {os.path.getsize(pm)/1024:.0f} KB (min) / {len(gz)/1024:.0f} KB (gzip)')
    print('DONE -> out/kokage_graph.json')


if __name__ == '__main__':
    main()
