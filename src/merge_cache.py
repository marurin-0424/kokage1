# -*- coding: utf-8 -*-
"""メッシュ単位の抽出結果を1本にまとめる（2026-08-17 新設）

★ なぜ要るか
  `extract_footprints.py` は `cache/b_{mesh}.json` までしか作らず、
  **`cache/ikebukuro_bldg_lod0.json` に統合するコードが src/ に無かった**。
  `extract_ground.py`（同日新設）も同じ構造なので、統合をここに1本化する。

使い方
  python3 merge_cache.py bldg      # b_*.json    → cache/ikebukuro_bldg_lod0.json
  python3 merge_cache.py ground    # g_*.json    → cache/ground.json
  python3 merge_cache.py lod2      # lod2_*.json → cache/lod2_faces.json(.gz)

［注］重複の扱い
  隣り合うメッシュの境界にまたがる建物は、CityGML では**片方のメッシュにだけ**入ります
  （gml:id が一意）。念のため bldg は id で重複排除します。ground は点群なので排除しません。
"""
import paths
import sys, os, json, gzip, glob

MESHES = ['53394566', '53394567', '53394576', '53394577',
          '53394578', '53394586', '53394587', '53394588']

EXPECT = {'bldg': 21381, 'ground': 51910, 'lod2': 128012}   # 2026-08-17 時点の実測値


def merge_bldg():
    seen, out = set(), []
    for m in MESHES:
        p = paths.cache('b_%s.json' % m)
        if not os.path.exists(p):
            print('  ! 無い: b_%s.json（extract_footprints.py %s を先に）' % (m, m))
            continue
        for b in json.load(open(p)):
            if b['id'] in seen:
                continue
            seen.add(b['id'])
            out.append(b)
    json.dump(out, open(paths.cache('ikebukuro_bldg_lod0.json'), 'w'))
    print('ikebukuro_bldg_lod0.json → 建物 %d棟（うち LOD2 あり %d棟）／期待値 %d'
          % (len(out), sum(x['lod2'] for x in out), EXPECT['bldg']))


def merge_ground():
    out = []
    for m in MESHES:
        p = paths.cache('g_%s.json' % m)
        if not os.path.exists(p):
            print('  ! 無い: g_%s.json（extract_ground.py %s を先に）' % (m, m))
            continue
        out += json.load(open(p))
    json.dump(out, open(paths.cache('ground.json'), 'w'))
    zs = [p[2] for p in out]
    print('ground.json → %d点／期待値 %d、z %.2f〜%.2f'
          % (len(out), EXPECT['ground'], min(zs), max(zs)))


def merge_lod2():
    out = {}
    for p in sorted(glob.glob(paths.cache('lod2_*.json'))):
        if p.endswith('lod2_faces.json'):
            continue
        out.update(json.load(open(p)))
    nf = sum(len(v) for v in out.values())
    with gzip.open(paths.cache('lod2_faces.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(out, f)
    print('lod2_faces.json.gz → 建物 %d棟 / 面 %d枚／期待値 %d'
          % (len(out), nf, EXPECT['lod2']))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else ''
    {'bldg': merge_bldg, 'ground': merge_ground, 'lod2': merge_lod2}.get(
        what, lambda: print(__doc__))()
