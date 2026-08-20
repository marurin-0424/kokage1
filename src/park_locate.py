# -*- coding: utf-8 -*-
"""現地確認シート（第2版）：公園の「場所」を確かめる。

★ 2026-08-12 夜に目的を変更。
   第1版は「時刻ごとの日陰率が合っているか」を見るシートだったが、
   ①雨が続く見込みで日陰が観察できない
   ②公園の座標が【東京都と豊島区で最大164mずれている】ことが判明した
   ため、天候・時刻に依存しない「場所の確認」に振り切った。

★ 2026-08-12 夜③：現地で位置を特定できるよう、地図に目印を3種類足した。
   ① 都営バスの停留所名（ToeiBus-GTFS・538件）
   ② 豊島区の公共施設名（公共施設一覧・558件）
   ③ 通称道路名（都道の街路樹CSVの「通称道路名」から）

出力：park-check.html（build_locate.py 経由）
"""
import paths
import sys, json, math, zipfile, io as _io, csv, collections
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union, transform
from shadow import FWD, load_buildings
import destination as D

W = H = 640
SPAN = 400.0            # 1枚の地図が覆う実距離（m）。目印を入れるために260→400に拡大
PAL = dict(bldg='#f1f0ed', bldg_e='#dcdbd4', park='#1baf7a', ink='#0b0b0b',
           muted='#898781', pref='#2a78d6', ward='#eb6834', road='#ecebe6',
           lot='#f8f8f6', lot_e='#e6e5df', surf='#fcfcfb',
           bus='#4a3aa7', fac='#52514e', rdlab='#7c7a74', lmk='#a05a1e', stn='#0b0b0b')

# 目印にする施設（名前に含まれれば採用）。前にあるものほど優先して描く
FAC_KEY = ['小学校', '中学校', '高等学校', '幼稚園', '保育園', '区民ひろば', '図書館',
           '児童館', 'センター', '出張所', '区民集会室', '地域文化創造館', '会館', '公社']

TARGETS = [
    dict(key='yamabuki', name='山吹の里公園', area='A 高田', pri=1,
         addr='豊島区高田1-10-5', why='都と区で75mずれている。ポリゴン(578㎡)は都の座標の6m先'),
    dict(key='takada1', name='高田一丁目児童遊園', area='A 高田', pri=1,
         addr='豊島区高田1-23-33', why='都のデータに存在しない。最寄りのポリゴン(447㎡)は58m先'),
    dict(key='mimizuku', name='雑司が谷みみずく公園', area='A 高田', pri=2,
         addr='豊島区雑司が谷3-15-20', why='都と区で42mずれ。公共空地のポリゴンが当たらない'),
    dict(key='ekimae', name='池袋駅前公園', area='B 池袋駅', pri=1,
         addr='豊島区東池袋1-50-23', why='都と区で151mずれ。公共空地のポリゴンが当たらない'),
    dict(key='nishiike', name='西池袋公園', area='B 池袋駅', pri=1,
         addr='豊島区西池袋3-20-1', why='★ズレ最大164m。公開8,691㎡に対しポリゴンは2,889㎡'),
    dict(key='nishiguchi', name='池袋西口公園', area='B 池袋駅', pri=2,
         addr='豊島区西池袋1-8-26', why='ポリゴンが6,005㎡で公開3,123㎡の約2倍。芸術劇場の広場と一体か'),
    dict(key='higashichuo', name='東池袋中央公園', area='B 池袋駅', pri=2,
         addr='豊島区東池袋3-1-6', why='40m以内にポリゴンが無い。120mまで広げると5,883㎡が58m先（公開5,994㎡とほぼ一致）'),
    dict(key='kamisakura', name='上池袋さくら公園', area='C 遠い', pri=3,
         addr='豊島区上池袋2-45-15', why='ズレ93m。公開4,992㎡に対しポリゴンは1,418㎡'),
    dict(key='hanasaki', name='南長崎花咲公園', area='C 遠い', pri=3,
         addr='豊島区南長崎3-9-22', why='ズレ52m。公開2,197㎡に対しポリゴンは685㎡'),
    dict(key='komagome', name='駒込西公園', area='C 遠い', pri=3,
         addr='豊島区駒込5-4-33', why='座標は一致（2m）。公共空地のポリゴンが当たらない'),
]


# ---------------------------------------------------------------- データ読み込み
def load_coords():
    z = zipfile.ZipFile(D.DATA + '13116_toshima-ku_2025_related.zip')
    gj = json.load(_io.TextIOWrapper(z.open('13116_toshima-ku_pref_2023_park.geojson'),
                                     encoding='utf-8'))
    pref = {f['properties']['公園名'] + '公園':
            (f['geometry']['coordinates'][0], f['geometry']['coordinates'][1],
             f['properties']['供用済面積'], f['properties']['公園種別'])
            for f in gj['features']}
    raw = open(D.DATA + 'r5_public_facility.csv', 'rb').read().decode('cp932')
    rr = csv.reader(_io.StringIO(raw)); next(rr)
    ward, fac = {}, []
    for x in rr:
        try:
            lo, la = float(x[11]), float(x[10])
        except Exception:
            continue
        ward[x[4]] = (lo, la)
        fac.append((x[4], lo, la))
    return pref, ward, fac


def load_bus():
    return [(n, lo, la) for n, lo, la in json.load(open(paths.out('bus_stops.json')))]


def load_landmarks():
    """PLATEAU 関連データセットのランドマーク143件と駅35件"""
    z = zipfile.ZipFile(D.DATA + '13116_toshima-ku_2025_related.zip')
    lm = json.load(_io.TextIOWrapper(z.open('13116_toshima-ku_pref_2025_landmark.geojson'),
                                     encoding='utf-8'))
    L = [(f['properties'].get('名称', ''), f['properties'].get('種類', ''),
          f['geometry']['coordinates'][0], f['geometry']['coordinates'][1])
         for f in lm['features'] if f['geometry']['type'] == 'Point']
    st = json.load(_io.TextIOWrapper(z.open('13116_toshima-ku_pref_2025_station.geojson'),
                                     encoding='utf-8'))
    S, seen = [], set()
    for f in st['features']:
        nm = f['properties'].get('駅名', '')
        c = f['geometry']['coordinates'][:2]
        k = (nm, round(c[0], 4), round(c[1], 4))
        if nm and k not in seen:
            seen.add(k); S.append((nm, c[0], c[1]))
    return L, S


def load_roads():
    """通称道路名 → 座標の点群（都道の街路樹CSVから）"""
    d = collections.defaultdict(list)
    with _io.open(paths.raw('tokyo_gairoju.csv'), encoding='cp932', errors='replace') as f:
        for x in csv.DictReader(f):
            nm = (x.get('通称道路名') or '').strip() or (x.get('路線名') or '').strip()
            if not nm:
                continue
            try:
                lo, la = float(x['経度']), float(x['緯度'])
            except Exception:
                continue
            if 139.66 <= lo <= 139.77 and 35.68 <= la <= 35.77:
                d[nm].append(FWD.transform(lo, la))
    return d


def load_luse():
    op = []
    for x in json.load(open(paths.cache('luse_open_space.json'))):
        try:
            p = Polygon(x['ring'], x['holes'])
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                op.append(p)
        except Exception:
            pass
    ctx = []
    for x in json.load(open(paths.cache('luse_park_context.json'))):
        try:
            p = Polygon(x['r'])
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                ctx.append((p, x['c']))
        except Exception:
            pass
    return op, ctx


def to_m(g):
    return transform(lambda x, y, z=None: FWD.transform(x, y), g)


def match(op, lo, la, r=120.0):
    pt = Point(lo, la); d = r / 111000.0
    near = [p for p in op if p.distance(pt) < d]
    if not near:
        return None, None
    core = [p for p in near if p.contains(pt)]
    if core:
        p = max(core, key=lambda q: q.area); dist = 0.0
    else:
        p = min(near, key=lambda q: q.distance(pt)); dist = p.distance(pt) * 111000
    return to_m(p), dist


# ---------------------------------------------------------------- 描画
class Map:
    """ラベルの重なりを避けながら描く。先に呼んだものが優先。"""

    def __init__(self, cx, cy, span=SPAN):
        self.cx, self.cy, self.k = cx, cy, W / span
        self.box = box(cx - span / 2, cy - span * H / W / 2,
                       cx + span / 2, cy + span * H / W / 2)
        self.parts, self.taken = [], []

    def px(self, x, y):
        return ((x - self.cx) * self.k + W / 2, H / 2 - (y - self.cy) * self.k)

    def inside(self, x, y, m=6):
        X, Y = self.px(x, y)
        return -m <= X <= W + m and -m <= Y <= H + m

    def _free(self, r, pad=2):
        x0, y0, x1, y1 = r
        for a, b, c, d in self.taken:
            if x0 - pad < c and a - pad < x1 and y0 - pad < d and b - pad < y1:
                return False
        return True

    def _take(self, r):
        self.taken.append(r)

    def poly(self, g, **a):
        if g is None or g.is_empty or not g.intersects(self.box):
            return
        g = g.intersection(self.box)
        gs = list(g.geoms) if hasattr(g, 'geoms') else [g]
        d = []
        for p in gs:
            if p.is_empty or p.geom_type != 'Polygon':
                continue
            for ring in [p.exterior] + list(p.interiors):
                c = list(ring.coords)
                if len(c) < 3:
                    continue
                d.append('M' + ' L'.join('%.0f,%.0f' % self.px(x, y) for x, y in c) + 'Z')
        if d:
            at = ' '.join('%s="%s"' % (k.replace('_', '-'), v) for k, v in a.items())
            self.parts.append('<path d="%s" %s fill-rule="evenodd"/>' % (''.join(d), at))

    def label(self, X, Y, text, size, fill, anchor='start', weight='400', halo=4.5,
              reserve=True, dy=0):
        w = len(text) * size * 0.62 + 4
        x0 = X if anchor == 'start' else (X - w if anchor == 'end' else X - w / 2)
        r = (x0, Y + dy - size, x0 + w, Y + dy + size * 0.4)
        if x0 < 2 or x0 + w > W - 2 or Y + dy < size or Y + dy > H - 6:
            return False                      # 画面外にはみ出すラベルは置かない
        if reserve and not self._free(r):
            return False
        if reserve:
            self._take(r)
        self.parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" font-weight="%s" '
            'fill="%s" paint-order="stroke" stroke="#fff" stroke-width="%.1f">%s</text>'
            % (X, Y + dy, anchor, size, weight, fill, halo, esc(text)))
        return True

    def park_mark(self, x, y, color, lab, anchor='start'):
        X, Y = self.px(x, y)
        self._take((X - 11, Y - 11, X + 11, Y + 11))
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="9" fill="%s" stroke="#fff" '
                          'stroke-width="3"/>' % (X, Y, color))
        dx = 14 if anchor == 'start' else -14
        self.label(X + dx, Y + 5, lab, 14, color, anchor, '700', 5, True)

    def bus(self, x, y, name):
        if not self.inside(x, y):
            return
        X, Y = self.px(x, y)
        if not self._free((X - 5, Y - 5, X + 5, Y + 5)):
            return
        self._take((X - 5, Y - 5, X + 5, Y + 5))
        self.parts.append('<rect x="%.1f" y="%.1f" width="9" height="9" rx="2" fill="%s" '
                          'stroke="#fff" stroke-width="1.8"/>' % (X - 4.5, Y - 4.5, PAL['bus']))
        for anc, dx in (('start', 8), ('end', -8)):
            if self.label(X + dx, Y + 4, name, 11.5, PAL['bus'], anc, '700', 4):
                return

    def fac(self, x, y, name):
        if not self.inside(x, y):
            return
        X, Y = self.px(x, y)
        if not self._free((X - 4, Y - 4, X + 4, Y + 4)):
            return
        self._take((X - 4, Y - 4, X + 4, Y + 4))
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="%s"/>' % (X, Y, PAL['fac']))
        for anc, dx in (('start', 6), ('end', -6)):
            if self.label(X + dx, Y + 4, name, 11, PAL['fac'], anc, '400', 4):
                return

    def landmark(self, x, y, name, kind):
        if not self.inside(x, y):
            return
        X, Y = self.px(x, y)
        if not self._free((X - 5, Y - 5, X + 5, Y + 5)):
            return
        self._take((X - 5, Y - 5, X + 5, Y + 5))
        self.parts.append('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="%s" '
                          'stroke="#fff" stroke-width="1.6"/>'
                          % (X, Y - 5.5, X + 5.5, Y, X, Y + 5.5, X - 5.5, Y, PAL['lmk']))
        for anc, dx in (('start', 8), ('end', -8)):
            if self.label(X + dx, Y + 4, name, 11, PAL['lmk'], anc, '400', 4):
                return

    def station(self, x, y, name):
        if not self.inside(x, y):
            return
        X, Y = self.px(x, y)
        self._take((X - 7, Y - 7, X + 7, Y + 7))
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="6.5" fill="#fff" stroke="%s" '
                          'stroke-width="3"/>' % (X, Y, PAL['stn']))
        for anc, dx in (('start', 10), ('end', -10)):
            if self.label(X + dx, Y + 5, name, 13, PAL['stn'], anc, '700', 5):
                return

    def road(self, pts, name):
        """道路名を、点群の主軸に沿って回転して置く"""
        ins = [p for p in pts if self.inside(*p, m=-30)]
        if len(ins) < 3:
            return
        n = len(ins)
        mx = sum(p[0] for p in ins) / n; my = sum(p[1] for p in ins) / n
        sxx = sum((p[0] - mx) ** 2 for p in ins); syy = sum((p[1] - my) ** 2 for p in ins)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in ins)
        ang = 0.5 * math.atan2(2 * sxy, sxx - syy)          # 主軸（平面直角座標・北基準）
        deg = -math.degrees(ang)                             # SVGは下向き正
        if deg > 90:
            deg -= 180
        if deg < -90:
            deg += 180
        X, Y = self.px(mx, my)
        w = len(name) * 13 * 0.62
        if not self._free((X - w / 2, Y - 10, X + w / 2, Y + 6)):
            return
        self._take((X - w / 2, Y - 10, X + w / 2, Y + 6))
        self.parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" font-weight="700" '
            'fill="%s" paint-order="stroke" stroke="#fff" stroke-width="5.5" '
            'transform="rotate(%.1f %.1f %.1f)">%s</text>'
            % (X, Y, PAL['rdlab'], deg, X, Y, esc(name)))

    def furniture(self, span=SPAN):
        m = 50; L = m * self.k
        self.parts.append(
            '<rect x="6" y="%d" width="%.0f" height="30" fill="#fcfcfb" opacity="0.82"/>'
            '<line x1="16" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2.5"/>'
            '<text x="%.1f" y="%d" text-anchor="middle" font-size="11" fill="%s">%d m</text>'
            % (H - 34, L + 24, H - 18, 16 + L, H - 18, PAL['ink'], 16 + L / 2, H - 24,
               PAL['ink'], m))
        self.parts.append(
            '<path d="M%d,%d L%d,%d L%d,%d L%d,%d Z" fill="%s"/>'
            '<text x="%d" y="%d" text-anchor="middle" font-size="10" fill="%s">N</text>'
            % (W - 26, 18, W - 32, 38, W - 26, 33, W - 20, 38, PAL['ink'],
               W - 26, 52, PAL['muted']))

    def svg(self):
        return ('<svg viewBox="0 0 %d %d" width="100%%" style="display:block;background:%s">%s</svg>'
                % (W, H, PAL['surf'], ''.join(self.parts)))


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


DIRS = ['北', '北東', '東', '南東', '南', '南西', '西', '北西']


def bearing(dx, dy):
    return DIRS[int(((math.degrees(math.atan2(dx, dy)) % 360) + 22.5) // 45) % 8]


def nearest(cx, cy, busm, lmkm, facm, stnm, skip=''):
    """地図に入らなかったときのために、最寄りの目印を方角つきで1つずつ返す"""
    out = {}
    for key, items, namei in (('bus', busm, 0), ('lmk', lmkm, 0),
                              ('stn', stnm, 0), ('fac', facm, 1)):
        best = None
        for it in items:
            if skip and it[namei] == skip:      # 対象の公園そのものは目印にしない
                continue
            x, y = it[-2], it[-1]
            d = math.hypot(x - cx, y - cy)
            if best is None or d < best[0]:
                best = (d, it[namei], bearing(x - cx, y - cy))
        if best:
            out[key] = dict(name=best[1], dist=round(best[0]), dir=best[2])
    return out


def fac_rank(name):
    for i, k in enumerate(FAC_KEY):
        if k in name:
            return i
    return 99


def main():
    pref, ward, fac = load_coords()
    op, ctx = load_luse()
    bus = load_bus()
    roads = load_roads()
    B1 = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
    B2 = load_buildings(paths.cache('takada_bldg_lod0.json'))
    ctxm = [(to_m(p), c) for p, c in ctx]
    LOT = unary_union([p for p, c in ctxm if c not in ('217', '215')])
    ROAD = unary_union([p for p, c in ctxm if c == '215'])
    OPEN = unary_union([p for p, c in ctxm if c == '217'])
    BLD = unary_union([p.simplify(0.4) for p, h, _ in (B1 + B2) if p.area >= 25])
    lmk, stn = load_landmarks()
    busm = [(n, ) + FWD.transform(lo, la) for n, lo, la in bus]
    lmkm = [(n, k) + FWD.transform(lo, la) for n, k, lo, la in lmk]
    stnm = [(n, ) + FWD.transform(lo, la) for n, lo, la in stn]
    facm = sorted([(fac_rank(n), n) + FWD.transform(lo, la) for n, lo, la in fac])

    cards = []
    for t in TARGETS:
        p = pref.get(t['name']); w = ward.get(t['name'])
        pts = [FWD.transform(*q[:2]) for q in ([p] if p else []) + ([w] if w else [])]
        cx = sum(a for a, b in pts) / len(pts); cy = sum(b for a, b in pts) / len(pts)
        gap = (math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1])
               if len(pts) == 2 else None)
        src = p if p else w
        g, dist = match(op, src[0], src[1])
        gw, distw = match(op, w[0], w[1]) if w else (None, None)

        m = Map(cx, cy)
        m.poly(LOT, fill=PAL['lot'], stroke=PAL['lot_e'], stroke_width='0.7')
        m.poly(ROAD, fill=PAL['road'], stroke='none')
        m.poly(BLD, fill=PAL['bldg'], stroke=PAL['bldg_e'], stroke_width='0.6')
        m.poly(OPEN, fill=PAL['park'], opacity='0.20', stroke=PAL['park'],
               stroke_width='2', stroke_dasharray='6 4')
        # ラベルは 公園の点 → 道路名 → バス停 → 施設 の順（先勝ち）
        if p:
            m.park_mark(*FWD.transform(p[0], p[1]), color=PAL['pref'], lab='都')
        if w:
            m.park_mark(*FWD.transform(w[0], w[1]), color=PAL['ward'], lab='区', anchor='end')
        for nm, ps in sorted(roads.items(), key=lambda kv: -len(kv[1])):
            m.road(ps, nm)
        def draw(items, fn, cap):
            n = 0
            for it in items:
                if n >= cap:
                    break
                before = len(m.parts)
                fn(*it)
                n += (len(m.parts) > before)
            return n
        ns = draw([(x, y, nm) for nm, x, y in stnm], m.station, 4)
        nb = draw([(x, y, nm) for nm, x, y in busm], m.bus, 7)
        nl = draw([(x, y, nm, kd) for nm, kd, x, y in lmkm], m.landmark, 6)
        nf = draw([(x, y, nm) for _, nm, x, y in facm], m.fac, 10)
        m.furniture()
        near = nearest(cx, cy, busm, lmkm, facm, stnm, skip=t['name'])

        cards.append(dict(t=t, pref=p, ward=w, gap=gap,
                          poly_area=(g.area if g is not None else None),
                          poly_dist=dist, poly_dist_ward=distw,
                          n_bus=nb, n_fac=nf, n_lmk=nl, n_stn=ns, near=near,
                          has_bldg=(not BLD.is_empty and BLD.distance(Point(cx, cy)) < 200),
                          svg=m.svg()))
    json.dump([{k: v for k, v in c.items() if k != 'svg'} for c in cards],
              open(paths.out('park_locate.json'), 'w'), ensure_ascii=False, default=str)
    return cards


if __name__ == '__main__':
    for c in main():
        print('%-16s ズレ%s ポリゴン%s(%s先) バス停%d 施設%d'
              % (c['t']['name'][:16],
                 ('%5.0fm' % c['gap']) if c['gap'] else '   —',
                 ('%6.0f㎡' % c['poly_area']) if c['poly_area'] else '  なし',
                 ('%3.0fm' % c['poly_dist']) if c['poly_dist'] is not None else ' — ',
                 c['n_bus'], c['n_fac']))
