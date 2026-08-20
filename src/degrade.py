# -*- coding: utf-8 -*-
"""§5-13-a 退化テスト：主指標「往復mL」は、ただの最寄り案内に化けないか
   往復mL(move) は滞在のMETsに依存しないので、遊び方の設定によらず結果は同じ。
"""
import json, math, hydration, destination as D, paths

BASE = dict(wbgt=29.0, stay_min=60.0, bw=15.0, stroller=False, origin=(139.71150, 35.72950))
LABEL = '池袋駅東口'

def rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0]*len(vals)
    i = 0
    while i < len(order):
        j = i
        while j+1 < len(order) and vals[order[j+1]] == vals[order[i]]:
            j += 1
        avg = (i+j)/2 + 1
        for k in range(i, j+1):
            r[order[k]] = avg
        i = j+1
    return r

def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra)/n, sum(rb)/n
    num = sum((x-ma)*(y-mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x-ma)**2 for x in ra) * sum((y-mb)**2 for y in rb))
    return num/den if den else float('nan')

out = {}
for hour in (13, 14, 16):
    res = D.recommend(hour=hour, top=400, **BASE)
    P = [x for x in res['all'] if not x['indoor']]
    move = [x['move'] for x in P]
    dist = [x['dist'] for x in P]
    sun  = [x['sun_min'] for x in P]
    tot  = [x['total'] for x in P]
    rho_md = spearman(move, dist)
    rho_ms = spearman(move, sun)
    rho_ts = spearman(tot, sun)
    best = lambda key: min(P, key=lambda x: x[key])['name']
    b_move, b_dist, b_sun, b_tot = best('move'), best('dist'), best('sun_min'), best('total')
    by_move = sorted(P, key=lambda x: x['move'])
    by_dist = sorted(P, key=lambda x: x['dist'])
    # 順位が入れ替わる件数（往復mL順 vs 距離順で位置が違う公園）
    pos_d = {x['name']: i for i, x in enumerate(by_dist)}
    swaps = sum(1 for i, x in enumerate(by_move) if pos_d[x['name']] != i)
    print('='*100)
    print(f"■ {LABEL} {hour}:00 / WBGT29 / 15kg / 歩行53.1m/分 / 公園{len(P)}件")
    print(f"  ρ(往復mL, 往復距離) = {rho_md:.4f}   ← 0.95以上なら退化")
    print(f"  ρ(往復mL, 往復日なた時間) = {rho_ms:.4f}")
    print(f"  ρ(合計mL, 往復日なた時間) = {rho_ts:.4f}")
    print(f"  1位：往復mL={b_move} / 最短距離={b_dist} / 日なた時間={b_sun} / 合計mL={b_tot}")
    print(f"  往復mL順と距離順で位置が違う公園：{swaps}/{len(P)}件")
    print(f"  {'順':>3} {'公園':<18}{'往復mL':>8}{'往復距離':>9}{'往復日なた':>11}{'道の日陰率':>11}{'距離順位':>9}")
    for i, x in enumerate(by_move[:8], 1):
        shade_road = 1 - (x['sun_min'] / max(x['minutes']-BASE['stay_min'], 1e-9))
        print(f"  {i:>3} {x['name']:<18}{x['move']:>7.0f}{x['dist']*2:>8.0f}m{x['sun_min']:>9.1f}分"
              f"{shade_road*100:>10.1f}%{pos_d[x['name']]+1:>8}位")
    d1, d2 = by_move[0], by_move[1]
    print(f"  1位と2位の差（往復mL）：{d2['move']-d1['move']:.0f}mL"
          f"（{(d2['move']-d1['move'])/max(d1['move'],1e-9)*100:.1f}%）")
    out[hour] = dict(rho_move_dist=round(rho_md,4), rho_move_sun=round(rho_ms,4),
                     rho_total_sun=round(rho_ts,4), n=len(P), swaps=swaps,
                     best=dict(move=b_move, dist=b_dist, sun=b_sun, total=b_tot),
                     by_move=[dict(name=x['name'], move=round(x['move']), dist2=round(x['dist']*2),
                                   sun_min=round(x['sun_min'],2), total=round(x['total'])) for x in by_move])
json.dump(out, open(paths.out('degrade_test.json'), 'w'), ensure_ascii=False, indent=1)
print('\nDONE -> out/degrade_test.json')
