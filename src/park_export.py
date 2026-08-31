# -*- coding: utf-8 -*-
"""東京都の公園ポリゴンを書き出す（2026-08-31 新設・tasks.md P38）

★ なぜ要るか
  それまでの公園の形は、豊島区の公園データ（点＋供用済面積）に、
  PLATEAU の udx/luse（土地利用 class=217「公共空地」）を座標で当てて作っていた。
  ［実測 2026-08-31］いま画面に出ている51件を都のポリゴンと重ねると、
    IoU 中央値 0.919 だが、0.7未満が10件。
    南池袋みどり公園 0.000（まったく別の場所）／雑司が谷公園 0.137（実際の1/7）
    高田公園 0.165（1/6）／池袋西口公園 0.430（隣接地を含んで倍）
  ＝ 土地利用ポリゴンは「公園」ではなく「公共空地」なので、公園の境界とは一致しない。

★ 都のデータの良いところ
  ・公園名が属性に入っている（座標で当てにいく必要がない）
  ・座標系が JGD_2011_Japan_Zone_9 ＝ EPSG:6677 で、こかげと同じ。変換が要らない
  ・「都市公園以外」に児童遊園が入っている（区の都市公園データには無い）

出力: cache/tokyo_parks.json
  [{"name":公園名, "kind":"都市公園"|"都市公園以外", "area_attr":面積m2(属性),
    "rings":[[[x,y],...], ...]}]   ※ x,y は EPSG:6677。外周のみ（穴は入れない）

依存: pyshp（pip install pyshp）
"""
import paths
import json, os, re, glob, zipfile, tempfile, shutil
import shapefile

ZIP = paths.raw('01_kouenryokuchi.zip')
# 使うのは区市町村立の2つだけ。都立・国営は池袋周辺に無い
MEMBERS = [
    '01_公園・緑地等/01_都市公園/02_区市町村立公園/区市町村立公園(都市公園)',
    '01_公園・緑地等/02_都市公園以外/01_区市町村立公園/区市町村立公園(都市公園以外)',
]
MARGIN = 400.0        # 歩行NWの外側どこまで拾うか（出発地は網から200mまで）
WARD = '豊島区'        # ★ 候補プールは豊島区の公園データ由来なので、区内は全部拾う。
#                       歩行NWの外にある候補（駒込・巣鴨・南長崎など）も名前で引けるようにする


def bbox_of_network():
    G = json.load(open(paths.out('kokage_graph.json')))
    N = G['nodes']
    return (min(N['x']) - MARGIN, min(N['y']) - MARGIN,
            max(N['x']) + MARGIN, max(N['y']) + MARGIN)


def run():
    x0, y0, x1, y1 = bbox_of_network()
    tmp = tempfile.mkdtemp(prefix='kokage_park_')
    try:
        z = zipfile.ZipFile(ZIP)
        for m in MEMBERS:
            for e in ('shp', 'shx', 'dbf', 'prj'):
                with z.open(m + '.' + e) as fi, open(os.path.join(tmp, os.path.basename(m) + '.' + e), 'wb') as fo:
                    shutil.copyfileobj(fi, fo)
        out = []
        for f in sorted(glob.glob(os.path.join(tmp, '*.shp'))):
            r = shapefile.Reader(f, encoding='cp932')
            flds = [d[0] for d in r.fields[1:]]
            n = 0
            for sr in r.iterShapeRecords():
                d = dict(zip(flds, sr.record))
                b = sr.shape.bbox
                near = not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)
                if not near and WARD not in (d.get('区市町村') or ''):
                    continue
                pts, parts = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
                rings = [[[round(p[0], 2), round(p[1], 2)] for p in pts[parts[i]:parts[i + 1]]]
                         for i in range(len(parts) - 1)]
                rings = [g for g in rings if len(g) >= 4]
                if not rings:
                    continue
                out.append({'name': d['公園名'], 'kind': d['区分'],
                            'area_attr': d['面積m2'], 'rings': rings})
                n += 1
            print('%s → %d件' % (os.path.basename(f), n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    json.dump(out, open(paths.cache('tokyo_parks.json'), 'w'), ensure_ascii=False)
    print('合計 %d件 → cache/tokyo_parks.json' % len(out))


if __name__ == '__main__':
    run()
