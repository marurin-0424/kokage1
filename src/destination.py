"""こかげ：行き先を1箇所に収束させる

スコア ＝ 往復の移動水分量(mL) ＋ 滞在中の水分量(mL)
出力  ＝ 1箇所 ＋ その内訳 ＋ 屋内の代替1つ
"""
import paths
import sys, json, math, csv, io, zipfile, re
import networkx as nx
from shapely.geometry import Point
from shapely.ops import unary_union
from route import build, summarize, FWD, SPEED_M_PER_MIN
from shadow import load_buildings, shadow
from hydration import sweat_rate, effective_wbgt, Segment, METS, wbgt_level
import bridge

# 置き場は paths.py に集約（2026-08-13）
GATE_WBGT = 31.0                 # ［事実］JSPO「熱中症予防運動指針」第6版 p.15「運動は原則中止。特に子どもの場合には中止すべき」（環境省の指針ではない）

# 歩行空間NWは網羅ではない（data-sources.md §2 発見④b-3）。ネットワークに載らない候補地は
# 直線距離×迂回係数で近似し、精度レベルを落として出す（spec.md §7-2 L3）。
SNAP_M = 80.0          # ここまでは実経路（L1）
FALLBACK_M = 400.0     # ここまでは直線近似（L3）。それ以上は出さない
DETOUR = 1.3           # ［推測］直線距離→実距離の迂回係数。市街地の一般値
# ★★ 公園の形（2026-08-13 にポリゴンへ置き換え）
#   豊島区の公園データ（都市公園geojson）は「点＋供用済面積」だけで形がない。
#   → PLATEAU の udx/luse（土地利用）に luse:class=217「公共空地（公園・緑地、広場、
#      運動場、墓園）」のポリゴンが 2,261件あり、これを使う（data-sources.md §1d）。
#   ［事実］豊島区の都市公園62件のうち 60件が当たり、面積の相対誤差は中央値7.0%。
#   ［事実］円近似では建物率が平均18.1%あったが、ポリゴンでは平均1.3%。
#   ［事実］2026-08-13 の現地確認で、山吹の里公園・高田一丁目児童遊園の
#          「形はかなり正確」と確認済み（tasks.md B3c）。
LUSE_R = 80.0            # 公園の点から、この距離まで公共空地のポリゴンを探す
LUSE_LO, LUSE_HI = 0.5, 2.0   # 供用済面積に対してこの倍率に収まるものだけ採用（隣を掴まない）
# ポリゴンが当たらなかったときだけ、従来の円近似に落とす。
#   ［事実］円は建物に食い込む（東池袋中央公園の点はサンシャインシティのLOD1の箱の中で、
#          円の100%が建物・地面の日陰率0%だった）。円のときだけ、この保険を残す。
BLDG_COVER_MAX = 0.50
# 外遊びの候補にしない公園（3〜5歳が走り回れないもの）
MIN_AREA_PLAY = 500.0   # ［推測］13m四方（168㎡の元池袋史跡公園）では走り回れない
EXCLUDE_KIND = ('緑道',)  # 線状なので円にもポリゴンにも乗らない

# 目的ごとの候補プールと滞在時の活動強度
PURPOSE = {
    'outdoor_play': dict(label='外で遊ばせたい',       pools=('park',),            mets='play_active'),
    'cool_down':    dict(label='涼みたい',             pools=('indoor',),          mets='play_light'),
    'baby_care':    dict(label='授乳・おむつ替えが要る', pools=('babyflat', 'indoor'), mets='sit'),
}
INDOOR_KEYS = ('区民ひろば', '図書館', '児童館', '子どもスキップ', 'すくすく')


def _norm(s):
    s = re.sub(r'[（(].*?[)）]', '', s or '')
    return re.sub(r'[\s　・（）()]', '', s)


def load_candidates():
    """(kind, name, lon, lat, area, indoor) のリスト"""
    out = []
    z = zipfile.ZipFile(paths.raw('13116_toshima-ku_2025_related.zip'))
    for f in json.load(io.TextIOWrapper(z.open('13116_toshima-ku_pref_2023_park.geojson'),
                                        encoding='utf-8'))['features']:
        a = f['properties'].get('供用済面積') or 0
        if a <= 0 or a < MIN_AREA_PLAY:
            continue
        if f['properties'].get('公園種別') in EXCLUDE_KIND:
            continue
        lo, la = f['geometry']['coordinates'][:2]
        out.append(('park', f['properties']['公園名'] + '公園', lo, la, a, False))

    fac = []
    raw = open(paths.raw('r5_public_facility.csv'), 'rb').read().decode('cp932')
    rr = csv.reader(io.StringIO(raw)); next(rr)
    for x in rr:
        try:
            fac.append((x[4], float(x[11]), float(x[10])))
        except Exception:
            pass
    for nm, lo, la in fac:
        if any(k in nm for k in INDOOR_KEYS):
            out.append(('indoor', nm, lo, la, None, True))

    # 赤ちゃん・ふらっと（座標なし）→ 公共施設一覧と施設名で突合
    # ★ 正規化で括弧を落とすため「区民ひろば要（仮施設）」と「区民ひろば要」が同じキーになる。
    #   先勝ちだと仮施設を拾うので、括弧のない正式名を優先する（2026-08-12 修正）。
    idx = {}
    for n, lo, la in sorted(fac, key=lambda t: (('（' in t[0]) or ('(' in t[0]), len(t[0]))):
        idx.setdefault(_norm(n), (lo, la))
    raw = open(paths.raw('akachanflat_ichiran_R80617.csv'), 'rb').read().decode('cp932')
    rr = csv.reader(io.StringIO(raw)); hdr = next(rr)
    ci = {h: i for i, h in enumerate(hdr)}
    hit = miss = 0
    for x in rr:
        try:
            if '豊島' not in x[ci.get('地域', 1)]:
                continue
            nm = x[ci.get('施設名', 2)]
        except Exception:
            continue
        k = _norm(nm)
        p = idx.get(k) or next((v for kk, v in idx.items() if kk and (kk in k or k in kk)), None)
        if p:
            out.append(('babyflat', nm, p[0], p[1], None, True)); hit += 1
        else:
            miss += 1
    return out, hit, miss


_LUSE = None


def load_luse():
    """公共空地（luse:class=217）のポリゴン。(緯度経度のPolygon, 平面直角のPolygon) の組"""
    global _LUSE
    if _LUSE is None:
        from shapely.geometry import Polygon as _P
        from shapely.ops import transform as _tf
        out = []
        for x in json.load(open(paths.cache('luse_open_space.json'))):
            try:
                q = _P(x['ring'], x['holes'])
                if not q.is_valid:
                    q = q.buffer(0)
                if q.is_empty:
                    continue
                out.append((q, _tf(lambda a, b, z=None: FWD.transform(a, b), q)))
            except Exception:
                pass
        _LUSE = out
    return _LUSE


def park_polygon(lo, la, area):
    """公園の点＋供用済面積 → 公共空地のポリゴン（平面直角）。無ければ None

    ★ 面積ガードを掛けているのは、隣の大きな広場を掴まないため。
      ［事実］ガード無し・半径120mだと 南池袋公園(7,812㎡)が14,904㎡になった。
    """
    pt = Point(lo, la); d = LUSE_R / 111000.0
    cand = [(q, gm) for q, gm in load_luse() if q.distance(pt) < d]
    if not cand:
        return None, None
    ok = [(q, gm) for q, gm in cand if LUSE_LO <= gm.area / area <= LUSE_HI]
    if not ok:
        return None, None
    inside = [(q, gm) for q, gm in ok if q.contains(pt)]
    if inside:
        q, gm = max(inside, key=lambda t: t[1].area)
        return gm, 0.0
    q, gm = min(ok, key=lambda t: t[0].distance(pt))
    return gm, q.distance(pt) * 111000


_CACHE = {}


def _prepare(hour, wbgt, stroller, sun_frac=1.0):
    k = (hour, round(wbgt, 2), stroller, round(sun_frac, 2))
    if k not in _CACHE:
        G, alt, az, _ = build(hour, wbgt_base=wbgt, stroller=stroller, sun_frac=sun_frac)
        B = load_buildings(paths.cache('ikebukuro_bldg_lod0.json'))
        # ★ LOD2 を持つ建物は実形状で（route.build と同じ扱い）
        import lod2
        L2 = lod2.shadows(alt, az, bridge.ground_lookup())
        polys = [shadow(p.simplify(0.3), h, alt, az) for p, h, b in B if b['id'] not in L2]
        polys += list(L2.values())
        decks = bridge.load_decks()
        for g in (bridge.deck_shadow(decks, alt, az), bridge.under_deck(decks)):
            if g is not None:
                polys.append(g)
        U = unary_union(polys)
        # ★ 建物のフットプリント。日陰率は「地面」だけで測る（2026-08-12 修正）。
        #   shadow() の戻り値はフットプリントを含むので、除かないと
        #   「建物の中」を日陰として数えてしまう（東池袋中央公園がサンシャインシティの
        #   LOD1の箱の中に入っており、日陰率100%と出ていた）。
        FOOT = unary_union([p.simplify(0.3) for p, h, _ in B])
        _CACHE[k] = (G, alt, U, FOOT)
    return _CACHE[k]


def recommend(hour=14, wbgt=29.0, stay_min=60.0, stroller=False, bw=15.0,
              purpose='outdoor_play', origin=(139.71150, 35.72950), top=8, sun_frac=1.0):
    G, alt, U, FOOT = _prepare(hour, wbgt, stroller, sun_frac)
    cands, hit, miss = load_candidates()

    # 出発点と同じ連結成分の中だけで最寄りノードを探す（ベビーカー制約で分断されるため）
    def _nn(lo, la, pool, maxd):
        x, y = FWD.transform(lo, la)
        n = min(pool, key=lambda k: (G.nodes[k]['x'] - x) ** 2 + (G.nodes[k]['y'] - y) ** 2)
        d = math.hypot(G.nodes[n]['x'] - x, G.nodes[n]['y'] - y)
        return n if d <= maxd else None

    # ［注］ベビーカー制約下では、最寄りノードが孤立点になることがある（池袋駅東口で実際に発生）。
    #       20ノード以上の成分に限って出発点をスナップする。
    naive = _nn(*origin, G.nodes, 200)
    isolated_origin = naive is not None and len(nx.node_connected_component(G, naive)) < 20
    usable = {k for c in nx.connected_components(G) if len(c) >= 20 for k in c}
    ori0 = _nn(*origin, usable, 200)
    reach = nx.node_connected_component(G, ori0) if ori0 else set()

    def node(lo, la, maxd=SNAP_M):
        return _nn(lo, la, reach, maxd)

    def _snap(lo, la):
        """(node, 残りの直線距離[m], 精度レベル)。NW外の候補は直線距離で補う。"""
        n = _nn(lo, la, reach, SNAP_M)
        if n is not None:
            return n, 0.0, 'L1'
        # ★ ベビーカーありのときは直線近似を使わない。
        #   段差・階段・線路を避けることが目的なのに、直線で跨いだら意味がないため。
        #   （実際、これを入れないと池袋駅を445mの直線で横断して池袋西口公園が1位になった）
        if stroller:
            return None, 0.0, None
        n = _nn(lo, la, reach, FALLBACK_M)
        if n is None:
            return None, 0.0, None
        x, y = FWD.transform(lo, la)
        return n, math.hypot(G.nodes[n]['x'] - x, G.nodes[n]['y'] - y) * DETOUR, 'L3'

    def _local_shade(n, r=200.0):
        """スナップ先ノード周辺の日陰率（延長重み）。NW外区間の日陰率の代用。"""
        px, py = G.nodes[n]['x'], G.nodes[n]['y']
        tot = sh = 0.0
        for u, v, e in G.edges(data=True):
            if math.hypot(G.nodes[u]['x'] - px, G.nodes[u]['y'] - py) > r:
                continue
            tot += e['dist']; sh += e['dist'] * e['shade']
        return (sh / tot) if tot else 0.0

    def _extra(metres, shade):
        """NW外区間（直線近似）の片道 分・mL"""
        mins = metres / SPEED_M_PER_MIN
        ml = 0.0
        for frac, sunlit in ((1 - shade, True), (shade, False)):
            if frac <= 0:
                continue
            w = effective_wbgt(wbgt, Segment('', 0, 'stand', sunlit=sunlit, harsh=True), sun_frac)
            ml += sweat_rate(w, METS['walk_slow'], bw) * mins * frac
        return mins, ml

    def stay_ml(shade, mets, indoor):
        ml = 0.0
        for frac, sunlit in ((1 - shade, True), (shade, False)):
            if frac <= 0:
                continue
            w = effective_wbgt(wbgt, Segment('', 0, 'stand', sunlit=sunlit, harsh=True, indoor=indoor), sun_frac)
            ml += sweat_rate(w, METS[mets], bw) * stay_min * frac
        return ml

    gate = wbgt >= GATE_WBGT
    pools = ('indoor', 'babyflat') if gate else PURPOSE[purpose]['pools']
    mets = 'play_light' if gate else PURPOSE[purpose]['mets']
    ori = ori0
    unreachable = 0
    unusable = 0
    excluded = []

    rows = []
    for kind, nm, lo, la, area, indoor in cands:
        if kind not in pools and kind != 'indoor':
            continue
        n, gap, lvl_acc = _snap(lo, la)
        if n is None:
            unreachable += 1
            continue
        try:
            p = nx.shortest_path(G, ori, n, weight='cost')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        r = dict(summarize(G, p))
        if gap > 0:
            emin, eml = _extra(gap, _local_shade(n))
            r['dist'] += gap; r['ml'] += eml; r['minutes'] += emin
            r['sun_min'] += emin * (1 - _local_shade(n))
            r['sun_dist'] += gap * (1 - _local_shade(n))
        bcov = 0.0
        geom = None
        if indoor:
            shade = 1.0
            st = stay_ml(0.0, mets, True)
        else:
            c, gap_poly = park_polygon(lo, la, area)
            if c is not None:
                geom = 'luse'                                 # ★ 実測された公園の形
            else:
                geom = 'circle'                               # 当たらなければ従来の円
                R = math.sqrt(area / math.pi)
                c = Point(*FWD.transform(lo, la)).buffer(R)
            ground = c.difference(FOOT)                       # 建物の中は「公園」ではない
            bcov = 1.0 - ground.area / c.area
            if geom == 'circle' and bcov > BLDG_COVER_MAX:    # 円のときだけの保険
                unusable += 1
                excluded.append(dict(name=nm, bcov=round(bcov, 3), area=area,
                                     reason='形のデータが無く、円の%.0f%%が建物' % (bcov * 100)))
                continue
            shade = U.difference(FOOT).intersection(c).area / max(ground.area, 1e-9)
            st = stay_ml(shade, mets, False)
        rows.append(dict(kind=kind, name=nm, dist=r['dist'], move=r['ml'] * 2, shade=shade,
                         stay=st, total=r['ml'] * 2 + st, indoor=indoor, path=p,
                         acc=lvl_acc, gap=gap, bcov=bcov, area=area, geom=geom,
                         sun_min=r['sun_min'] * 2, minutes=r['minutes'] * 2 + stay_min,
                         sun_dist=r['sun_dist'] * 2))
    rows.sort(key=lambda x: x['total'])
    main = next((r for r in rows if (r['kind'] in pools)), None)
    alt_indoor = next((r for r in rows if r['indoor'] and r is not main), None)
    lvl, advice, rest = wbgt_level(wbgt)
    return dict(gate=gate, level=lvl, advice=advice, rest=rest, main=main,
                alt=alt_indoor, all=rows[:top], G=G, hit=hit, miss=miss, alt_deg=alt,
                n_cand=len(rows), unreachable=unreachable, unusable=unusable, excluded=excluded,
                isolated_origin=isolated_origin, reach=len(reach))


def render(res, wbgt, stay_min, purpose, stroller):
    m, a = res['main'], res['alt']
    print(f"── WBGT {wbgt}（{res['level']}）／滞在{stay_min:.0f}分／{PURPOSE[purpose]['label']}"
          f"／ベビーカー{'あり' if stroller else 'なし'} ──")
    if res['gate']:
        print(f"  ★ 今日は外に出ない方がいいです（{res['advice']}）")
        print("    屋内なら：", end='')
    if not m:
        print('  候補が見つかりませんでした'); return
    print(f"【{m['name']}】")
    print(f"    片道 {m['dist']:.0f}m ／ 往復{m['move']:.0f}mL ＋ 滞在{m['stay']:.0f}mL "
          f"＝ 合計 {m['total']:.0f}mL")
    if m.get('acc') == 'L3':
        print(f"    ※ この行き先は歩行空間ネットワークに接続していません。"
              f"最後の{m['gap']:.0f}mは直線距離からの概算です（精度レベルL3）")
    if not m['indoor']:
        print(f"    公園の日陰率 {m['shade']:.0%} ／ 往復で日なたにいる時間 {m['sun_min']:.0f}分")
    if res['rest']:
        print(f"    {res['rest']}分ごとに給水してください"
              f"（お子様がのどの渇きに応じて自由に飲めるように）")
    if a and a is not m:
        print(f"    だめなら屋内：{a['name']}（合計 {a['total']:.0f}mL）")
