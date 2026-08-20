# -*- coding: utf-8 -*-
"""CityGML の `udx/brid`（橋梁）から、面の頂点列を抜いて `cache/bridges.json` を作る。

★ なぜ要るか（2026-08-17 新設）
  `bridge.py` は `cache/bridges.json` を読むだけで、**それを作るコードが src/ に無かった**。
  ＝ `how-it-works.md` §2② の「高架のデッキ679面」が再現できない状態だった。
  データ活用賞は「オープンデータをどう加工したか」を見るので、ここが空白なのは致命的。

出力フォーマット（`bridge.load_decks()` が読む形。既存ファイルと同じ）
  [ {"mesh": "53394577", "f": "99",
     "r": [ [[lon, lat, z], [lon, lat, z], ...], ... ] }, ... ]
  ・`r` は面（ポリゴンの外周リング）のリスト。既存ファイルは全13,335面が三角形（4点・閉じ）
  ・座標は EPSG:6697（緯度 経度 標高 の順で入っているので、読むときに入れ替える）
  ・`f` は `brid:function`（既存は 99／01／07 の3種）

［注］この段階では「どれがデッキか」を選びません。水平（高低差≦1.5m）・面積≧20㎡・
      地盤から3m以上、という選別は `bridge.load_decks()` 側の仕事です（既存の設計を変えない）。

使い方
  python3 extract_bridges.py            # 全メッシュ → cache/bridges.json
  python3 extract_bridges.py 53394577   # 1メッシュだけ確認したいとき（標準出力に件数）

★ 未実行（2026-08-17）：このスクリプトは 1.18GB の CityGML zip が要るため、
  クラウド側では実行できていません。**丸山さんの環境で回して、既存の
  `cache/bridges.json` と一致することを確かめてください**（`verify_cache.py`）。
"""
import paths
import sys, re, json, zipfile, time

Z = paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')

# 池袋駅周辺の2次メッシュ8枚（`ikebukuro_bldg_lod0.json` と同じ範囲）
# ［注］既存の bridges.json に現れるのは 53394566 / 76 / 77 / 87 の4枚だけですが、
#       「他のメッシュに橋が無い」ことを毎回確認する意味で全8枚を走査します。
MESHES = ['53394566', '53394567', '53394576', '53394577',
          '53394578', '53394586', '53394587', '53394588']

re_obj = re.compile(r'<brid:Bridge\b.*?</brid:Bridge>', re.S)
re_fn = re.compile(r'<brid:function[^>]*>([^<]*)</brid:function>')
re_pos = re.compile(r'<gml:posList>([^<]+)</gml:posList>')


def run(mesh):
    """1メッシュぶん。戻り値は bridges.json の要素のリスト"""
    z = zipfile.ZipFile(Z)
    name = 'udx/brid/%s_brid_6697_op.gml' % mesh
    try:
        data = z.read(name).decode('utf-8', 'replace')
    except KeyError:
        return []                     # そのメッシュに brid ファイルが無い＝橋が無い
    out = []
    for m in re_obj.finditer(data):
        blk = m.group(0)
        fn = re_fn.search(blk)
        rings = []
        for pl in re_pos.finditer(blk):
            v = pl.group(1).split()
            if len(v) < 12:           # 3点未満の面は捨てる（12 = 4点 × 3成分）
                continue
            # EPSG:6697 は「緯度 経度 標高」の順。(lon, lat, z) に並べ替える
            rings.append([[float(v[k + 1]), float(v[k]), float(v[k + 2])]
                          for k in range(0, len(v), 3)])
        if rings:
            out.append({'mesh': mesh,
                        'f': fn.group(1) if fn else None,
                        'r': rings})
    return out


if __name__ == '__main__':
    t = time.time()
    meshes = sys.argv[1:] or MESHES
    allout = []
    for mesh in meshes:
        r = run(mesh)
        allout += r
        print('%s → 橋 %d件 / 面 %d枚' % (mesh, len(r), sum(len(x['r']) for x in r)))
    if not sys.argv[1:]:
        json.dump(allout, open(paths.cache('bridges.json'), 'w'))
        print('→ cache/bridges.json  橋 %d件 / 面 %d枚  %.1fs'
              % (len(allout), sum(len(x['r']) for x in allout), time.time() - t))
        print('［期待値 2026-08-17 時点］橋 21件 / 面 13,335枚')
