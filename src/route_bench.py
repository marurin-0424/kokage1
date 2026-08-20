# -*- coding: utf-8 -*-
"""経路ベンチ：最短経路 vs こかげ経路（2026-08-16 再作成）

★ なぜ作り直したか
  spec.md §8-2 の「ランダム138経路」は 2026-08-12 に実行したもので、
  ① 歩行速度が 35 m/分（旧・［推測］）
  ② LOD2化（2026-08-13）より前＝LOD1の箱ベース
  ③ 日なた時間の「分母」（最短経路の日なた時間）が記録されておらず % で言えない
  という3つの問題があった。スクリプト自体も保存されていなかった。

使い方: PYTHONPATH=. python3 route_bench.py [hour] [n] [seed]
"""
import sys, json, random, statistics as st
import networkx as nx
import route as R
import paths
from shadow import load_links
from sidewalk import find_pairs

HOUR = int(sys.argv[1]) if len(sys.argv) > 1 else 14
N_ROUTE = int(sys.argv[2]) if len(sys.argv) > 2 else 400
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 20260816
MIN_DIST = 300.0


def link_index(G, links):
    """G の各エッジに、元の link の通し番号を割り当てる（同一道路ペア判定に使う）"""
    key = {}
    for i, (ls, pr) in enumerate(links):
        a, b = str(pr.get('start_id')), str(pr.get('end_id'))
        key[(a, b)] = i
        key[(b, a)] = i
    return key


def main():
    G, alt, az, skipped = R.build(HOUR, stroller=False)
    links = load_links(paths.raw('ikebukuro_link.geojson'))
    key = link_index(G, links)
    partner = {}
    for i, j, sep, b, linked in find_pairs(links):
        if linked:
            partner.setdefault(i, set()).add(j)
            partner.setdefault(j, set()).add(i)

    comp = max(nx.connected_components(G), key=len)
    nodes = sorted(comp)
    rnd = random.Random(SEED)

    rows = []
    tried = 0
    while len(rows) < N_ROUTE and tried < N_ROUTE * 60:
        tried += 1
        u, v = rnd.sample(nodes, 2)
        try:
            p_short = nx.shortest_path(G, u, v, weight='dist')
            p_koka = nx.shortest_path(G, u, v, weight='cost')
        except nx.NetworkXNoPath:
            continue
        s = R.summarize(G, p_short)
        k = R.summarize(G, p_koka)
        if s['dist'] < MIN_DIST:
            continue
        li_s = {key.get(e) for e in zip(p_short[:-1], p_short[1:])}
        li_k = {key.get(e) for e in zip(p_koka[:-1], p_koka[1:])}
        only_k = li_k - li_s
        swap = any(partner.get(i, set()) & li_s for i in only_k if i is not None)
        rows.append(dict(
            d_short=s['dist'], d_koka=k['dist'],
            sun_short=s['sun_min'], sun_koka=k['sun_min'],
            ml_short=s['ml'], ml_koka=k['ml'], swap=swap))

    def q(f):
        xs = sorted(f(r) for r in rows)
        return st.median(xs), sum(xs) / len(xs), xs[0], xs[-1]

    dd = [(r['d_koka'] - r['d_short']) / r['d_short'] * 100 for r in rows]
    ds = [r['sun_koka'] - r['sun_short'] for r in rows]
    dm = [r['ml_koka'] - r['ml_short'] for r in rows]
    rel = [(r['sun_koka'] - r['sun_short']) / r['sun_short'] * 100
           for r in rows if r['sun_short'] > 0.01]

    print(f"■ 経路ベンチ {HOUR}:00 / n={len(rows)} / seed={SEED} / 最短経路長≧{MIN_DIST:.0f}m")
    print(f"   歩行速度 {R.SPEED_M_PER_MIN} m/分 ・ LOD2実形状 ・ ベビーカーなし")
    print()
    print(f"{'指標':<34}{'中央値':>10}{'平均':>10}{'最良':>10}")
    print(f"{'距離の増分 (%)':<34}{st.median(dd):>+10.1f}{sum(dd)/len(dd):>+10.1f}{max(dd):>+10.1f}")
    print(f"{'日なた時間の差 (分)':<32}{st.median(ds):>+10.1f}{sum(ds)/len(ds):>+10.1f}{min(ds):>+10.1f}")
    print(f"{'日なた時間の差 (%)':<33}{st.median(rel):>+10.1f}{sum(rel)/len(rel):>+10.1f}{min(rel):>+10.1f}")
    print(f"{'合計mLの差':<36}{st.median(dm):>+10.1f}{sum(dm)/len(dm):>+10.1f}{min(dm):>+10.1f}")
    print()
    print(f"★ 分母（最短経路の日なた時間）  中央値 {st.median([r['sun_short'] for r in rows]):.1f}分"
          f" / 平均 {sum(r['sun_short'] for r in rows)/len(rows):.1f}分")
    print(f"★ 最短経路の長さ                中央値 {st.median([r['d_short'] for r in rows]):.0f}m")
    print(f"★ 同じ道路の反対側の歩道に乗り換えた経路：{sum(r['swap'] for r in rows)}/{len(rows)}"
          f" ＝ {sum(r['swap'] for r in rows)/len(rows)*100:.0f}%")
    print()
    imp = sum(1 for x in ds if x < -0.5)
    print(f"［分布］日なたが 0.5分以上 減った経路：{imp}/{len(rows)} ＝ {imp/len(rows)*100:.0f}%")
    for lo, hi in ((-999, -10), (-10, -5), (-5, -2), (-2, -0.5), (-0.5, 999)):
        c = sum(1 for x in ds if lo <= x < hi)
        print(f"   {lo if lo>-999 else '':>5}〜{hi if hi<999 else '':<5}分 : {c:>4}本 ({c/len(rows)*100:>4.1f}%)")

    json.dump(dict(hour=HOUR, n=len(rows), seed=SEED, speed=R.SPEED_M_PER_MIN,
                   d_pct=dict(median=st.median(dd), mean=sum(dd)/len(dd), best=max(dd)),
                   sun_min_diff=dict(median=st.median(ds), mean=sum(ds)/len(ds), best=min(ds)),
                   sun_pct_diff=dict(median=st.median(rel), mean=sum(rel)/len(rel), best=min(rel)),
                   sun_short=dict(median=st.median([r['sun_short'] for r in rows])),
                   ml_diff=dict(median=st.median(dm), mean=sum(dm)/len(dm), best=min(dm)),
                   swap_rate=sum(r['swap'] for r in rows)/len(rows)),
              open(paths.out(f'route_bench_{HOUR}.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
