# -*- coding: utf-8 -*-
"""CityGML から、指定した建物IDの LOD2 の面（頂点列＋標高）を抜き出す。

★ なぜ要るか：LOD1 は「底面 × measuredHeight の箱」なので、
   サンシャインシティのような低層部＋タワーの複合施設で影を過大評価する。
   ［事実］この箱の高さを 234.1m→60m にすると、こかげの1位が3ケースすべてで変わった。
標準ライブラリのみ。1メッシュずつ実行する（45秒の制限に収めるため）。
"""
import paths
import sys, re, json, zipfile, io, time

Z = paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')
TARGETS = set(json.load(open(paths.out('lod2_targets.json'))))

def run(mesh):
    t = time.time()
    z = zipfile.ZipFile(Z)
    name = 'udx/bldg/%s_bldg_6697_op.gml' % mesh
    f = z.open(name)
    out = {}
    tail = ''
    while True:
        b = f.read(1 << 22)
        if not b:
            break
        s = tail + b.decode('utf-8', 'replace')
        parts = s.split('</core:cityObjectMember>')
        tail = parts.pop()
        for p in parts:
            m = re.search(r'<bldg:Building gml:id="([^"]+)"', p)
            if not m or m.group(1) not in TARGETS:
                continue
            i = p.find('<bldg:lod2Solid')
            if i < 0:
                i = p.find('<bldg:lod2MultiSurface')
            if i < 0:
                continue
            faces = []
            for pl in re.finditer(r'<gml:posList>([^<]+)</gml:posList>', p[i:]):
                v = pl.group(1).split()
                if len(v) < 12:
                    continue
                # EPSG:6697 は 緯度 経度 標高 の順
                faces.append([[round(float(v[k+1]), 7), round(float(v[k]), 7),
                               round(float(v[k+2]), 2)] for k in range(0, len(v), 3)])
            if faces:
                out[m.group(1)] = faces
    json.dump(out, open(paths.cache('lod2_%s.json' % mesh), 'w'))
    nf = sum(len(v) for v in out.values())
    print('%s → 建物 %d棟 / 面 %d枚  %.1fs' % (mesh, len(out), nf, time.time() - t))

if __name__ == '__main__':
    run(sys.argv[1])
