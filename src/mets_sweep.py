# -*- coding: utf-8 -*-
"""滞在中の「走る割合」を振って、合計mLと1位がどう動くかを見る。

★ 2026-08-17 改訂：「走らない時間」の METs を 1.3 → 2.2 に直しました。
  ［事実］旧版は `sit`＝**1.3（座位・静かに＝何もしていない座位）**を当てていました。
  ［事実］`[R-09c]` 厚労省「生活活動のメッツ表」の3メッツ未満の欄に
        **「子どもと遊ぶ（座位、軽度）2.2」**という専用の行があります（data-sources.md §10-3）。
        公園で座って遊んでいる子どもには、こちらが正しい。
  → 実行結果（2026-08-17）：**1位は1ケースも入れ替わらず**、合計は座り7割で **+16〜22%**。
    **1位が入れ替わる走る割合は 14:00 で 66.8%→58.5%、13:00 で 25.9%→7.4% と、既定75%から遠ざかりました。**

使い方
  python3 mets_sweep.py            # 現行（座り＝2.2）
  python3 mets_sweep.py --compare  # 旧（1.3）と並べて比較する
"""
import paths
import sys, hydration, destination as D

# ★ 経路（グラフ）は滞在の METs に依存しないので、時刻ごとに1回だけ組む
_CACHE = {}
_orig_prepare = D._prepare
def _prepare(hour, wbgt, stroller, sun_frac):
    k = (hour, wbgt, stroller, sun_frac)
    if k not in _CACHE:
        _CACHE[k] = _orig_prepare(hour, wbgt, stroller, sun_frac)
    return _CACHE[k]
D._prepare = _prepare

BASE = dict(wbgt=29.0, stay_min=60.0, bw=15.0, stroller=False, origin=(139.71150, 35.72950))

SIT_NOW = hydration.METS['play_sit']      # 2.2（[R-09c]「子どもと遊ぶ（座位、軽度）」）
SIT_OLD = hydration.METS['sit']           # 1.3（座位・静かに）★ 2026-08-17 まで使っていた値
# ★ run() が hydration.METS['play_active'] を書き換えるので、走る側の値は先に控えておく
ACTIVE = hydration.METS['play_active']    # 5.8（子どもと遊ぶ・歩く/走る、活発に）

RUNS = [(1.00, '走る100%（旧・固定値）'), (0.75, '走り回る中心＝現行の既定'), (0.50, '半々'),
        (0.30, '★対象者1（座り7割）'), (0.25, '座って遊ぶ中心'), (0.00, '座り100%')]


def mets(r, sit):
    """走る割合 r のときの、滞在中の実効METs"""
    return round(r * ACTIVE + (1 - r) * sit, 4)


def run(hour, r, sit):
    hydration.METS['play_active'] = mets(r, sit)
    res = D.recommend(hour=hour, top=60, **BASE)
    parks = sorted([x for x in res['all'] if not x['indoor']], key=lambda x: x['total'])
    return res['main'], parks


def flip(hour, sit):
    """1位が入れ替わる走る割合を二分探索。入れ替わらなければ None"""
    lo, hi = 0.0, 1.0
    n0 = run(hour, 0.0, sit)[0]['name']
    n1 = run(hour, 1.0, sit)[0]['name']
    if n0 == n1:
        return None, n0, n1
    for _ in range(11):
        mid = (lo + hi) / 2
        if run(hour, mid, sit)[0]['name'] == n0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, n0, n1


def sweep(hour, sit, tag):
    print(f"  ── 座りの METs：{tag}")
    print(f"    {'走る割合':<24}{'METs':>6}  {'1位':<14}{'合計':>8}{'往復':>7}{'滞在':>7}   2位との差")
    for r, lab in RUNS:
        m, parks = run(hour, r, sit)
        gap = parks[1]['total'] - parks[0]['total']
        print(f"    {lab:<24}{mets(r, sit):>6.2f}  {m['name']:<14}{m['total']:>6.0f}mL"
              f"{m['move']:>6.0f}{m['stay']:>7.0f}   +{gap:>4.0f}mL ({parks[1]['name']}) "
              f"{gap / parks[0]['total'] * 100:.1f}%")
    f, n0, n1 = flip(hour, sit)
    if f is None:
        print(f"    ★ 走る割合を 0〜100% 動かしても1位は {n0} のまま")
    else:
        print(f"    ★ 1位が入れ替わる走る割合 ≒ {f * 100:.1f}%（実効METs {mets(f, sit):.2f}）"
              f" : {n0} ←→ {n1}")


if __name__ == '__main__':
    compare = '--compare' in sys.argv
    for hour in (13, 14, 16):
        print(f"\n■ 池袋駅東口 {hour}:00 / WBGT29 / 60分 / 15kg / 歩行53.1m/分")
        if compare:
            sweep(hour, SIT_OLD, f'旧 sit={SIT_OLD}（座位・静かに）★2026-08-17 まで')
        sweep(hour, SIT_NOW, f'現行 {SIT_NOW}（[R-09c] 子どもと遊ぶ・座位、軽度）')
