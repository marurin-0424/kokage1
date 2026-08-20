# -*- coding: utf-8 -*-
"""行き先ごとの「往復の日なた時間」で並べたらどうなるか（2026-08-16 新設）

★ なぜ作ったか
  ヒアリング1人目が「公園の陰があてにならないから、移動だけ参考にする。
  日向時間が短い公園を選ぶ」と述べた。これは
  「同じ行き先への経路選択の差」（route_bench.py）とは別物で、
  「行き先ごとの往復日なた時間の差」＝ 主指標の候補。まだ一度も測っていなかった。

  ※ 日なた時間は歩行のMETsだけで決まるので、遊び方（play_active）に依存しない。
    合計mLは依存するので、参考として座り7割（実効METs 2.65）でも出す。

使い方: PYTHONPATH=. python3 sun_rank.py
"""
import json
import hydration, destination as D, paths

BASE = dict(wbgt=29.0, stay_min=60.0, bw=15.0, stroller=False,
            origin=(139.71150, 35.72950))
LABEL = '池袋駅東口'
METS_SIT7 = round(0.30 * 5.8 + 0.70 * 1.3, 4)   # ＝2.65（走る30%＝座り7割）

out = {}
for hour in (13, 14, 16):
    hydration.METS['play_active'] = METS_SIT7
    res = D.recommend(hour=hour, top=400, **BASE)
    parks = [x for x in res['all'] if not x['indoor']]
    by_ml = sorted(parks, key=lambda x: x['total'])
    by_sun = sorted(parks, key=lambda x: x['sun_min'])
    rank_ml = {x['name']: i + 1 for i, x in enumerate(by_ml)}

    print(f"\n{'='*92}")
    print(f"■ {LABEL} {hour}:00 / WBGT29 / 滞在60分 / 15kg / 歩行53.1m/分 / 座り7割(METs {METS_SIT7})")
    print(f"   公園候補 {len(parks)}件")
    print(f"{'='*92}")
    print(f"{'順':>3} {'公園':<16}{'往復日なた':>10}{'往復距離':>9}{'往復時間':>9}"
          f"{'公園日陰率':>10}{'合計mL':>8}{'mL順位':>7}")
    for i, x in enumerate(by_sun[:12], 1):
        walk_min = x['minutes'] - BASE['stay_min']
        print(f"{i:>3} {x['name']:<16}{x['sun_min']:>8.1f}分{x['dist']*2:>8.0f}m"
              f"{walk_min:>8.1f}分{x['shade']*100:>9.1f}%{x['total']:>7.0f}mL{rank_ml[x['name']]:>6}位")

    top_ml, top_sun = by_ml[0], by_sun[0]
    print()
    print(f"   合計mLの1位     : {top_ml['name']}（往復日なた {top_ml['sun_min']:.1f}分・{top_ml['total']:.0f}mL）")
    print(f"   日なた時間の1位 : {top_sun['name']}（往復日なた {top_sun['sun_min']:.1f}分・{top_sun['total']:.0f}mL）")
    print(f"   → 一致：{'はい' if top_ml['name']==top_sun['name'] else '★ いいえ（指標を替えると答えが変わる）'}")
    s = sorted(x['sun_min'] for x in parks)
    print(f"   日なた時間の分布：最小 {s[0]:.1f}分 / 中央 {s[len(s)//2]:.1f}分 / 最大 {s[-1]:.1f}分"
          f" ／ 1位と2位の差 {by_sun[1]['sun_min']-by_sun[0]['sun_min']:.1f}分"
          f"（{(by_sun[1]['sun_min']-by_sun[0]['sun_min'])/max(by_sun[0]['sun_min'],1e-9)*100:.0f}%）")
    m = sorted(x['total'] for x in parks)
    print(f"   合計mLの分布    ：最小 {m[0]:.0f} / 中央 {m[len(m)//2]:.0f} / 最大 {m[-1]:.0f}mL"
          f" ／ 1位と2位の差 {by_ml[1]['total']-by_ml[0]['total']:.0f}mL"
          f"（{(by_ml[1]['total']-by_ml[0]['total'])/by_ml[0]['total']*100:.1f}%）")

    out[hour] = dict(
        n=len(parks),
        by_sun=[dict(name=x['name'], sun_min=round(x['sun_min'], 2), dist2=round(x['dist']*2),
                     shade=round(x['shade'], 4), total=round(x['total'])) for x in by_sun],
        by_ml=[dict(name=x['name'], total=round(x['total']), sun_min=round(x['sun_min'], 2))
               for x in by_ml])

json.dump(out, open(paths.out('sun_rank.json'), 'w'), ensure_ascii=False, indent=1)
print("\nDONE → out/sun_rank.json")
