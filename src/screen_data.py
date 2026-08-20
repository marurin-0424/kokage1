"""こかげ v0（ヒアリング用）の事前計算。
出発地3 × 時刻2 ＋ WBGTゲート1 ＋ 範囲外1 を JSON に書き出す。
"""
import paths
import sys, json, math, io, zipfile, csv
import destination as D
from route import build, summarize
from shadow import FWD, load_links, load_buildings, shadow, sun, TZ
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from datetime import datetime
import pandas as pd
import bridge

ORIGINS = {
    'toden_zoshigaya': dict(label='都電雑司ヶ谷駅', sub='都電荒川線', lon=139.717760, lat=35.724081),
    'ikebukuro_east':  dict(label='池袋駅東口',     sub='JR・私鉄・地下鉄', lon=139.71150, lat=35.72950),
}
OUT_OF_RANGE = dict(key='metro_zoshigaya', label='地下鉄 雑司が谷駅', sub='東京メトロ副都心線',
                    lon=139.715050, lat=35.720537)
HOURS = [12, 14]
WBGT, STAY, BW = 29.0, 60.0, 15.0


def path_segments(G, path):
    segs = []
    for u, v in zip(path[:-1], path[1:]):
        e = G[u][v]
        segs.append(dict(xy=[[round(x, 1), round(y, 1)] for x, y in e['geom'].coords],
                         shade=round(e['shade'], 3), dist=round(e['dist'], 1)))
    return segs


def case(okey, hour, wbgt=WBGT, purpose='outdoor_play'):
    o = ORIGINS[okey]
    r = D.recommend(hour=hour, wbgt=wbgt, stay_min=STAY, stroller=False, bw=BW,
                    purpose=purpose, origin=(o['lon'], o['lat']), top=300)
    G = r['G']; m = r['main']; a = r['alt']
    parks = [x for x in r['all'] if x['kind'] == 'park']
    ox, oy = FWD.transform(o['lon'], o['lat'])
    d = dict(origin=okey, origin_label=o['label'], origin_sub=o['sub'],
             origin_xy=[round(ox, 1), round(oy, 1)], hour=hour, wbgt=wbgt,
             gate=r['gate'], level=r['level'], advice=r['advice'], rest=r['rest'],
             alt_deg=round(r['alt_deg'], 1),
             main=dict(name=m['name'], dist=round(m['dist']), move=round(m['move']),
                       stay=round(m['stay']), total=round(m['total']),
                       shade=round(m['shade'], 3), sun_min=round(m['sun_min'], 1),
                       minutes=round(m['minutes']), acc=m['acc'], gap=round(m['gap']),
                       indoor=m['indoor'], sun_dist=round(m['sun_dist'])),
             alt=(dict(name=a['name'], total=round(a['total'])) if a else None),
             segs=path_segments(G, m['path']),
             # ★ move/stay/sun_dist/sun_min は 2026-08-15 追加。
             #   画面（モバイル版）が2位・3位のカードにも内訳と日なた比率を出すため。
             ranking=[dict(name=x['name'], total=round(x['total']), dist=round(x['dist']),
                           shade=round(x['shade'], 3), acc=x['acc'], geom=x.get('geom'),
                           move=round(x['move']), stay=round(x['stay']),
                           sun_dist=round(x['sun_dist']), sun_min=round(x['sun_min'], 1),
                           indoor=x['indoor'], gap=round(x['gap']))
                      for x in (parks if not r['gate'] else r['all'])[:6]],
             n_park=len(parks), n_l1=sum(1 for x in parks if x['acc'] == 'L1'),
             n_cand=r['n_cand'], reach=r['reach'], excluded=r['excluded'],
             n_luse=sum(1 for x in parks if x.get('geom') == 'luse'))
    # 行き先の座標
    for kind, nm, lo, la, area, indoor in D.load_candidates()[0]:
        if nm == m['name']:
            X, Y = FWD.transform(lo, la)
            d['main']['xy'] = [round(X, 1), round(Y, 1)]
            d['main']['radius'] = round(math.sqrt(area / math.pi), 1) if area else 25.0
            break
    return d


def geometry(hour):
    """描画用の静的レイヤ（建物・影・高架・NWリンク）"""
    B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    L = load_links(paths.raw('ikebukuro_link.geojson'))
    dt = pd.DatetimeIndex([datetime(2026, 8, 12, hour, 0, tzinfo=TZ)])
    alt, az = sun(dt)
    import lod2
    L2 = lod2.shadows(alt, az, bridge.ground_lookup())
    S = unary_union([shadow(p.simplify(0.5), h, alt, az) for p, h, b in B if b['id'] not in L2]
                    + list(L2.values()))
    decks = bridge.load_decks()
    BR = unary_union([g for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)) if g])
    bld = unary_union([p.simplify(0.5) for p, h, _ in B if h >= 6])
    return dict(alt=round(alt, 1), az=round(az, 1),
                shadow=S.simplify(1.0), bridge=BR.simplify(1.0), bldg=bld.simplify(1.0),
                links=[(ls, pr) for ls, pr in L])


if __name__ == '__main__':
    out = dict(cases={}, meta=dict(wbgt=WBGT, stay=STAY, bw=BW))
    for h in HOURS:
        for k in ORIGINS:
            c = case(k, h)
            out['cases'][f'{k}_{h}'] = c
            print(f'{k} {h}:00 -> {c["main"]["name"]} {c["main"]["total"]}mL', flush=True)
    g = case('toden_zoshigaya', 14, wbgt=31.5)
    out['cases']['gate'] = g
    print('gate ->', g['main']['name'], g['main']['total'], flush=True)
    json.dump(out, open(paths.out('screen_cases.json'), 'w'), ensure_ascii=False)
    print('DONE')
