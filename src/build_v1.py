# -*- coding: utf-8 -*-
"""画面 v1（4ステップ）を1枚のHTMLに書き出す（2026-08-17 新設・C34/C35/C36/C37）

  ① ゲート → ② いつ出るか（11〜16時の6枚） → ③ どこへ行くか（3件＋影の形） → ④ どの道で行くか

★ 設計の根拠は spec.md M2a〜M2c と tasks.md §5-13-a3。
★ 出さないと決めたもの：公園の日陰率（%）／「おすすめ」バッジ／31超えの日の割合。
"""
import json
import hourly, paths

S = json.load(open(paths.out('screen6.json')))
SVG = json.load(open(paths.out('park_svgs.json')))
HOURS = [str(h) for h in hourly.HOURS]

# ★★ 2026-08-20 訂正。旧版は7行で、次の3つが誤りだった。
#   ① 保育園一覧（r5_preschool.csv）はどのスクリプトからも読んでいない（paths.py に置き場があるだけ）
#   ② 豊島区は CC BY 4.0 ではなく CC BY 2.1 日本（区のページの逐語。都カタログの 4.0 と食い違うので厳しい方）
#   ③ アメダスと都道の街路樹は「検証に使用」で、答えには入っていない
#      （sun_frac は固定・route.build() の既定が trees=False）
#   → data-sources.md §7-1／§7-2／§7-3 と、提出フォーム④の区分に合わせた。
#   ★ CC BY の帰属表示義務がかかるのは SRC_LINES の5件。ここを増やすときは §7-1 を先に直すこと。
SRC_LINES = [
    ('東京都3Dデジタルマップ（3D都市モデル 豊島区 2025年度版）', '東京都', 'CC BY 4.0'),
    ('歩行空間ネットワークデータ（池袋駅周辺）', '国土交通省', '公共データ利用規約 第1.0版'),
    ('公共施設一覧', '豊島区', 'CC BY 2.1 日本'),
    ('赤ちゃん・ふらっと一覧', '東京都福祉局', 'CC BY 4.0'),
    ('熱中症予防情報（暑さ指数WBGT）', '環境省', '公共データ利用規約 第1.0版'),
]

# 検証に使ったが、答えには入っていないもの（作品には組み込んでいない旨を明記する）
CHECK_ONLY = '都道の街路樹／アメダス観測データ／緑のオープンデータ／都営バス GTFS-JP'

CSS = """
:root{--surface:#fcfcfb;--plane:#f4f4f1;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--hair:#e1e0d9;--sun:#eb6834;--shade:#2a78d6;--deck:#4a3aa7;--park:#1baf7a;
--warning:#fab219;--critical:#d03b3b}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
font-family:"Hiragino Kaku Gothic ProN","Noto Sans JP",system-ui,sans-serif;
line-height:1.7;-webkit-text-size-adjust:100%}
.wrap{max-width:430px;margin:0 auto;padding:0 16px 56px}
header{padding:20px 0 10px}
.logo{font-size:20px;font-weight:700;letter-spacing:.04em}
.logo span{color:var(--park)}
.tag{font-size:12px;color:var(--muted);margin-top:2px}
.step{background:var(--surface);border:1px solid var(--hair);border-radius:14px;
padding:16px;margin:14px 0}
.no{display:inline-block;font-size:11px;font-weight:700;color:#fff;background:var(--ink);
border-radius:999px;padding:2px 9px;margin-bottom:8px;letter-spacing:.06em}
h2{font-size:17px;margin:0 0 4px}
.lead{font-size:13px;color:var(--ink2);margin:0 0 12px}
.warn{background:#fff8e6;border:1px solid var(--warning);border-radius:10px;
padding:10px 12px;font-size:13px;margin:0 0 12px}
.warn b{color:#8a5f00}
.hours{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.hr{border:1.5px solid var(--hair);background:var(--surface);border-radius:11px;
padding:10px 6px;text-align:center;cursor:pointer;font:inherit;transition:.12s}
.hr[aria-pressed=true]{border-color:var(--park);background:#f2fbf7}
.hr .t{font-size:17px;font-weight:700;display:block}
.hr .s{font-size:10.5px;color:var(--ink2);display:block;margin-top:2px;line-height:1.45}
.hr .bar{display:block;height:7px;border-radius:4px;background:var(--sun);margin:7px 2px 5px;overflow:hidden}
.hr .bar i{display:block;height:7px;background:var(--shade);border-radius:4px 0 0 4px}
.delta{font-size:13px;color:var(--ink2);margin:12px 0 0;padding-top:10px;border-top:1px dashed var(--hair)}
.delta b{color:var(--ink)}
.cards{display:flex;flex-direction:column;gap:10px}
.card{border:1.5px solid var(--hair);border-radius:12px;overflow:hidden;background:var(--surface);
cursor:pointer;text-align:left;font:inherit;width:100%;padding:0}
.card[aria-pressed=true]{border-color:var(--park)}
.card figure{margin:0;background:#fff;border-bottom:1px solid var(--hair)}
.card svg{display:block;width:100%;height:auto}
.card .body{padding:10px 12px}
.card .nm{font-size:16px;font-weight:700}
.card .mt{font-size:12px;color:var(--muted);margin-top:2px}
.card .ml{font-size:13px;color:var(--ink2);margin-top:6px}
.card .ml b{font-size:19px;color:var(--ink)}
.tie{font-size:12px;color:#8a5f00;background:#fff8e6;border-radius:8px;padding:6px 9px;margin:8px 0 0}
.note{font-size:11.5px;color:var(--muted);margin-top:10px;line-height:1.6}
.route{font-size:14px}
.route .big{font-size:20px;font-weight:700}
.legend{display:flex;gap:14px;font-size:11.5px;color:var(--ink2);margin-top:8px;flex-wrap:wrap}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.disc{background:var(--plane);border:1px solid var(--hair);border-radius:10px;
padding:11px 12px;font-size:13px;color:var(--ink);margin-top:12px}
details{margin-top:10px;font-size:12.5px;color:var(--ink2)}
summary{cursor:pointer;color:var(--ink2);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px}
th,td{border-bottom:1px solid var(--hair);padding:5px 4px;text-align:left}
th{color:var(--muted);font-weight:600}
.src{font-size:11px;color:var(--muted);margin-top:18px;line-height:1.7}
.hidden{display:none}
"""


def hour_button(h):
    v = S['hours'][h]
    shade = hourly.sidewalk_shade(int(h))
    w, sd = v['wbgt'], v['wbgt_sd']
    band = f"±{sd:.1f}" if sd else ""
    return (f'<button class="hr" data-h="{h}" aria-pressed="false">'
            f'<span class="t">{h}時</span>'
            f'<span class="bar"><i style="width:{shade:.0f}%"></i></span>'
            f'<span class="s">日陰 {shade:.0f}%<br>暑さ {w:.1f}{band}</span></button>')


def park_card(h, i, t):
    svg = SVG[h].get(t['name'], '')
    walk = round(t['dist2'] / 2 / 53.1)
    return (f'<button class="card" data-h="{h}" data-i="{i}" aria-pressed="{"true" if i==0 else "false"}">'
            f'<figure>{svg}</figure><div class="body">'
            f'<div class="nm">{t["name"]}</div>'
            f'<div class="mt">片道 {t["dist2"]//2}m・歩いて約{walk}分／往復で日なたにいる時間 {t["sun_min"]:.0f}分</div>'
            f'<div class="ml">水 <b>{t["total"]}mL</b> 飲みたいぐらい'
            f'<span style="color:var(--muted)">（往復 {t["move"]} ＋ 滞在60分 {t["stay"]}）</span></div>'
            f'</div></button>')


def hour_panel(h):
    v = S['hours'][h]
    cards = ''.join(park_card(h, i, t) for i, t in enumerate(v['top']))
    d = v['all'][1]['total'] - v['all'][0]['total']
    pct = d / v['all'][0]['total'] * 100
    tie = (f'<p class="tie">1番目と2番目の差は <b>{d}mL（{pct:.1f}%）</b>です。'
           f'<b>どちらを選んでも、ほとんど変わりません。</b></p>') if pct < 5 else \
          (f'<p class="tie" style="background:var(--plane);color:var(--ink2)">'
           f'1番目と2番目の差は {d}mL（{pct:.1f}%）です。同じくらいの候補が'
           f' 他に {v["n"]-3} 件あります。</p>')
    t0 = v['top'][0]
    return (f'<div class="panel hidden" data-h="{h}">'
            f'<div class="cards">{cards}</div>{tie}'
            f'<p class="note">★ 図の青は<b>建物と高架の影</b>です。'
            f'<b>樹木の影は入っていません。</b>公園の日陰は、実際には樹木が作っていることが多く、'
            f'現地で確かめたところ、この図は日陰を 9〜32ポイント少なく見ています。'
            f'<b>割合の数字は出していません。形だけを見てください。</b>オレンジの点線は太陽の方向です。</p>'
            f'<div class="step" style="margin:14px 0 0">'
            f'<span class="no">4／どの道で行くか</span>'
            f'<h2>ここは、こかげが決めます</h2>'
            f'<p class="lead">選んだ行き先まで、日なたのいちばん短い道を出します。'
            f'<b>道路のどちら側の歩道を歩くか</b>まで指示します。</p>'
            f'<p class="route">最短の道より <b class="big">1.8%</b> だけ遠回りすると、'
            f'往復で日なたにいる時間が <b class="big">31%</b> 減ります'
            f'<span style="color:var(--muted)">（n=400 の中央値。0.5分以上減るのは84%）</span>。</p>'
            f'<div class="legend"><span><i style="background:var(--sun)"></i>日なた</span>'
            f'<span><i style="background:var(--shade)"></i>日陰</span>'
            f'<span><i style="background:var(--deck)"></i>高架の下</span>'
            f'<span><i style="background:var(--park)"></i>行き先</span></div>'
            f'<p class="note">この時刻に {t0["name"]} へ行くなら、往復で日なたにいる時間は'
            f' <b>{t0["sun_min"]:.0f}分</b>です。<b>{15}分ごとに給水してください。</b></p>'
            f'</div></div>')


def build():
    hrs = ''.join(hour_button(h) for h in HOURS)
    panels = ''.join(hour_panel(h) for h in HOURS)
    src = (''.join(f'<div>・{n}／{o}／{lic}</div>' for n, o, lic in SRC_LINES)
           + f'<div style="margin-top:9px">ほかに4件（{CHECK_ONLY}）を検証に使いましたが、'
             f'<b>この画面の答えには入っていません。</b></div>')
    best, worst = S['hours']['16'], S['hours']['11']
    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>こかげ — 今日、どこへ連れて行きますか</title><style>{CSS}</style></head><body>
<div class="wrap">
<header><div class="logo">こ<span>か</span>げ</div>
<div class="tag">建物の影から、子連れの外出をすこし楽にする</div></header>

<section class="step"><span class="no">1／今日、行けるか</span>
<h2>暑さ指数は {S['wbgt_input']}（厳重警戒）</h2>
<p class="lead">31以上のときは、行き先を出しません。今日は出せます。</p>
<div class="warn"><b>ただし、幼児にはひとつ上の基準が当てられます。</b>
日本生気象学会「日常生活における熱中症予防指針 Ver.4」p.12-13。
28以上は「不要な外出を控える」帯です。<b>出かけるかどうかは、あなたが決めてください。</b></div>
<p class="note">出典：日本スポーツ協会「熱中症予防運動指針」第6版 p.15（31＝運動は原則中止）／
日本生気象学会「日常生活における熱中症予防指針 Ver.4」p.12。環境省の指針ではありません。</p></section>

<section class="step"><span class="no">2／何時に出るか</span>
<h2>時間をずらすと、大きく変わります</h2>
<p class="lead">出発地から歩ける範囲（400m）の歩道が、その時刻に何%日陰かです。
<b>おすすめは出しません。</b>予定をずらせるかどうかは、あなたにしか分からないからです。</p>
<div class="hours">{hrs}</div>
<p class="delta">11時に出ると <b>{worst['top'][0]['total']}mL</b>、
16時なら <b>{best['top'][0]['total']}mL</b>。<b>ほぼ半分</b>になります。
歩く道の日陰は <b>25%（12時）から 72%（16時）</b>まで変わります。</p>
<p class="note">★ 午前中が涼しいわけではありません。2025年8月の実測では、
<b>11時でも暑さ指数が31以上だった日が55%</b>ありました（15時は48%）。前倒しより、後ろにずらす方が効きます。</p></section>

<section class="step"><span class="no">3／どこへ行くか</span>
<h2>選ぶのは、あなたです</h2>
<p class="lead">水分量の少ない順に3件出します。<b>公園のどこが影になるかを見て、
遊具の場所を思い浮かべて選んでください。</b></p>
{panels}
<details><summary>もっと見る（残りの候補）</summary>
<p class="note">v1 では3件までです。全候補の一覧と、公園名での検索は今後の予定です。</p></details>
</section>

<div class="disc"><b>これは公開データからの推定値です。医学的な判断ではありません。</b>
のどの渇きに応じて自由に飲めるようにしてください（環境省）。</div>

<details><summary>計算の内訳と、前提</summary>
<table><tr><th>項目</th><th>中身</th></tr>
<tr><td>影</td><td>建物 LOD2 実形状585棟＋LOD1、高架デッキ679面。<b>樹木は入っていません</b></td></tr>
<tr><td>歩行速度</td><td>53.1 m/分（3〜5歳連れの実測・n=3）</td></tr>
<tr><td>遊び方</td><td>走り回る中心（走る75%・実効METs 4.90）</td></tr>
<tr><td>暑さ指数</td><td>入力値は13時の値。他の時刻は実測の時刻差（−0.22〜−1.38℃・ばらつき±1.0〜1.5℃）を当てています</td></tr>
<tr><td>精度</td><td>L1＝歩行空間ネットワーク上／L3＝最後の数百mが直線距離からの概算</td></tr>
<tr><td><b>日付</b></td><td><b>太陽の位置は 2026年8月12日で固定しています。晴天時の値です。</b>曇りの日は日陰の差がほとんど消えますが、いまは反映できていません</td></tr>
</table>
<p class="note">計算に使ったスクリプトは公開しています（screen6.py／park_svg.py／hour_pick.py／degrade.py）。</p>
</details>

<div class="src"><b>答えに反映しているデータ（いずれも加工して利用しています）</b>{src}</div>
</div>
<script>
var hs={json.dumps(HOURS)};
function pick(h){{
  document.querySelectorAll('.hr').forEach(function(b){{b.setAttribute('aria-pressed', b.dataset.h===h);}});
  document.querySelectorAll('.panel').forEach(function(p){{p.classList.toggle('hidden', p.dataset.h!==h);}});
}}
document.querySelectorAll('.hr').forEach(function(b){{b.onclick=function(){{pick(b.dataset.h);}};}});
document.querySelectorAll('.card').forEach(function(c){{c.onclick=function(){{
  c.parentNode.querySelectorAll('.card').forEach(function(o){{o.setAttribute('aria-pressed','false');}});
  c.setAttribute('aria-pressed','true');}};}});
pick('13');
</script></body></html>"""
    for p in (paths.build('kokage-v1-mobile.html'), paths.pages('kokage-v1-mobile.html')):
        open(p, 'w', encoding='utf-8').write(html)
        print('wrote', p, len(html), 'bytes')


if __name__ == '__main__':
    build()
