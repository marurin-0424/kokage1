# -*- coding: utf-8 -*-
"""`cache/` の中間データが、下流のコードが期待する形と件数になっているか点検する。

★ なぜ要るか（2026-08-17 新設）
  `bridges.json` / `ground.json` / `ikebukuro_bldg_lod0.json` は、
  2026-08-17 まで**生成コードが無い状態**で置かれていた（＝再現できなかった）。
  同日に `extract_bridges.py` / `extract_ground.py` / `merge_cache.py` を新設したので、
  **作り直したものが元と同じか**を機械的に確かめられるようにする。

使い方
  python3 verify_cache.py                 # 形と件数だけ点検（数秒）
  python3 verify_cache.py --ref ../cache_old   # 旧ファイルと1件ずつ突合
"""
import paths
import sys, os, json, gzip

EXPECT = {
    'ikebukuro_bldg_lod0.json': dict(n=21381, note='建物（LOD0フットプリント＋高さ）'),
    'ground.json':              dict(n=51910, note='地盤高の点群'),
    'bridges.json':             dict(n=21,    note='橋（brid:Bridge）'),
}


def check_bldg(a):
    assert isinstance(a, list), 'list ではありません'
    b = a[0]
    for k in ('id', 'h', 'r'):
        assert k in b, 'キー %s がありません' % k
    assert isinstance(b['r'][0], list) and len(b['r'][0]) == 2, 'r は [lon, lat] の列であるべき'
    assert 100 < b['r'][0][0] < 180, 'r[0] が経度に見えません（緯度と入れ替わっていませんか）'
    bad = [x for x in a if len(x['r']) < 4]
    return '建物 %d棟／LOD2あり %d棟／リング4点未満 %d棟（shadow.load_buildings が捨てる）' % (
        len(a), sum(x.get('lod2', 0) for x in a), len(bad))


def check_ground(a):
    assert isinstance(a, list) and len(a[0]) == 3, '[lon, lat, z] の列であるべき'
    assert 100 < a[0][0] < 180, '経度と緯度が入れ替わっていませんか'
    zs = [p[2] for p in a]
    return '%d点／z %.2f〜%.2f m' % (len(a), min(zs), max(zs))


def check_bridges(a):
    assert isinstance(a, list) and 'r' in a[0], 'r キーがありません'
    ring = a[0]['r'][0]
    assert len(ring[0]) == 3, 'リングの頂点は [lon, lat, z] であるべき'
    assert 100 < ring[0][0] < 180, '経度と緯度が入れ替わっていませんか'
    nf = sum(len(x['r']) for x in a)
    return '橋 %d件／面 %d枚（うち load_decks がデッキと判定するのは 2026-08-17 時点で679枚）' % (len(a), nf)


CHECK = {'ikebukuro_bldg_lod0.json': check_bldg,
         'ground.json': check_ground,
         'bridges.json': check_bridges}


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    ng = 0
    for name, e in EXPECT.items():
        p = paths.cache(name)
        if not os.path.exists(p):
            print('✗ %-30s 無い' % name); ng += 1; continue
        a = json.load(open(p))
        try:
            msg = CHECK[name](a)
        except AssertionError as ex:
            print('✗ %-30s 形が違う: %s' % (name, ex)); ng += 1; continue
        mark = '○' if len(a) == e['n'] else '△'
        if len(a) != e['n']:
            ng += 1
        print('%s %-30s %s  ［期待 %d件］%s' % (mark, name, msg, e['n'], e['note']))
        if ref:
            q = os.path.join(ref, name)
            if os.path.exists(q):
                same = json.load(open(q)) == a
                print('    旧ファイルとの完全一致: %s' % ('○' if same else '✗ 差分あり'))
    # lod2 は gz なので別扱い
    p = paths.cache('lod2_faces.json.gz')
    if os.path.exists(p):
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            d = json.load(f)
        print('○ %-30s 建物 %d棟 / 面 %d枚  ［期待 128,012枚］'
              % ('lod2_faces.json.gz', len(d), sum(len(v) for v in d.values())))
    print('\n%s' % ('すべて期待どおりです。' if ng == 0 else '★ %d件が期待と違います。上の印を確認してください。' % ng))


if __name__ == '__main__':
    main()
