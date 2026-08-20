# -*- coding: utf-8 -*-
"""高田周辺の地盤高（DEM）を CityGML から抜き出す（2026-08-14 新設）

★ なぜ要るか
  2026-08-14 の現地確認で建物の影が過大に出た原因候補として「地盤の傾斜」を
  疑ったが、既存の ground.json は池袋駅周辺（lat 35.7166 以北）だけで、
  高田を含んでいなかった。→ 結果は「傾斜は無関係」（data-sources.md §1d-4）。

  udx/dem/533945_dem_6697_op.gml は展開後 701MB あるので、
  ストリームで読みながら該当範囲の頂点だけ拾う（数十秒）。

出力：cache/takada_dem.json（48,472点・1.6MB。標高 0.07〜32.66m）
"""
import paths
import re, json, zipfile, io

ZP = paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')
MEMBER = 'udx/dem/533945_dem_6697_op.gml'
LON0, LON1 = 139.7120, 139.7240
LAT0, LAT1 = 35.7095, 35.7205
CHUNK = 8 << 20      # 8MB
TAIL = 200           # 座標の三つ組が境界で切れないための重なり

# 緯度 経度 標高 の三つ組（緯度が 35.70〜35.72 のものだけ拾う）
RE = re.compile(r'35\.7[0-2][0-9]* 139\.7[0-9]* -?[0-9.]+')


def run():
    z = zipfile.ZipFile(ZP)
    seen = set()
    with z.open(MEMBER) as fh:
        r = io.TextIOWrapper(fh, encoding='utf-8')
        tail = ''
        while True:
            buf = r.read(CHUNK)
            if not buf:
                break
            s = tail + buf
            for m in RE.finditer(s):
                a = m.group(0).split()
                la, lo, zz = float(a[0]), float(a[1]), float(a[2])
                if LAT0 <= la <= LAT1 and LON0 <= lo <= LON1:
                    seen.add((round(lo, 7), round(la, 7), round(zz, 2)))
            tail = s[-TAIL:]
    pts = [list(t) for t in seen]
    json.dump(pts, open(paths.cache('takada_dem.json'), 'w'))
    print(len(pts), 'points', 'z',
          min(p[2] for p in pts), max(p[2] for p in pts))


if __name__ == '__main__':
    run()
