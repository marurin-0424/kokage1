# -*- coding: utf-8 -*-
"""時刻6枚（11〜16時）× 行き先3件 の中身を確定する（2026-08-17 新設）

★ 2026-08-17 の設計変更を反映：
  ・主指標は「滞在込みの合計mL」に戻す（退化テスト＝degrade.py の結果）
  ・時刻は 11〜16時 の6枚。推奨バッジは付けず「ずらしたときの差」を見せる
  ・入力WBGTは「いまの時刻」の値。他の時刻には実測の時刻差を当てる（下の WBGT_OFFSET）
  ・既定の遊び方は「走り回る中心（走る75%）」。sit は [R-09c] の 2.2（2026-08-17 訂正）
"""
import json
import hydration, destination as D, paths

ORIGIN = (139.71150, 35.72950)
LABEL = '池袋駅東口'
WBGT_AT_BASE = 29.0          # 利用者が入力する「いまの時刻＝13時」の暑さ指数
BASE_HOUR = 13
HOURS = (11, 12, 13, 14, 15, 16)
TOP = 3

# ［事実：2026-08-17 実測］環境省 2025年8月・3地点・31日＝93サンプル。
#   同じ日の13時を基準にした WBGT の差（平均）。ばらつきは標準偏差 0.98〜1.46℃。
WBGT_OFFSET = {11: -0.44, 12: -0.22, 13: 0.00, 14: -0.35, 15: -0.60, 16: -1.38}
WBGT_SD     = {11: 1.20, 12: 0.98, 13: 0.00, 14: 1.29, 15: 1.33, 16: 1.46}

# ［事実：2026-08-17 実測 hour_pick.py］出発地から400m圏の歩道の日陰率（延長重み）
SIDEWALK_SHADE = {11: 36.9, 12: 25.5, 13: 33.9, 14: 50.8, 15: 64.3, 16: 72.4}

# 既定の遊び方＝走る75%。sit は [R-09c]「子どもと遊ぶ（座位、軽度）」2.2
METS_DEFAULT = round(0.75 * 5.8 + 0.25 * 2.2, 4)     # ＝4.90

out = {}
for h in HOURS:
    w = round(WBGT_AT_BASE + WBGT_OFFSET[h], 2)
    hydration.METS['play_active'] = METS_DEFAULT
    res = D.recommend(hour=h, wbgt=w, stay_min=60.0, bw=15.0, stroller=False,
                      origin=ORIGIN, top=400)
    parks = [x for x in res['all'] if not x['indoor']]
    by_ml = sorted(parks, key=lambda x: x['total'])
    print('=' * 100)
    print(f"■ {LABEL} {h}:00 ／ WBGT {w}（入力29.0 {WBGT_OFFSET[h]:+.2f} ±{WBGT_SD[h]:.1f}）"
          f"／ 歩道の日陰 {SIDEWALK_SHADE[h]}% ／ 遊び方 走る75%(METs {METS_DEFAULT}) ／ 候補{len(parks)}件"
          f" ／ ゲート{'★発動' if res['gate'] else '通過'}")
    print(f"  {'順':>2} {'公園':<18}{'合計mL':>8}{'往復':>7}{'滞在':>7}{'往復日なた':>11}{'往復m':>8}{'公園日陰率':>10}{'精度':>5}")
    for i, x in enumerate(by_ml[:6], 1):
        mark = '★' if i <= TOP else ' '
        print(f" {mark}{i:>2} {x['name']:<18}{x['total']:>7.0f}{x['move']:>7.0f}{x['stay']:>7.0f}"
              f"{x['sun_min']:>9.1f}分{x['dist']*2:>7.0f}{x['shade']*100:>9.1f}%{x['acc']:>5}")
    if len(by_ml) > 1:
        d = by_ml[1]['total'] - by_ml[0]['total']
        print(f"  1位と2位の差 {d:.0f}mL（{d/by_ml[0]['total']*100:.1f}%）"
              f" ／ 3位まで {by_ml[min(2,len(by_ml)-1)]['total']-by_ml[0]['total']:.0f}mL")
    out[h] = dict(
        wbgt=w, wbgt_offset=WBGT_OFFSET[h], wbgt_sd=WBGT_SD[h],
        sidewalk_shade=SIDEWALK_SHADE[h], gate=res['gate'], n=len(parks),
        top=[dict(name=x['name'], total=round(x['total']), move=round(x['move']),
                  stay=round(x['stay']), sun_min=round(x['sun_min'], 2),
                  dist2=round(x['dist'] * 2), shade=round(x['shade'], 4), acc=x['acc'])
             for x in by_ml[:TOP]],
        all=[dict(name=x['name'], total=round(x['total']), sun_min=round(x['sun_min'], 2),
                  dist2=round(x['dist'] * 2)) for x in by_ml])

json.dump(dict(origin=LABEL, wbgt_input=WBGT_AT_BASE, base_hour=BASE_HOUR,
               mets_play=METS_DEFAULT, hours=out),
          open(paths.out('screen6.json'), 'w'), ensure_ascii=False, indent=1)
print('\nDONE -> out/screen6.json')
