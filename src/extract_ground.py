# -*- coding: utf-8 -*-
"""CityGML の建物から地盤高の点群 `cache/ground.json` を作る。

★ なぜ要るか（2026-08-17 新設）
  `bridge.ground_lookup()` は `cache/ground.json` を読むだけで、**それを作るコードが
  src/ に無かった**。高架のデッキ影は「デッキ標高 − その場所の地盤高」で決まるので、
  この点群が無いと `how-it-works.md` §2② が再現できない。

考え方
  PLATEAU に「地面の標高」レイヤはありません。そこで **建物の `bldg:lod1Solid` の
  頂点標高の最小値**を、その場所の地盤高とみなします（＝箱の底面の高さ）。
  建物は市街地にほぼ均等に分布するので、これで十分な密度の点群になります。
  ［推測］この近似の弱点は、建物が無い場所（大きな公園・河川敷・線路上）で
  最近傍が遠くなること。池袋駅周辺では実害が小さいと判断しています。

出力フォーマット（`bridge.ground_lookup()` が読む形。既存ファイルと同じ）
  [ [lon, lat, z], ... ]   lon/lat は小数6桁、z は小数2桁

使い方
  python3 extract_ground.py 53394577    # → cache/g_53394577.json
  （8メッシュぶん回してから）
  python3 merge_cache.py ground         # → cache/ground.json

★ 未実行（2026-08-17）：1.18GB の CityGML zip が要るため、クラウド側では
  実行できていません。**丸山さんの環境で回して `verify_cache.py` で突合してください。**
  ［期待値 2026-08-17 時点］8メッシュ合計 51,910点・z は 9.57〜36.26 m
"""
import paths
import sys, re, json, zipfile, time

Z = paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')

MESHES = ['53394566', '53394567', '53394576', '53394577',
          '53394578', '53394586', '53394587', '53394588']

re_pos = re.compile(r'<gml:posList>([^<]+)</gml:posList>')
re_lod1 = re.compile(r'<bldg:lod1Solid>(.*?)</bldg:lod1Solid>', re.S)


def run(mesh):
    """1メッシュぶん。建物1棟につき1点（代表点の lon/lat と、底面の標高）"""
    z = zipfile.ZipFile(Z)
    f = z.open('udx/bldg/%s_bldg_6697_op.gml' % mesh)
    out = []
    tail = ''
    # ★ 建物は1メッシュで数万棟ある。全部メモリに載せず、cityObjectMember 単位で流す
    #   （extract_lod2.py と同じ読み方）
    while True:
        b = f.read(1 << 22)
        if not b:
            break
        s = tail + b.decode('utf-8', 'replace')
        parts = s.split('</core:cityObjectMember>')
        tail = parts.pop()
        for p in parts:
            m = re_lod1.search(p)
            if not m:
                continue
            lons = []
            lats = []
            zs = []
            for pl in re_pos.finditer(m.group(1)):
                v = pl.group(1).split()
                for k in range(0, len(v), 3):
                    # EPSG:6697 は「緯度 経度 標高」の順
                    lats.append(float(v[k]))
                    lons.append(float(v[k + 1]))
                    zs.append(float(v[k + 2]))
            if not zs:
                continue
            out.append([round(sum(lons) / len(lons), 6),
                        round(sum(lats) / len(lats), 6),
                        round(min(zs), 2)])
    return out


if __name__ == '__main__':
    t = time.time()
    for mesh in (sys.argv[1:] or MESHES):
        r = run(mesh)
        json.dump(r, open(paths.cache('g_%s.json' % mesh), 'w'))
        print('%s → %d点  %.1fs' % (mesh, len(r), time.time() - t))
