# -*- coding: utf-8 -*-
"""ファイルの置き場を1箇所で解決する（2026-08-13 新設）

★ なぜ要るか
  2026-08-13 のフォルダ分けまで、全スクリプトが '/home/claude/kokage/' を直書きしていた。
  フォルダを分けた時点で how-it-works.md §6 の「再現の手順」が動かなくなっていたが、
  それに気づいていなかった。CLAUDE.md の作業ルール「絶対パスを書かない」にも反していた。

使い方
  from paths import cache, out, build, raw
  load_buildings(cache('ikebukuro_bldg_lod0.json'))
  json.dump(x, open(out('trace.json'), 'w'))
"""
import os

SRC     = os.path.dirname(os.path.abspath(__file__))   # data/tokyo-3d-map/derived/src
DERIVED = os.path.dirname(SRC)                         # data/tokyo-3d-map/derived
CACHE   = os.path.join(DERIVED, 'cache')               # 再生成が重い中間データ
OUT     = os.path.join(DERIVED, 'out')                 # 結果（軽い）
FIG     = os.path.join(DERIVED, 'fig')                 # スライド用PNG
TOKYO3D = os.path.dirname(DERIVED)                     # data/tokyo-3d-map
DATA    = os.path.dirname(TOKYO3D)                     # kokage/data
KOKAGE  = os.path.dirname(DATA)                        # kokage
BUILD   = os.path.join(KOKAGE, 'build')                # ブラウザで開くもの
PAGES   = os.path.join(KOKAGE, 'pages')                # GitHub Pages 用の一式

HOKOU    = os.path.join(DATA, 'hokou-network')
KENSETSU = os.path.join(DATA, 'tokyo-kensetsu')
FUKUSHI  = os.path.join(DATA, 'tokyo-fukushi')
TOSHIMA  = os.path.join(DATA, 'toshima-ku')
ENVWBGT  = os.path.join(DATA, 'env-wbgt')

# 取得済みの生データ（データ元ごとのフォルダに置く。data-sources.md §0）
_RAW = {
    'ikebukuro_link.geojson':                       HOKOU,
    'ikebukuro_node.geojson':                       HOKOU,
    'tokyo_gairoju.csv':                            KENSETSU,
    'r5_public_facility.csv':                       TOSHIMA,
    'r5_preschool.csv':                             TOSHIMA,
    'akachanflat_ichiran_R80617.csv':               FUKUSHI,
    '13116_toshima-ku_2025_related.zip':            TOKYO3D,
    '13116_toshima-ku_pref_2025_citygml_1_op.zip':  TOKYO3D,
}


def cache(name):
    return os.path.join(CACHE, name)


def out(name):
    return os.path.join(OUT, name)


def build(name):
    return os.path.join(BUILD, name)


def pages(name):
    return os.path.join(PAGES, name)


def fig(name):
    return os.path.join(FIG, name)


def raw(name):
    if name not in _RAW:
        raise KeyError('paths.raw: 置き場が未登録です → %s（paths.py の _RAW に追加してください）' % name)
    return os.path.join(_RAW[name], name)
