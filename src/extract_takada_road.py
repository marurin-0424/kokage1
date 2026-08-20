# -*- coding: utf-8 -*-
"""高田・雑司ヶ谷方面の「道路面」ポリゴンを CityGML から抜き出す（2026-08-14 新設）

★ なぜ要るか
  現地確認で「公園まわりの道路の日陰」を区間ごとに答え合わせしたかったが、
  既存の sidewalk_poly.json は歩行空間NWの収録範囲（池袋駅周辺）だけで、
  高田（lat 35.714 付近）を含んでいなかった。
  こちらは tran:Road の lod1MultiSurface＝道路の面そのもの（歩道部に限らない）。

出力：cache/takada_road_poly.json（1,562レコード・1,576面・557KB）
"""
import paths
import re, json, zipfile

ZP = paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')
MESHES = ['53394556', '53394557', '53394566', '53394567']
LON0, LON1 = 139.7120, 139.7240
LAT0, LAT1 = 35.7095, 35.7205

re_road = re.compile(r'<tran:Road\b.*?</tran:Road>', re.S)
re_id   = re.compile(r'gml:id="([^"]+)"')
re_cls  = re.compile(r'<tran:class[^>]*>([^<]*)</tran:class>')
re_fn   = re.compile(r'<tran:function[^>]*>([^<]*)</tran:function>')
re_pos  = re.compile(r'<gml:posList>(.*?)</gml:posList>', re.S)


def run():
    z = zipfile.ZipFile(ZP)
    out = []
    for mesh in MESHES:
        try:
            d = z.read('udx/tran/%s_tran_6697_op.gml' % mesh).decode('utf-8')
        except KeyError:
            continue
        n = 0
        for m in re_road.finditer(d):
            blk = m.group(0)
            rings = []
            for p in re_pos.finditer(blk):
                v = p.group(1).split()
                # CityGML は 緯度 経度 標高 の順
                rings.append([[round(float(v[i+1]), 7), round(float(v[i]), 7)]
                              for i in range(0, len(v), 3)])
            keep = [r for r in rings
                    if any(LON0 <= x <= LON1 and LAT0 <= y <= LAT1 for x, y in r)]
            if not keep:
                continue
            n += 1
            out.append({'id': re_id.search(blk).group(1), 'mesh': mesh,
                        'c': (re_cls.search(blk).group(1) if re_cls.search(blk) else None),
                        'f': (re_fn.search(blk).group(1) if re_fn.search(blk) else None),
                        'rings': keep})
        print(mesh, 'kept', n, flush=True)
    json.dump(out, open(paths.cache('takada_road_poly.json'), 'w'))
    print('total', len(out))


if __name__ == '__main__':
    run()
