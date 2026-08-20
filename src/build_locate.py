# -*- coding: utf-8 -*-
"""park-check.html（第2版：場所の確認）を組み立てる"""
import paths
import sys, io
import park_locate as PL

CSS = """
:root{--surface:#fcfcfb;--plane:#f4f4f1;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
 --hair:#e1e0d9;--pref:#2a78d6;--ward:#eb6834;--park:#1baf7a;--bad:#d03b3b}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--plane);color:var(--ink);
 font-family:system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;font-size:15px;line-height:1.65}
.wrap{max-width:820px;margin:0 auto;padding:26px 16px 70px}
h1{font-size:26px;margin:6px 0 4px;letter-spacing:.03em}
.sub{color:var(--ink2);font-size:14px;margin:0 0 18px}
.ck{background:var(--surface);border:1px solid var(--hair);border-radius:14px;padding:16px 18px;margin-bottom:16px}
.ck h2{font-size:16px;margin:0 0 10px}
.ck ol{margin:0;padding-left:1.3em}.ck li{margin-bottom:8px;font-size:14.5px}
.bad{background:#fff4f0;border:1px solid #f3c3ae;border-radius:10px;padding:12px 15px;font-size:14px;margin:12px 0}
.warn{background:#fff8e8;border:1px solid #f0dca8;border-radius:10px;padding:12px 15px;font-size:14px;margin:12px 0}
.note{font-size:12.5px;color:var(--muted);line-height:1.6}
.grp{font-size:15px;font-weight:800;letter-spacing:.06em;color:var(--ink2);
 margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--hair)}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:14px;padding:18px;margin-bottom:18px}
.hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.hd .n{font-size:20px;font-weight:800}
.pri{font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;color:#fff}
.p1{background:#d03b3b}.p2{background:#fab219;color:#0b0b0b}.p3{background:#898781}
.addr{font-size:13px;color:var(--muted);margin:2px 0 10px}
.why{font-size:14px;background:var(--plane);border-left:3px solid var(--bad);padding:9px 12px;border-radius:0 8px 8px 0;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-bottom:12px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--hair)}
th{color:var(--muted);font-weight:600;width:12em;font-size:12.5px}
tr:last-child th,tr:last-child td{border-bottom:0}
.map{border:1px solid var(--hair);border-radius:10px;overflow:hidden;margin-bottom:10px}
.lg{font-size:12px;color:var(--ink2);display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px}
.lg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-2px}
.q{border:1px solid var(--hair);border-radius:10px;padding:12px 14px;background:var(--plane)}
.q b{font-size:13.5px}
.q label{display:block;font-size:13.5px;margin:9px 0 3px}
input[type=text]{width:100%;font:inherit;font-size:14px;padding:7px 9px;border:1px solid rgba(11,11,11,.15);
 border-radius:8px;background:#fff}
.opt{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
.opt span{font-size:13px;border:1px solid rgba(11,11,11,.15);border-radius:99px;padding:3px 11px;background:#fff}
b{color:var(--ink)}
footer{margin-top:34px;padding-top:14px;border-top:1px solid var(--hair);font-size:11.5px;color:var(--muted);line-height:1.7}
"""


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;')


def main():
    cards = PL.main()
    o = []
    o.append('<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>現地確認シート — 公園の場所</title><style>%s</style></head><body><div class="wrap">' % CSS)
    o.append('<h1>現地確認シート — 公園の「場所」</h1>')
    o.append('<p class="sub">こかげ／2026-08-12 作成。<b>時刻にも天気にも依存しません。</b>雨でも曇りでも成立します。</p>')

    o.append('''<div class="bad">
<b>★ このシートの目的が変わりました。</b>もとは「時刻ごとの日陰率が合っているか」を見るシートでしたが、
<b>雨が続く見込みで日陰が観察できない</b>のと、作業中に
<b>「同じ公園の座標が、東京都と豊島区で最大164mずれている」</b>ことが分かったためです。
<b>日陰の確認は、晴れる日を改めて決めてから行います。</b>
</div>''')

    o.append('''<div class="ck">
<h2>何を確かめるのか</h2>
<p style="font-size:14.5px;margin:0 0 10px">公園の位置について、<b>3つの公式データが食い違っています。</b>どれが実物かを、現地で1回で決めます。</p>
<table>
<tr><th><span style="color:var(--pref)">● 都の点</span></th><td>東京都「関連データセット 都市公園」の座標（青）</td></tr>
<tr><th><span style="color:var(--ward)">● 区の点</span></th><td>豊島区「公共施設一覧」の座標（橙）</td></tr>
<tr><th><span style="color:var(--park)">▨ ポリゴン</span></th><td>東京都3Dデジタルマップ（PLATEAU）の土地利用<b>「公共空地（公園・緑地、広場、運動場、墓園）」</b>の面（緑の破線）</td></tr>
</table>
<p class="note">［事実］豊島区の都市公園62件のうち<b>58件</b>にこのポリゴンが当たり、面積の相対誤差は<b>中央値6.0%</b>。
公開されている「供用済面積」とよく一致します。調査年は<b>2021年</b>（都市計画基礎調査）。</p>
</div>''')

    o.append('''<div class="ck">
<h2>現地でやること（1公園あたり2〜3分）</h2>
<ol>
<li><b>公園の入口に立って、地図のどの位置にいるかを見る。</b>「都の点」と「区の点」の<b>どちらが公園の中（または入口）に近いか</b>を選ぶ。</li>
<li><b>緑の破線（ポリゴン）の形が、実際の公園の形と合っているか。</b>広すぎる／狭すぎる／ずれている／だいたい合っている、のどれか。</li>
<li><b>公園の中に建物があるか</b>（トイレ・倉庫・管理棟など）。日陰率の計算で「建物の中は公園ではない」と扱っているので、実際にどれくらいあるかを知りたい。</li>
<li><b>写真を1枚。</b>公園全体が入る角度で。あとで地図と重ねます。</li>
</ol>
<p class="note">★ <b>順番はどこからでも構いません。</b>優先度 <span class="pri p1">1</span> の4つだけでも十分価値があります。</p>
</div>''')

    cur = None
    for c in cards:
        t = c['t']
        if t['area'] != cur:
            cur = t['area']
            lab = {'A 高田': 'A　高田・雑司ヶ谷（都電雑司ヶ谷駅・地下鉄雑司が谷駅から徒歩圏）',
                   'B 池袋駅': 'B　池袋駅の周り',
                   'C 遠い': 'C　少し遠い（余力があれば）'}.get(cur, cur)
            o.append('<div class="grp">%s</div>' % lab)
        o.append('<div class="card">')
        o.append('<div class="hd"><span class="n">%s</span><span class="pri p%d">優先 %d</span></div>'
                 % (esc(t['name']), t['pri'], t['pri']))
        o.append('<div class="addr">%s</div>' % esc(t['addr']))
        o.append('<div class="why">%s</div>' % esc(t['why']))
        rows = []
        if c['pref']:
            rows.append(('東京都の座標', '%.5f, %.5f ／ 供用済面積 <b>%s㎡</b>（%s）'
                         % (c['pref'][0], c['pref'][1], format(c['pref'][2], ','), c['pref'][3])))
        else:
            rows.append(('東京都の座標', '<b>データに存在しません</b>（都市公園ではなく児童遊園のため）'))
        if c['ward']:
            rows.append(('豊島区の座標', '%.5f, %.5f' % (c['ward'][0], c['ward'][1])))
        if c['gap']:
            rows.append(('<b>2つの座標のズレ</b>', '<b style="color:var(--bad)">%.0f m</b>' % c['gap']))
        if c['poly_area']:
            rows.append(('ポリゴンの面積', '<b>%s㎡</b>' % format(int(c['poly_area']), ',')))
            rows.append(('ポリゴンまでの距離', '都の点から <b>%.0f m</b>%s'
                         % (c['poly_dist'],
                            '' if c['poly_dist_ward'] is None
                            else '／区の点から <b>%.0f m</b>' % c['poly_dist_ward'])))
        else:
            rows.append(('ポリゴン', '<b>120m以内に見つかりません</b>'))
        if not c['has_bldg']:
            rows.append(('建物', '<b>建物データの収録範囲外</b>です（地図に建物が出ません）'))
        o.append('<table>%s</table>' % ''.join('<tr><th>%s</th><td>%s</td></tr>' % r for r in rows))
        o.append('<div class="map">%s</div>' % c['svg'])
        o.append('<div class="lg">'
                 '<span><i style="background:#2a78d6;border-radius:50%"></i>都の座標</span>'
                 '<span><i style="background:#eb6834;border-radius:50%"></i>区の座標</span>'
                 '<span><i style="background:#1baf7a;opacity:.5"></i>公共空地のポリゴン</span>'
                 '<span><i style="background:#4a3aa7;border-radius:2px"></i>都営バス停留所</span>'
                 '<span><i style="background:#a05a1e;transform:rotate(45deg)"></i>ランドマーク</span>'
                 '<span><i style="background:#fff;border:3px solid #0b0b0b;border-radius:50%"></i>駅</span>'
                 '<span><i style="background:#52514e;border-radius:50%"></i>豊島区の公共施設</span>'
                 '<span><i style="background:#f1f0ed;border:1px solid #dcdbd4"></i>建物</span>'
                 '<span><i style="background:#f8f8f6;border:1px solid #e6e5df"></i>敷地（土地利用）</span>'
                 '<span><i style="background:#ecebe6"></i>道路用地</span>'
                 '<span style="color:#7c7a74">斜体の太字＝通称道路名</span></div>')
        n = c.get('near') or {}
        if n:
            def one(k, lab):
                v = n.get(k)
                return ('<b>%s</b>：%s（<b>%s</b>へ %sm）' % (lab, esc(v['name']), v['dir'], v['dist'])) if v else ''
            bits = [x for x in (one('stn', '最寄り駅'), one('bus', '最寄りバス停'),
                                one('lmk', '最寄りランドマーク'), one('fac', '最寄りの区施設')) if x]
            o.append('<p class="note" style="margin:-4px 0 12px">★ 地図に入らないものも含めた最寄りの目印：'
                     + ' ／ '.join(bits) + '<br>（方角と距離は、地図の中心＝2つの座標の中点からのものです）</p>')
        o.append('''<div class="q">
<b>記入欄</b>
<label>① 公園に近いのはどちらの点か</label>
<div class="opt"><span>都（青）</span><span>区（橙）</span><span>どちらも外れ</span><span>ほぼ同じ</span></div>
<label>② 緑の破線の形は、実際の公園と合っているか</label>
<div class="opt"><span>だいたい合っている</span><span>広すぎる</span><span>狭すぎる</span><span>位置がずれている</span><span>形が全然違う</span></div>
<label>③ 公園の中にある建物（トイレ・倉庫・管理棟など）</label>
<input type="text" placeholder="例：トイレ1棟、倉庫1棟。全体の1割くらい">
<label>④ 気づいたこと・写真のメモ</label>
<input type="text" placeholder="">
</div>''')
        o.append('</div>')

    o.append('''<div class="ck" style="margin-top:26px">
<h2>この確認で何が決まるか</h2>
<table>
<tr><th>①の結果</th><td><b>どちらの座標を使うかが決まります。</b>いまは区の座標を使っている箇所と都の座標を使っている箇所が混在しています</td></tr>
<tr><th>②の結果</th><td><b>円近似をポリゴンに置き換えるかが決まります。</b>合っていれば置き換え（日陰率の計算が大きく変わります。池袋西口公園は 99.9%→39.8% になります）。合っていなければ別の手を考えます</td></tr>
<tr><th>③の結果</th><td>「建物の中は公園ではない」という扱いの妥当性が測れます</td></tr>
</table>
</div>

<div class="warn">
<b>日陰の確認は、晴れる日に改めて。</b>そのときは
<b>山吹の里公園（予測：9:00 日陰94.8%／10:00 78.9%）</b>と
<b>高田一丁目児童遊園（9:00 48.4%／10:00 54.3%）</b>を見ます。
<b>高田一丁目児童遊園がいちばん当たり外れが分かりやすい</b>数字です（ちょうど中間なので）。
</div>''')

    o.append('<footer>こかげ ／ 都知事杯オープンデータ・ハッカソン2026（開発中）<br>'
             'データ：東京都3Dデジタルマップ（PLATEAU仕様）豊島区2025 建築物・土地利用（東京都／CC BY 4.0）／'
             '豊島区 公共施設一覧・関連データセット 都市公園（豊島区・東京都）。<br>'
             '土地利用の調査年は2021年（都市計画基礎調査）。</footer>')
    o.append('</div></body></html>')
    s = ''.join(o)
    io.open(paths.build('park-check.html'), 'w', encoding='utf-8').write(s)
    print('written', len(s) // 1024, 'KB')


if __name__ == '__main__':
    main()
