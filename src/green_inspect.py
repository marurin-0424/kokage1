# -*- coding: utf-8 -*-
"""東京都「緑のオープンデータ（GISデータ）」の中身を点検する（2026-08-17 新設）

★ なぜ作ったか
  B13（公園の樹木データを探し切る）で、東京都都市整備局が 2026-01-30 に
  「緑のオープンデータ」を公開していたことが判明した。
  data-sources.md §1d-3「樹木のデータは、やはりありません」を覆すかどうかを、
  要約ではなく実データで確かめる必要があった。

  結論（2026-08-17）：
    ・公園ポリゴン（公園名つき）は入っていた → roadmap.md §5 #9・#★10 の書き換えが要る
    ・街路樹は tokyo_gairoju.csv と完全に同一（144,183件・豊島区4,687件）
    ・樹林地は「公園緑地等の開園区域と重なるものは対象外」＝ 公園の中の木は入っていない

使い方:
  pip install --break-system-packages pyshp pyproj
  python3 green_inspect.py <展開したフォルダ>   # 既定は data/tokyo-toshiseibi/ 配下の展開先
"""
import glob
import os
import sys

import shapefile
from pyproj import Transformer

# 池袋周辺（歩行空間ネットワークの収録範囲におおむね対応）
IKEBUKURO_LONLAT = (139.6980, 35.7180, 139.7280, 35.7420)

# 緑のオープンデータは JGD2011 平面直角座標系 第9系＝EPSG:6677。
# ★ こかげが内部で使っている座標系と同じなので、再投影は要らない。
_T = Transformer.from_crs('EPSG:6668', 'EPSG:6677', always_xy=True)


def ikebukuro_bbox():
    x0, y0 = _T.transform(IKEBUKURO_LONLAT[0], IKEBUKURO_LONLAT[1])
    x1, y1 = _T.transform(IKEBUKURO_LONLAT[2], IKEBUKURO_LONLAT[3])
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _hit(shape, box):
    xmin, ymin, xmax, ymax = box
    if shape.shapeType in (1, 11):                     # POINT / POINTZ
        x, y = shape.points[0]
        return xmin <= x <= xmax and ymin <= y <= ymax
    b = shape.bbox                                     # [xmin, ymin, xmax, ymax]
    return not (b[2] < xmin or b[0] > xmax or b[3] < ymin or b[1] > ymax)


def _decode_name(name):
    """unzip が #Uxxxx 形式に落とした日本語ファイル名を戻す"""
    try:
        return name.encode().decode('unicode_escape')
    except Exception:
        return name


SHAPE_TYPE = {1: 'ポイント', 3: 'ライン', 5: 'ポリゴン',
              11: 'ポイントZ', 13: 'ラインZ', 15: 'ポリゴンZ'}


def inspect(root, ward='豊島'):
    box = ikebukuro_bbox()
    print('池袋bbox(EPSG:6677) x %.0f..%.0f / y %.0f..%.0f\n' % (box[0], box[2], box[1], box[3]))
    for shp in sorted(glob.glob(os.path.join(root, '**', '*.shp'), recursive=True)):
        try:
            r = shapefile.Reader(shp, encoding='cp932')
        except Exception as e:
            print('ERR', shp, e)
            continue
        fields = [f[0] for f in r.fields[1:]]
        name = _decode_name(os.path.basename(shp))
        print('■ %s | %s | 全%d件' % (name, SHAPE_TYPE.get(r.shapeType, r.shapeType), len(r)))
        print('   属性: %s' % fields)
        if '区市町村' not in fields:
            continue
        i = fields.index('区市町村')
        recs, shapes = r.records(), r.shapes()
        target = [k for k, rec in enumerate(recs) if ward in str(rec[i])]
        inbox = [k for k in target if _hit(shapes[k], box)]
        print('   %s区 %d件 / 池袋bbox内 %d件' % (ward, len(target), len(inbox)))
        if inbox:
            print('   例: %s' % dict(zip(fields, recs[inbox[0]])))


if __name__ == '__main__':
    inspect(sys.argv[1] if len(sys.argv) > 1 else '.')
