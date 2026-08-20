# -*- coding: utf-8 -*-
"""how-it-works.md の数字を再生成する（トレース＋感度）。

［なぜスクリプトにしたか］2026-08-12 の日陰率バグで how-it-works.md の
593mL のトレースが全部書き換えになった。次に前提が変わったときに
手で直さずに済むよう、数字の出どころを1本のスクリプトにまとめた。
"""
import paths
import sys, json, math
import destination as D
from route import SPEED_M_PER_MIN, SIGNAL_WAIT_SEC
from hydration import sweat_rate, effective_wbgt, Segment, METS

# 見出しに使うケース（v0 の既定）
CASE = dict(hour=14, wbgt=29.0, stay=60.0, bw=15.0, stroller=False,
            origin=(139.71150, 35.72950), origin_label='池袋駅東口')


def one(hour=None, wbgt=None, stay=None, bw=None, speed=None, wait=None,
        mets=None, shade=None, sun_frac=1.0, harsh=True):
    """1条件で合計mLを出す。行き先は基準ケースの1位に固定して比べる。"""
    c = dict(CASE)
    if hour is not None: c['hour'] = hour
    if wbgt is not None: c['wbgt'] = wbgt
    if stay is not None: c['stay'] = stay
    if bw is not None: c['bw'] = bw
    r = D.recommend(hour=c['hour'], wbgt=c['wbgt'], stay_min=c['stay'], bw=c['bw'],
                    stroller=c['stroller'], origin=c['origin'], top=300, sun_frac=sun_frac)
    return r


def rebuild(m, G, speed=SPEED_M_PER_MIN, wait_s=SIGNAL_WAIT_SEC, mets_play=None,
            shade_park=None, wbgt=29.0, bw=15.0, stay=60.0, sun_frac=1.0):
    """行き先と経路を固定したまま、パラメータだけ差し替えて合計を出し直す"""
    move = 0.0; sunmin = 0.0; mins = 0.0
    for u, v in zip(m['path'][:-1], m['path'][1:]):
        e = G[u][v]
        walk = e['dist'] / speed
        w8 = (wait_s / 60.0) if e['wait'] > 0 else 0.0
        sh = e['shade']
        for minutes, mets in ((walk, METS['walk_slow']), (w8, METS['stand'])):
            if minutes <= 0: continue
            for frac, sunlit in ((1 - sh, True), (sh, False)):
                if frac <= 0: continue
                ew = effective_wbgt(wbgt, Segment('', 0, 'stand', sunlit=sunlit, harsh=True), sun_frac)
                move += sweat_rate(ew, mets, bw) * minutes * frac
        mins += walk + w8; sunmin += (walk + w8) * (1 - sh)
    sh = m['shade'] if shade_park is None else shade_park
    mp = METS['play_active'] if mets_play is None else mets_play
    st = 0.0
    for frac, sunlit in ((1 - sh, True), (sh, False)):
        if frac <= 0: continue
        ew = effective_wbgt(wbgt, Segment('', 0, 'stand', sunlit=sunlit, harsh=True), sun_frac)
        st += sweat_rate(ew, mp, bw) * stay * frac
    return dict(move=move * 2, stay=st, total=move * 2 + st,
                minutes=mins * 2 + stay, sun_min=sunmin * 2)


def main():
    r = D.recommend(hour=CASE['hour'], wbgt=CASE['wbgt'], stay_min=CASE['stay'],
                    bw=CASE['bw'], stroller=CASE['stroller'], origin=CASE['origin'], top=300)
    G = r['G']; m = r['main']
    base = rebuild(m, G)
    segs = []
    for u, v in zip(m['path'][:-1], m['path'][1:]):
        e = G[u][v]
        segs.append(dict(dist=round(e['dist'], 2), walk=round(e['dist'] / SPEED_M_PER_MIN, 4),
                         wait=round(e['wait'], 4), shade=round(e['shade'], 4)))
    out = dict(origin=CASE['origin_label'], hour=CASE['hour'], wbgt=CASE['wbgt'],
               main=m['name'], dist=round(m['dist'], 1), shade=round(m['shade'], 4),
               bcov=round(m['bcov'], 4), area=m['area'], acc=m['acc'],
               n_seg=len(segs), segs=segs,
               move=round(base['move']), stay=round(base['stay']), total=round(base['total']),
               minutes=round(base['minutes']), sun_min=round(base['sun_min'], 1),
               n_shade100=sum(1 for s in segs if s['shade'] >= 0.999),
               n_sun100=sum(1 for s in segs if s['shade'] <= 0.001),
               shade_w=round(sum(s['dist'] * s['shade'] for s in segs) / sum(s['dist'] for s in segs), 4))
    json.dump(out, open(paths.out('trace.json'), 'w'), ensure_ascii=False, indent=1)
    T = out['total']
    print(f"■ {out['origin']} {out['hour']}:00 → {out['main']} {T}mL "
          f"(往復{out['move']} + 滞在{out['stay']}) 区間{out['n_seg']}本 日陰{out['shade_w']:.1%}")

    S = []

    def add(label, v):
        S.append(dict(label=label, total=round(v), delta=round((v - T) / T * 100, 1)))
        print(f'  {label:34s} {v:6.0f} mL  {(v-T)/T*100:+6.1f}%')

    add('基準', T)
    for s in (35.0, 45.0, 60.0, 70.0):
        add(f'歩行速度 {s:.0f} m/分', rebuild(m, G, speed=s)['total'])
    for w in (0.0, 15.0, 60.0, 90.0):
        add(f'信号待ち {w:.0f} 秒', rebuild(m, G, wait_s=w)['total'])
    for mp in (2.8, 4.0, 5.8, 7.0):
        add(f'遊びの METs {mp}', rebuild(m, G, mets_play=mp)['total'])
    for st in (30.0, 45.0, 90.0, 120.0):
        add(f'滞在 {st:.0f} 分', rebuild(m, G, stay=st)['total'])
    for sh in (0.0, 0.25, 0.5, 0.75, 1.0):
        add(f'公園の日陰率 {sh:.0%}', rebuild(m, G, shade_park=sh)['total'])
    for w in (27.0, 28.0, 30.0, 31.0):
        add(f'WBGT {w:.0f}', rebuild(m, G, wbgt=w)['total'])
    for b in (12.0, 18.0, 22.0):
        add(f'体重 {b:.0f} kg', rebuild(m, G, bw=b)['total'])
    for f in (0.0, 0.3, 0.6):
        add(f'くもり係数 f={f}', rebuild(m, G, sun_frac=f)['total'])
    # ★★ 2026-08-15 追加：合計mLではなく「1位そのもの」が入れ替わるかを見る。
    #   ［なぜ］上の感度表は行き先と経路を固定した値。こかげの出力は mL ではなく
    #   「行き先1つ」なので、合計が何%動くかより、順位が入れ替わるかの方が本質。
    #   ［方法］経路は固定したまま、候補それぞれを同じパラメータで計算し直して並べ替える。
    #   ［限界］速度を変えると最短経路そのものも変わりうる。ここでは経路を固定しているので
    #          入れ替わり点は近似値（実測との差は 1〜2 m/分 程度）。
    parks = [x for x in r['all'] if x['kind'] == 'park'][:8]
    flips = []
    print('\n■ 歩行速度と「1位そのもの」')
    prev = None
    for sp in [20, 25, 30, 33, 35, 36, 37, 38, 39, 40, 45, 50, 53.1, 60, 70, 80]:
        tot = []
        for x in parks:
            v = rebuild(x, G, speed=sp)
            tot.append((v['total'], x['name']))
        tot.sort()
        win = tot[0][1]
        flips.append(dict(speed=sp, winner=win, total=round(tot[0][0]),
                          second=tot[1][1], gap=round(tot[1][0] - tot[0][0])))
        mark = '  ← ここで入れ替わる' if (prev and prev != win) else ''
        print(f'  {sp:5.1f} m/分 → {win}  {tot[0][0]:5.0f}mL（2位 {tot[1][1]} と {tot[1][0]-tot[0][0]:+.0f}mL）{mark}')
        prev = win
    json.dump(dict(base=T, cases=S, speed_flip=flips), open(paths.out('sensitivity.json'), 'w'),
              ensure_ascii=False, indent=1)
    print('DONE')


if __name__ == '__main__':
    main()
