# -*- coding: utf-8 -*-
"""地図の目印（ラベル）を書き出す（2026-08-21 新設）

★ なぜ要るか
  v1c の地図には名前が1つも無く、「どこがどこだか分からない」という指摘を受けた。
  新しいデータは取らない。すでに使っている5件の中から名前を拾う。

出どころ
  ・建物名  … 東京都3Dデジタルマップ CityGML の gml:name（out/bldg_names.json）
  ・公園名  … 豊島区 都市公園geojson（destination.load_candidates）
  ・屋内施設… 豊島区 公共施設一覧（同上）
  ・地下出入口/停留所 … 歩行空間ネットワーク付随の都市設備（cache/frn_points.json）

出力: out/map_labels.json
  rank … 1=常に出す（駅・大規模）／2=中ズーム／3=高ズームのみ
"""
import json, re
import destination as D
import paths
from shadow import FWD

BBOX = (35.700, 35.755, 139.680, 139.745)   # lat0, lat1, lon0, lon1

# ★ rank の付け方。歩いている人が現在地を照合するのに使う順。
RANK1 = ('駅',)
RANK2 = ('大学', '警察署', '消防署', '病院', '小学校', '中学校', '高等学校', '区役所',
         '保健所', '図書館', '博物館', '美術館', 'シティ', 'タウン', 'タワー')
RANK3 = ('郵便局', '交番', '駐在所', '出張所', '職業安定所', '税務署', '法務局', '労働局')


def rank_of(name):
    if name.endswith(RANK1) or ('駅' in name and len(name) <= 8):
        return 1
    for k in RANK2:
        if k in name:
            return 2
    for k in RANK3:
        if k in name:
            return 3
    return 2


def inside(la, lo):
    return BBOX[0] <= la <= BBOX[1] and BBOX[2] <= lo <= BBOX[3]


def main():
    out = []
    seen = set()

    # 1) 建物名（CityGML gml:name）
    try:
        for b in json.load(open(paths.out('bldg_names.json'))):
            nm, la, lo = b['name'], b['lat'], b['lon']
            if not inside(la, lo):
                continue
            key = (nm, round(la, 4), round(lo, 4))
            if key in seen:
                continue
            seen.add(key)
            x, y = FWD.transform(lo, la)
            out.append(dict(t='bldg', n=nm, x=round(x, 1), y=round(y, 1), r=rank_of(nm)))
    except FileNotFoundError:
        print('bldg_names.json が無いので建物名は入れません')

    # 2) 公園・屋内施設
    # ★ 2026-08-22：公園のラベルは「点の座標」ではなく「ポリゴンの重心」に置く。
    #   区の公園データの点は最大146mずれており、東池袋中央公園のラベルが
    #   サンシャインシティの建物の真ん中に出ていた。
    # ★ 2026-08-22：重心は自分で計算し直さず、バンドル（kokage_graph.json）の cx/cy を使う。
    #   ポリゴンの取り合いを解いた結果と、ラベルの位置を必ず一致させるため。
    try:
        bundle = {p['name']: p for p in json.load(open(paths.out('kokage_graph.json')))['parks']}
    except FileNotFoundError:
        bundle = {}
        print('★ kokage_graph.json が無いので、ラベルは公園の点のままです')
    cands, _h, _m = D.load_candidates()
    moved = 0
    for kind, nm, lo, la, area, indoor in cands:
        if not inside(la, lo):
            continue
        x, y = FWD.transform(lo, la)
        rec = bundle.get(nm)
        if not indoor and rec and rec.get('cx') is not None:
            if ((rec['cx'] - x) ** 2 + (rec['cy'] - y) ** 2) ** 0.5 > 5:
                moved += 1
            x, y = rec['cx'], rec['cy']
        out.append(dict(t='park' if not indoor else 'fac', n=nm,
                        x=round(x, 1), y=round(y, 1), r=1 if not indoor else 2))
    print('公園ラベルをバンドルの重心へ合わせた件数：%d' % moved)

    # 3) 地下出入口・停留所（記号だけ。名前は持っていない）
    pts = []
    for f in json.load(open(paths.cache('frn_points.json'))):
        if f['label'] not in ('地下出入口', '停留所'):
            continue
        if not inside(f['lat'], f['lon']):
            continue
        x, y = FWD.transform(f['lon'], f['lat'])
        pts.append(dict(t='sub' if f['label'] == '地下出入口' else 'bus',
                        x=round(x, 1), y=round(y, 1)))

    # ★ 同じ名前が近くに何個も出る（池袋駅は棟ごとに名前が付いていて4個あった）。
    #   300m 以内の同名はまとめて重心1点にする。
    def dedupe(items, r=300.0):
        keep = []
        for it in items:
            # ★ 駅は棟ごとに名前が付いていて離れて出る（池袋駅は4個あった）。駅だけ広く取る
            rr = 700.0 if it['n'].endswith('駅') else r
            for k in keep:
                if k['n'] == it['n'] and abs(k['x'] - it['x']) < rr and abs(k['y'] - it['y']) < rr:
                    k['x'] = (k['x'] + it['x']) / 2
                    k['y'] = (k['y'] + it['y']) / 2
                    k['_c'] = k.get('_c', 1) + 1
                    break
            else:
                keep.append(it)
        for k in keep:
            k['x'] = round(k['x'], 1); k['y'] = round(k['y'], 1); k.pop('_c', None)
        return keep

    n0 = len(out)
    out = dedupe(out)
    print('同名まとめ %d → %d' % (n0, len(out)))

    bundle = dict(labels=out, points=pts,
                  note='rank 1=常時 / 2=中ズーム / 3=高ズームのみ。座標は EPSG:6677。')
    json.dump(bundle, open(paths.out('map_labels.json'), 'w'),
              ensure_ascii=False, separators=(',', ':'))
    import os
    from collections import Counter
    print('ラベル', len(out), Counter(l['t'] for l in out), Counter(l['r'] for l in out))
    print('記号  ', len(pts), Counter(p['t'] for p in pts))
    print('%.0f KB' % (os.path.getsize(paths.out('map_labels.json')) / 1024))
    for l in sorted([l for l in out if l['r'] == 1], key=lambda z: z['n'])[:40]:
        print('  r1', l['t'], l['n'])


if __name__ == '__main__':
    main()
