# -*- coding: utf-8 -*-
"""こかげ v0.1（ヒアリング用・スマホ）：単一HTMLを組み立てる。

★ build_screen.py（PC版）との関係
  - データ源は同じ（screen_cases.json ＋ screen_svgs.json）。**数値はここで一切作らない。**
  - 違いはレイアウトだけ。PC版 1600×900 / モバイル版 390px 基準。
  - デザインは design/design-handoff.md に沿って外部で起こしたものを、実データに接続した。

★ 制約（design-handoff.md §3-1）
  1. 単一HTML・CSS/JS/SVGはすべてインライン
  2. 外部通信ゼロ（Webフォント・CDN・画像URL・アイコンフォントは使わない）
  3. 画像を使わない
  4. localStorage / sessionStorage を使わない
  5. スマホ前提（幅390px基準）
  6. フォントは system-ui 系に固定
  7. 地図は viewBox="0 0 720 540" のインラインSVGを幅100%・比率維持で差し込む

★ v0 で「効く」入力（2026-08-15 時点）
  出発地3 × 時刻2 ＋ WBGTゲート1 ＋ 収録範囲外1。
  それ以外（16:00・屋内・遊び方・滞在時間・ベビーカー・体重）は**事前計算していない**。
  押せるようにはするが「未計算」と明示し、結果画面の先頭に何を代用したかを出す。
  ［理由］重い処理をしているように見せない（design-handoff.md §8）。
"""
import paths
import json

D = json.load(open(paths.out('screen_cases.json'), encoding='utf-8'))
SV = json.load(open(paths.cache('screen_svgs.json'), encoding='utf-8'))

from route import SPEED_M_PER_MIN as SPEED   # ★ 直書きしない。route.py を単一の出どころにする
#   （2026-08-15 まで 35.0 を直書きしていた。route.py を実測値に更新しても画面が追随しない状態だった）

# ---- v0 で事前計算済みの入力値（ここに無いものは「未計算」チップが付く） -------------
COMPUTED = {
    'hour':     ['12', '14'],
    'place':    ['outdoor'],
    'play':     ['active'],
    'stay':     ['60'],
    'stroller': ['no'],
    'bw':       ['15'],
}
LABEL = {'16': '16:00', 'indoor': '屋内', 'half': '半々', 'sit': '座って遊ぶ中心',
         '30': '30分', '90': '90分', 'yes': 'あり',
         '12kg': '12 kg', '18kg': '18 kg', '22kg': '22 kg'}
SUBST = {'hour': '14:00', 'place': '屋外', 'play': '走り回る中心', 'stay': '60分',
         'stroller': 'なし', 'bw': '15 kg'}

# ［事実］WBGT の運動指針は日本スポーツ協会が単独で作ったもの。環境省は転載している側。
#        （data-sources.md §10 R-01／R-08 p.46）。「環境省・日本スポーツ協会は」と
#        並記すると帰属を誤る。
GATE_SRC = '出典：日本スポーツ協会「スポーツ活動中の熱中症予防ガイドブック」第6版 熱中症予防運動指針'

# ★ 2026-08-17（tasks.md §5-4・案A）：WBGT 28〜31 の帯で行き先を出すときは、
#   「幼児・学童には一つ上の温度基準域の注意事項を適用する」（[R-02] p.12-13）を
#   自分から開示する。★ ゲート（31）は動かさない。
#   根拠：data-sources.md §10-3「★R-02 p.12-13」／§10-4 論点6／hydration-model.md §1
#   ★ 2025年8月・練馬の実測では 12〜15時の 77% が WBGT 28以上・48% が 31以上。
#     ゲートを28にすると v0 の公園ケースが全滅するため、開示で対応する。
WARN28 = ('日本生気象学会の指針は、<b>幼児・学童にはひとつ上の区分</b>を当てるとしています。'
          'いまは <b>厳重警戒</b> なので、お子様にとっては <b>危険</b> と同じ注意事項'
          '（外出はなるべく避け、涼しい室内へ）が当たる帯です。')
WARN28_SRC = '出典：日本生気象学会「日常生活における熱中症予防指針 Ver.4」p.3・p.12-13'

# 免責（design-handoff.md §9。短くしないこと）
DISC = ('暑さ目安は推定値で、医学的な判断ではありません。実際の給水は、お子様の様子を見て、'
        'のどの渇きに応じて自由に飲めるようにしてください。')

# ★ 1位カードの吹き出し。design-handoff.md §9 と spec.md §1-2（摂取量の指示は作らない）を
#   優先するなら「暑さの単位」側の文にする。1行で差し替えられるようにここに出してある。
TIP = '行って遊んで帰るまでに<br>お子様の体が必要とする水分の目安'

DIS_HTML = ('<ul><li><b>日陰</b>は、PLATEAUから、建物と鉄道・道路の高架の形をもとに計算しています。'
            '公園内の樹木・街路樹（道路沿いに植えられた樹木）は含みません。'
            '（PLATEAU：国土交通省が公開している3D都市モデル。建物の輪郭と高さのデータ）</li>'
            '<li>豊島区内には<b>WBGT</b>（熱中症予防の目安指標）の観測地点が存在せず、'
            '近隣地点の観測結果を用いているため、結果数値はおよそ <span class="num">±15%</span> の'
            'ブレが生じ、順位が入れ替わることもあります。</li></ul>')

LVL_HTML = ('<div class="lvlt">経路の精度</div>'
            '<div class="row"><span class="acc">L1</span><span>歩行空間ネットワークデータの上を'
            '実際にたどった経路（歩行空間ネットワークデータ：国土交通省が仕様を定めて整備している、'
            '歩道・横断歩道・階段・段差を線でつないだ地図データ）</span></div>'
            '<div class="row"><span class="acc l3">L3</span><span>歩行空間ネットワークデータに'
            'つながっていない行き先。データ上のいちばん近い接続点（歩行空間ネットワークデータの上で、'
            '経路の計算に使える地点）までは実際の経路、その先は直線距離を1.3倍して概算</span></div>')


def pack(c, svg):
    """screen_cases.json の1ケース → 画面が使う形。★ 数値の加工はここだけ。"""
    m = c['main']
    rk = []
    for i, r in enumerate(c['ranking'][:3]):
        rk.append(dict(name=r['name'], total=r['total'], move=r['move'], stay=r['stay'],
                       dist=r['dist'], round_m=r['dist'] * 2, sun_dist=r['sun_dist'],
                       shade=r['shade'], acc=r['acc'], indoor=r['indoor']))
    return dict(
        origin=c['origin_label'], sub=c['origin_sub'], hour=c['hour'], wbgt=c['wbgt'],
        level=c['level'], advice=c['advice'], rest=c['rest'], gate=c['gate'],
        name=m['name'], dist=m['dist'], walk_min=round(m['dist'] / SPEED),
        total=m['total'], move=m['move'], stay=m['stay'], indoor=m['indoor'],
        acc=m['acc'], rank=rk, svg=svg,
        gap_ml=(rk[1]['total'] - rk[0]['total']) if len(rk) > 1 else None,
        gap_pct=(round((rk[1]['total'] - rk[0]['total']) / rk[0]['total'] * 100)
                 if len(rk) > 1 else None))


payload = {k: pack(c, SV[k]) for k, c in D['cases'].items()}
payload['outrange'] = dict(outrange=True, origin='地下鉄 雑司が谷駅',
                           sub='東京メトロ副都心線', svg=SV['outrange'])

CSS = r"""
:root{
 --surface:#fcfcfb; --plane:#f4f4f1; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --hair:#e1e0d9;
 --sun:#eb6834; --shade:#2a78d6; --deck:#4a3aa7; --park:#1baf7a;
 --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --crit:#d03b3b;
 --r:12px; --r-s:8px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--plane);color:var(--ink);
 font-family:system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;
 font-size:15px;line-height:1.65;text-wrap:pretty;
 font-feature-settings:"palt" 1}
b,strong{font-weight:700}
a{color:var(--shade)} a:hover{color:var(--ink)}
.num{font-variant-numeric:tabular-nums;letter-spacing:-.01em}

/* ---- 画面の器（390px基準・PCでは中央寄せ） ---- */
.screen{width:100%;max-width:390px;margin:0 auto;background:var(--surface)}
.slug{max-width:390px;margin:0 auto;padding:26px 18px 8px;font-size:11px;letter-spacing:.14em;
 font-weight:700;color:var(--muted);background:var(--plane)}
.slug:first-child{padding-top:14px}

/* ---- ヘッダ ---- */
.nav{position:sticky;top:0;z-index:5;background:rgba(252,252,251,.95);backdrop-filter:blur(8px);
 border-bottom:1px solid var(--hair);padding:11px 18px;display:flex;align-items:center;gap:10px}
.nav .logo{font-size:17px;font-weight:800;letter-spacing:.08em}
.nav .ctx{font-size:11.5px;color:var(--ink2);line-height:1.35}
.nav .back{margin-left:auto;font-size:12px;color:var(--ink2);border:1px solid var(--hair);
 border-radius:999px;padding:5px 11px;background:var(--surface);white-space:nowrap}
.pad{padding:20px 18px 28px}

/* ---- 画面1 入力 ---- */
.h2{font-size:26px;font-weight:800;line-height:1.35;letter-spacing:-.01em;margin:2px 0 12px}
.lede{font-size:13.5px;color:var(--ink2);margin:0 0 18px;line-height:1.75}
.lede b{color:var(--ink);font-weight:700}
.can{border:1px solid var(--hair);border-radius:var(--r);background:var(--plane);padding:14px 15px;margin-bottom:22px}
.can .t{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted);margin-bottom:10px}
.can ul{margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
.can li{list-style:none;display:flex;gap:10px;font-size:13px;line-height:1.6;align-items:flex-start}
.ic{flex:0 0 auto;width:18px;height:18px;border-radius:5px;margin-top:2px}
.grp{margin-bottom:20px}
.gl{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted);margin:0 0 9px}
.opts{display:flex;flex-direction:column;gap:8px}
.opts.h{flex-direction:row}
.opt{font-size:15px;padding:13px 15px;border:1px solid var(--hair);border-radius:var(--r);
 background:var(--surface);flex:1;line-height:1.35}
.opt small{display:block;font-size:11px;color:var(--muted);margin-top:2px}
.opt.on{background:var(--ink);color:var(--surface);font-weight:700;border-color:var(--ink)}
.opt.on small{color:rgba(252,252,251,.66)}
.opt.h{text-align:center;font-weight:700}
.go{width:100%;font-size:17px;font-weight:800;padding:16px;border:0;border-radius:var(--r);
 background:var(--park);color:#fff;letter-spacing:.04em;margin-top:6px;font-family:inherit}
.hint{font-size:11.5px;color:var(--muted);margin-top:12px;text-align:center;line-height:1.6}

/* ---- 画面2 結果 ---- */
.pre{font-size:12.5px;color:var(--ink2);margin:0 0 4px}
.nm{font-size:30px;font-weight:800;letter-spacing:-.015em;line-height:1.2;margin:0 0 5px}
.sub2{font-size:12.5px;color:var(--muted);margin:0 0 20px;line-height:1.6}

/* ★ 核心ブロック：ここだけ読んで意味が通ること */
.heat{border:2px solid var(--ink);border-radius:var(--r);background:var(--surface);padding:15px 16px 14px}
.heat .qq{font-size:14px;font-weight:800;color:var(--ink2);letter-spacing:.01em;margin-bottom:2px}
.heat .aa{margin:4px 0 0;line-height:1.1}
.heat .aa .u1{font-size:19px;font-weight:700;margin-right:2px}
.heat .aa em{font-style:normal;font-size:62px;font-weight:800;letter-spacing:-.03em}
.heat .aa .u2{font-size:24px;font-weight:800;margin-left:1px}
.heat .aa .tail{display:block;font-size:21px;font-weight:800;margin-top:2px;letter-spacing:.01em}
.bot{display:flex;align-items:flex-end;gap:13px;margin:14px 0 0;padding-top:13px;border-top:1px solid var(--hair)}
.bot .bs{display:flex;gap:6px;align-items:flex-end;flex:0 0 auto}
.btl{height:108px;width:auto;display:block}
.bot .cap{font-size:12.5px;line-height:1.65;color:var(--ink2);padding-bottom:3px}
.bot .cap b{display:block;font-size:15px;color:var(--ink);font-weight:800;line-height:1.4}
.bot .cap .u{font-size:10.5px;color:var(--muted);letter-spacing:.06em}
.heat .nb{margin:13px 0 0;padding-top:12px;border-top:1px solid var(--hair);
 display:flex;flex-direction:column;gap:6px;font-size:12px;line-height:1.7;color:var(--ink2)}
.heat .nb .k{color:var(--ink);font-weight:700}

.kv{display:flex;gap:8px;margin:12px 0 0}
.kv>div{flex:1;border:1px solid var(--hair);border-radius:var(--r-s);padding:10px 10px 9px;background:var(--surface);
 display:flex;flex-direction:column;justify-content:space-between}
.kv .k{font-size:10.5px;color:var(--muted);line-height:1.35;min-height:2.7em}
.kv .v{font-size:19px;font-weight:800;margin-top:2px}
.kv .v span{font-size:11px;font-weight:700;color:var(--ink2);margin-left:1px}

.race{display:flex;flex-direction:column;gap:7px}
.cand{border:1px solid var(--hair);border-radius:var(--r-s);padding:9px 11px 10px;background:var(--surface)}
.cand.pick{border:2px solid var(--ink);background:var(--plane);padding:8px 10px 9px}
.tag{display:inline-block;font-size:9.5px;font-weight:800;color:#fff;background:var(--park);
 border-radius:4px;padding:2px 7px;letter-spacing:.08em;margin-bottom:6px}
.ch{display:grid;grid-template-columns:2.2em 1fr auto;align-items:center;gap:0 7px}
.cand{display:grid;grid-template-columns:1fr 104px;grid-template-rows:auto auto auto auto auto;
 column-gap:10px;align-items:start;position:relative}
.tag{justify-self:start}
.cand .ch{grid-column:1;grid-row:2}
.cand .mt.r3{grid-column:1;grid-row:3}
.cand .blg2{grid-column:1;grid-row:4;display:flex;gap:11px;font-size:9.5px;color:var(--ink2);
 margin:2px 0 0;padding-left:57px}
.cand .blg2 span{display:flex;align-items:center;gap:4px}
.cand .blg2 i{width:11px;height:5px;border-radius:3px}
.cand .mt.r4{grid-column:1;grid-row:5;margin-top:10px}
.hm{grid-column:2;grid-row:2/span 4;align-self:end;text-align:center;padding-bottom:1px}
.hl{display:flex;align-items:center;justify-content:center;gap:3px;font-size:12px;font-weight:700;
 color:var(--ink2);white-space:nowrap}
.qm{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;
 border:1px solid var(--muted);border-radius:50%;font-size:9.5px;font-weight:700;color:var(--muted);line-height:1}
.wv{line-height:1;margin-top:5px;white-space:nowrap}
.wv .pfx{font-size:15px;font-weight:700}
.wv em{font-style:normal;font-size:33px;font-weight:800;letter-spacing:-.02em}
.wv .u{font-size:13px;font-weight:700;margin-left:1px}
.cand.pick .wv em{font-size:38px}
.cand.pick{margin-top:38px}
.tip{position:absolute;right:6px;top:-30px;width:206px;
 background:var(--ink);color:var(--surface);border-radius:6px;padding:9px 11px;
 font-size:11.5px;line-height:1.6;text-align:center;font-weight:600}
.tip::after{content:"";position:absolute;bottom:-34px;right:49px;width:0;height:0;
 border-left:7px solid transparent;border-right:7px solid transparent;border-top:35px solid var(--ink)}
.aad{font-size:12px;line-height:1.65;color:var(--ink2);margin:7px 0 0}
.ch .rk{font-size:10.5px;font-weight:700;color:var(--muted)}
.ch .nmx{font-size:14px;font-weight:700;line-height:1.3}
.cand.pick .ch .nmx{font-size:15.5px;font-weight:800}
.ch .m2{font-size:16px;font-weight:800;text-align:right;line-height:1.15}
.ch .m2 .pfx{font-size:10.5px;font-weight:700;color:var(--ink2);margin-right:1px}
.ch .m2 em{display:block;font-style:normal;font-size:9.5px;font-weight:700;
 color:var(--muted);letter-spacing:.02em;margin-top:2px}
.cand.pick .ch .m2{font-size:18px}
.ch .m2 span{font-size:10.5px;font-weight:700;color:var(--ink2);margin-left:1px}
.mt{display:grid;grid-template-columns:52px 1fr 40px;align-items:center;gap:0 5px;margin-top:5px}
.trw{display:block;height:7px;border-radius:4px;background:var(--hair)}
.tr2{display:flex;height:100%;border-radius:4px;overflow:hidden}
.tr2 i{display:block;height:100%}
.tr2 .s1{background:var(--sun)}
.tr2 .s2{background:var(--shade)}
.lead2{font-size:12px;line-height:1.7;color:var(--ink2);margin:0 0 9px}
.lead2 b{color:var(--ink);font-weight:700}
.blg{display:flex;gap:12px;font-size:10px;color:var(--ink2);margin:-3px 0 8px}
.blg span{display:flex;align-items:center;gap:4px}
.blg i{width:11px;height:5px;border-radius:3px}
.mt .ml{font-size:10px;color:var(--muted);font-weight:700}
.tr{height:7px;border-radius:4px;background:var(--hair);display:block;overflow:hidden}
.tr.na{background:transparent;border-bottom:1px dashed var(--hair)}
.tr i{display:block;height:100%;border-radius:4px;background:var(--ink2)}
.tr.sun{background:rgba(235,104,52,.25)}
.tr.sun i{background:var(--shade)}
.mt .mv{font-size:11px;font-weight:700;text-align:right;color:var(--ink2)}
.rh{font-size:19px;font-weight:800;letter-spacing:-.01em;margin:2px 0 8px}
.cmp{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted);margin:26px 0 9px}
.alt{display:grid;grid-template-columns:2.4em 1fr auto auto;align-items:center;gap:0 8px;
 border:1px solid var(--hair);border-radius:var(--r-s);padding:10px 11px;margin-bottom:7px;background:var(--surface)}
.alt .rk{font-size:10.5px;color:var(--muted);font-weight:700}
.alt .n2{font-size:14px;font-weight:700;line-height:1.3}
.alt .n2 small{display:block;font-size:10.5px;color:var(--muted);font-weight:400;margin-top:1px}
.alt .m2{font-size:17px;font-weight:800;text-align:right}
.alt .m2 span{font-size:10.5px;font-weight:700;color:var(--ink2);margin-left:1px}
.alt.self{border-color:var(--ink);background:var(--plane)}
.alt.self .rk{color:var(--park)}
.acc{font-size:9.5px;font-weight:700;border:1px solid var(--hair);border-radius:5px;
 padding:2px 5px;color:var(--ink2);background:var(--plane);white-space:nowrap}
.same{font-size:12.5px;line-height:1.7;color:var(--ink2);background:var(--plane);
 border-radius:var(--r-s);padding:11px 12px;margin:4px 0 0}
.same b{color:var(--ink)}

/* ---- 地図（720×540 のSVGが入る。比率4:3を維持） ---- */
.maphd{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted);margin:26px 0 9px}
.map{aspect-ratio:720/540;border:1px solid var(--hair);border-radius:var(--r);overflow:hidden;background:var(--surface)}
.map>svg{display:block;width:100%;height:auto}
.map:empty{background:repeating-linear-gradient(45deg,#f4f4f1,#f4f4f1 9px,#efeee9 9px,#efeee9 18px)}
.lgd{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:10.5px;color:var(--ink2);margin:9px 0 0}
.lgd span{display:flex;align-items:center;gap:5px;white-space:nowrap}
.lgd i{width:13px;height:3px;border-radius:2px;flex:0 0 auto}

.dis{font-size:11.5px;line-height:1.75;color:var(--ink2);background:var(--plane);
 border-radius:var(--r-s);padding:12px 13px;margin:24px 0 0}
.dis b{color:var(--ink)}
.dis ul{margin:0;padding-left:1.15em}
.dis li{margin:0 0 7px}
.dis li:last-child{margin:0}
details{margin-top:12px;border-top:1px solid var(--hair);padding-top:12px}
summary{font-size:13px;color:var(--ink2);cursor:pointer;list-style:none;padding:2px 0}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";color:var(--muted)}
details[open] summary::before{content:"▾ "}
details .in{font-size:12px;color:var(--ink2);line-height:1.8;padding:8px 0 0}
.op{background:#eceae4;border-top:1px dashed rgba(11,11,11,.2);padding:7px 18px;font-size:10.5px;color:var(--muted)}
.op code{background:var(--surface);border:1px solid var(--hair);border-radius:4px;padding:1px 5px}

.hyd{font-size:15px;font-weight:800;line-height:1.55;margin:16px 0 0}
.hyn{font-size:11.5px;line-height:1.75;color:var(--ink2);margin:5px 0 0}
.brk{display:flex;justify-content:center;gap:5px;font-size:9.5px;font-weight:700;
 color:var(--muted);margin-top:4px;white-space:nowrap;letter-spacing:-.01em}
.lvl{margin:16px 0 0;padding-top:13px;border-top:1px solid var(--hair);
 display:flex;flex-direction:column;gap:8px}
.lvlt{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted)}
.lvl .row{display:grid;grid-template-columns:auto 1fr;gap:0 8px;align-items:start;
 font-size:11px;line-height:1.7;color:var(--ink2)}
.lvl .acc{margin-top:2px}

/* ---- 画面3 ゲート ---- */
.gate .big{font-size:27px;font-weight:800;line-height:1.3;letter-spacing:-.015em;color:var(--crit);margin:2px 0 10px}
.gate .tx{font-size:13.5px;line-height:1.75;color:var(--ink2);margin:0 0 8px}
.gate .tx b{color:var(--ink)}
.src{font-size:11.5px;color:var(--muted);margin:0 0 24px;padding-bottom:22px;border-bottom:2px solid var(--hair)}
.heat.crit{border-color:var(--crit)}
.heat.crit .qq{color:var(--crit)}

/* ---- 実装で足したぶん（2026-08-15。デザインのパレット・寸法は変えていない） ---- */
.sc{display:none}
.sc.on{display:block}
.opt{cursor:pointer;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}
.go,.back{cursor:pointer}
.acc.l3{border-color:#f0dca8;background:#fff8e8;color:#8a6a12}
.nc{display:inline-block;font-size:9px;font-weight:700;line-height:1.5;color:#8a6a12;
 background:#fff8e8;border:1px solid #f0dca8;border-radius:4px;padding:0 4px;margin-left:5px;
 letter-spacing:.02em;vertical-align:1px}
.opt.on .nc{background:rgba(252,252,251,.16);border-color:rgba(252,252,251,.4);color:#ffe9b8}
.sub{background:#fff8e8;border:1px solid #f0dca8;border-radius:var(--r-s);
 padding:11px 12px;font-size:11.5px;line-height:1.8;color:var(--ink2);margin:0 0 16px}
.w28{margin:0 0 14px;padding:12px 14px;border-radius:10px;background:#fff4e5;border:1px solid #f0c48a;color:#6b4a1c;font-size:13px;line-height:1.7}
.w28s{display:block;margin-top:6px;font-size:11px;color:#8a6a3c}
.sub b{color:var(--ink)}
.op .nc{margin-left:0}
.seg{display:inline-flex;border:1px solid var(--hair);border-radius:6px;overflow:hidden;
 vertical-align:-3px;margin:0 4px}
.seg button{font:inherit;font-size:10.5px;color:var(--ink2);background:var(--surface);
 border:0;padding:3px 8px;cursor:pointer}
.seg button+button{border-left:1px solid var(--hair)}
.seg button[aria-pressed=true]{background:var(--ink);color:var(--surface);font-weight:700}
"""

JS = r"""
const D = __DATA__;
const S = {origin:'ikebukuro_east', hour:'14', place:'outdoor', play:'active',
           stay:'60', stroller:'no', bw:'15', wbgt:29};
const COMPUTED = __COMPUTED__, LABEL = __LABEL__, SUBST = __SUBST__;
const $ = s => document.querySelector(s);
const $$ = s => Array.prototype.slice.call(document.querySelectorAll(s));

function key(){
  if(S.origin === 'metro_zoshigaya') return 'outrange';
  if(S.wbgt === 31.5) return 'gate';
  return S.origin + '_' + (S.hour === '16' ? '14' : S.hour);
}
// v0 で事前計算していない選択肢を拾う。結果画面の先頭に「何を代用したか」を出すため。
function subs(){
  const out = [];
  for(const k in COMPUTED){
    if(COMPUTED[k].indexOf(S[k]) < 0)
      out.push({k:k, chose:(LABEL[S[k]] || S[k]), used:SUBST[k]});
  }
  return out;
}
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function bar(r, maxRound){
  const sun = r.round_m ? (r.sun_dist / r.round_m * 100) : 0;
  const rel = maxRound ? (r.round_m / maxRound * 100) : 0;
  return '<div class="mt r3"><span class="ml">往復距離</span><span class="trw">'
    + '<span class="tr2" style="width:' + rel.toFixed(1) + '%">'
    + '<i class="s1" style="width:' + sun.toFixed(1) + '%"></i>'
    + '<i class="s2" style="width:' + (100 - sun).toFixed(1) + '%"></i></span></span>'
    + '<span class="mv num">' + r.round_m + 'm</span></div>'
    + '<div class="blg2"><span><i style="background:var(--sun)"></i>日なた</span>'
    + '<span><i style="background:var(--shade)"></i>日陰</span></div>';
}
function card(r, i, maxRound){
  const pick = (i === 0);
  const acc = '<span class="acc' + (r.acc === 'L3' ? ' l3' : '') + '">' + r.acc + '</span>';
  const foot = r.indoor
    ? '<div class="mt r4"><span class="ml">遊ぶ場所</span><span class="tr na"></span><span class="mv">屋内</span></div>'
    : '<div class="mt r4"><span class="ml">公園の日陰</span><span class="tr sun">'
      + '<i style="width:' + Math.round(r.shade * 100) + '%"></i></span>'
      + '<span class="mv num">' + Math.round(r.shade * 100) + '%</span></div>';
  return '<div class="cand' + (pick ? ' pick' : '') + '">'
    + (pick ? '<span class="tag">今日はこれ</span><div class="tip">' + TIP + '</div>' : '')
    + '<div class="ch"><span class="rk">' + (i + 1) + '位</span>'
    + '<span class="nmx">' + esc(r.name) + '</span>' + acc + '</div>'
    + '<div class="hm"><div class="hl">暑さ目安</div>'
    + '<div class="wv num"><span class="pfx">水</span><em>' + r.total + '</em><span class="u">mL</span></div>'
    + '<div class="brk"><span>往復 ' + r.move + 'mL</span><span>遊び ' + r.stay + 'mL</span></div></div>'
    + bar(r, maxRound) + foot + '</div>';
}
function subsHTML(){
  const s = subs();
  if(!s.length) return '';
  return '<div class="sub"><b>v0 で事前に計算しているのは、下の条件だけです。</b><br>'
    + s.map(x => '選ばれた「' + esc(x.chose) + '」は未計算のため、<b>' + esc(x.used) + '</b> の結果を出しています。').join('<br>')
    + '</div>';
}
function resultHTML(c){
  const maxRound = Math.max.apply(null, c.rank.map(r => r.round_m));
  // ★ 差が小さいときだけ「ほとんど変わりません」と言う。
  //   2026-08-15：歩行速度を実測値にしたら差が 8mL(1%) → 29mL(4%) に広がり、
  //   文言を固定していたせいで「29mL（4%）。ほとんど変わりません」と出ていた。
  const same = (c.gap_ml === null) ? ''
    : (c.gap_pct <= 2)
      ? '<p class="same">2位との差は <b>' + c.gap_ml + 'mL（' + c.gap_pct + '%）</b>。ほとんど変わりません。</p>'
      : '<p class="same">2位より <b>' + c.gap_ml + 'mL（' + c.gap_pct + '%）</b> 少なくてすみます。</p>';
  // ★ 2026-08-17：WBGT 28〜31 は「幼児にはひとつ上の区分」の帯（tasks.md §5-4・案A）
  const warn = (c.wbgt >= 28 && c.wbgt < 31)
    ? '<div class="w28">' + WARN28 + '<span class="w28s">' + WARN28_SRC + '</span></div>' : '';
  return warn
    + subsHTML()
    + '<h2 class="rh">おすすめの遊び場</h2>'
    + '<div class="race">' + c.rank.map((r, i) => card(r, i, maxRound)).join('') + '</div>'
    + same
    + (c.rest ? '<p class="hyd">' + c.rest + '分ごとを目安に給水しましょう</p>' : '')
    + '<p class="hyn">' + DISC + '</p>'
    + '<div class="nm" style="margin-top:30px">' + esc(c.name) + '<br>へのおすすめルート</div>'
    + '<div class="sub2">片道 <span class="num">' + c.dist + '</span>m（徒歩<span class="num">'
      + c.walk_min + '</span>分）</div>'
    + '<div class="map">' + c.svg + '</div>'
    + '<div class="lgd">'
    + '<span><i style="background:var(--sun)"></i>日なたが半分以上</span>'
    + '<span><i style="background:var(--shade)"></i>日陰が半分以上</span>'
    + '<span><i style="background:#98a0a8"></i>建物の影</span>'
    + '<span><i style="background:var(--deck)"></i>高架の影</span>'
    + '<span><i style="background:var(--muted)"></i>概算（破線）</span></div>'
    + '<div class="lvl">' + LVL + '</div>'
    + '<div class="dis">' + DIS + '</div>'
    + '<details><summary>計算の内訳</summary><div class="in">往復 ' + c.move
      + 'mL ＋ 滞在60分 ' + c.stay + 'mL ＝ ' + c.total + 'mL<br>'
      + '徒歩の分数は ' + SPEED + 'm/分 で計算しています</div></details>';
}
function gateHTML(c){
  const maxRound = Math.max.apply(null, c.rank.map(r => r.round_m));
  return '<p class="big">今日は、外に出ない方が<br>いいです</p>'
    + '<p class="tx">WBGT <span class="num">' + c.wbgt + '</span>（<b>' + esc(c.level)
      + '</b>）。日本スポーツ協会の熱中症予防運動指針は「' + esc(c.advice) + '」としています。</p>'
    + '<p class="src">' + GATE_SRC + '</p>'
    + subsHTML()
    + '<p class="pre">どうしても出かけるなら、屋内で</p>'
    + '<h2 class="rh">おすすめの遊び場</h2>'
    + '<div class="race">' + c.rank.map((r, i) => card(r, i, maxRound)).join('') + '</div>'
    + '<p class="hyn">' + DISC + '</p>'
    + '<div class="nm" style="margin-top:30px">' + esc(c.name) + '</div>'
    + '<div class="sub2">片道 <span class="num">' + c.dist + '</span>m（徒歩<span class="num">'
      + c.walk_min + '</span>分）　屋内</div>'
    + '<div class="lvl">' + LVL + '</div>'
    + '<div class="dis">' + DIS + '</div>'
    + '<details><summary>計算の内訳</summary><div class="in">往復 ' + c.move
      + 'mL ＋ 滞在60分 ' + c.stay + 'mL ＝ ' + c.total + 'mL<br>'
      + '徒歩の分数は ' + SPEED + 'm/分 で計算しています<br>'
      + '屋内の暑さ指数は WBGT 25.0 の定数（建築物環境衛生管理基準 28℃/70% の理論上限）を'
      + '置いています。実測ではありません</div></details>';
}
function outrangeHTML(c){
  return '<p class="big" style="color:var(--ink)">この出発地では<br>答えを出せません</p>'
    + '<p class="tx">歩行空間ネットワークに収録された最寄りの地点まで <b>442m</b> あります。'
    + '<b>歩いて3分の雑司が谷公園にも答えられません。</b>その公園から歩行空間ネットワークまでは'
    + ' 628m あり、直線距離での概算（精度L3）の上限 400m も超えています。</p>'
    + '<div class="lvl"><div class="lvlt">なぜ</div>'
    + '<div class="row"><span class="acc">範囲</span><span>歩行空間ネットワークは'
      + '<b>都内17地区でしか整備されていません</b>。仕様書にも「優先的に整備対象とすることができる／'
      + '段階的に進めることができる」と書かれています</span></div>'
    + '<div class="row"><span class="acc">近さ</span><span><b>都電雑司ヶ谷駅は、収録範囲まで8m。</b>'
      + '2つの駅は463mしか離れていません</span></div>'
    + '<div class="row"><span class="acc">対策</span><span>OpenStreetMap の歩道データを重ねれば'
      + '23区に広げられます（ODbL・帰属表示が必要）</span></div></div>'
    + '<div class="map" style="margin-top:18px">' + c.svg + '</div>'
    + '<div class="lgd">'
    + '<span><i style="background:var(--shade)"></i>歩行空間ネットワークの収録範囲</span>'
    + '<span><i style="background:var(--good)"></i>範囲の中</span>'
    + '<span><i style="background:var(--crit)"></i>範囲の外</span></div>'
    + '<p class="hyn" style="margin-top:16px">これは不具合ではなく、'
      + '<b>いま公開されているデータの範囲そのもの</b>です。こかげはこれを隠さずに出します。</p>';
}
function show(id){
  $$('.sc').forEach(e => e.classList.toggle('on', e.id === id));
  window.scrollTo(0, 0);
}
function render(){
  const c = D[key()];
  const hourTxt = (S.hour === '16' ? '14:00' : S.hour + ':00');
  $('#ctx').innerHTML = esc(c.origin) + ' から<br>' + (c.outrange ? '' : hourTxt + ' に出発');
  const pad = $('#pad2');
  pad.className = 'pad' + ((c.gate || c.outrange) ? ' gate' : '');
  pad.innerHTML = c.outrange ? outrangeHTML(c) : (c.gate ? gateHTML(c) : resultHTML(c));
  $$('#wbgtsel button').forEach(b => b.setAttribute('aria-pressed', b.dataset.wbgt === String(S.wbgt)));
}
document.addEventListener('DOMContentLoaded', function(){
  if(/[?&]wbgt=31\.5/.test(location.search)) S.wbgt = 31.5;
  $$('.opt').forEach(function(b){
    b.addEventListener('click', function(){
      const g = b.dataset.g;
      $$('.opt[data-g="' + g + '"]').forEach(x => x.classList.toggle('on', x === b));
      S[g] = b.dataset.v;
    });
  });
  $$('#wbgtsel button').forEach(function(b){
    b.addEventListener('click', function(){ S.wbgt = +b.dataset.wbgt; render(); });
  });
  $('#go').addEventListener('click', function(){ render(); show('s2'); });
  $('#back').addEventListener('click', function(){ show('s1'); });
  render();
});
"""

HTML = r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>こかげ v0.1 — 今日、どこへ連れて行くか（ヒアリング用・スマホ）</title>
<style>__CSS__</style></head><body>

<!-- ==================== 画面1／入力 ==================== -->
<div class="screen sc on" id="s1">
 <div class="nav">
  <span class="logo">こかげ</span>
  <span class="ctx">夏の午後、3〜5歳を<br>どこで遊ばせるか</span>
 </div>
 <div class="pad">
  <h1 class="h2">今日のおすすめ遊び場</h1>
  <p class="lede">3〜5歳を連れて外に出るとき、<b>どこがいちばん楽か</b>を1つだけ答えます。</p>

  <div class="can">
   <div class="t">わかること</div>
   <ul>
    <li><span class="ic" style="background:var(--park);opacity:.55"></span>
     <span><b>おすすめの遊び場</b>。日陰が多くて<b>涼しい公園</b>や、日陰を通って行きやすい場所を見つけます</span></li>
    <li><span class="ic" style="background:linear-gradient(90deg,var(--sun) 50%,var(--shade) 50%)"></span>
     <span><b>おすすめルート</b>。どの道を選ぶかはもちろん、<b>どちら側の歩道を歩くか</b>だけでも、暑い日なたにいる時間が変わります</span></li>
   </ul>
  </div>

  <div class="grp">
   <div class="gl">どこから出ますか</div>
   <div class="opts">
    <span class="opt on" data-g="origin" data-v="ikebukuro_east">池袋駅東口<small>JR・私鉄・地下鉄</small></span>
    <span class="opt" data-g="origin" data-v="toden_zoshigaya">都電雑司ヶ谷駅<small>都電荒川線</small></span>
    <span class="opt" data-g="origin" data-v="metro_zoshigaya">地下鉄 雑司が谷駅<small>東京メトロ副都心線</small></span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">何時に出ますか</div>
   <div class="opts h">
    <span class="opt h" data-g="hour" data-v="12">12:00</span>
    <span class="opt h on" data-g="hour" data-v="14">14:00</span>
    <span class="opt h" data-g="hour" data-v="16">16:00<span class="nc">未計算</span></span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">どこで遊びますか</div>
   <div class="opts h">
    <span class="opt h" data-g="place" data-v="indoor">屋内<span class="nc">未計算</span></span>
    <span class="opt h on" data-g="place" data-v="outdoor">屋外</span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">遊び方<span style="font-weight:400;letter-spacing:0;margin-left:7px">屋外のときだけ</span></div>
   <div class="opts h">
    <span class="opt h on" data-g="play" data-v="active">走り回る<br>中心</span>
    <span class="opt h" data-g="play" data-v="half">半々<span class="nc">未計算</span></span>
    <span class="opt h" data-g="play" data-v="sit">座って遊ぶ<br>中心<small>砂場など</small><span class="nc">未計算</span></span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">滞在時間</div>
   <div class="opts h">
    <span class="opt h" data-g="stay" data-v="30">30分<span class="nc">未計算</span></span>
    <span class="opt h on" data-g="stay" data-v="60">60分</span>
    <span class="opt h" data-g="stay" data-v="90">90分<span class="nc">未計算</span></span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">ベビーカー</div>
   <div class="opts h">
    <span class="opt h on" data-g="stroller" data-v="no">なし</span>
    <span class="opt h" data-g="stroller" data-v="yes">あり<span class="nc">未計算</span></span>
   </div>
  </div>

  <div class="grp">
   <div class="gl">お子様の体重</div>
   <div class="opts h">
    <span class="opt h" data-g="bw" data-v="12kg">12 kg<span class="nc">未計算</span></span>
    <span class="opt h on" data-g="bw" data-v="15">15 kg</span>
    <span class="opt h" data-g="bw" data-v="18kg">18 kg<span class="nc">未計算</span></span>
    <span class="opt h" data-g="bw" data-v="22kg">22 kg<span class="nc">未計算</span></span>
   </div>
  </div>

  <button class="go" id="go">行き先を出す</button>
  <div class="hint">今日の暑さ（WBGT）は環境省の観測値を自動で使います</div>
 </div>
 <div class="op"><b>実施者用</b>　v0で事前計算しているのは <code>出発地3 × 12:00/14:00</code> と
  <code>WBGT 31.5</code> のゲートだけです。<span class="nc">未計算</span> の選択肢も押せますが、
  結果は代用値になります。</div>
</div>

<!-- ==================== 画面2／結果・ゲート・収録範囲外 ==================== -->
<div class="screen sc" id="s2">
 <div class="nav">
  <span class="logo">こかげ</span>
  <span class="ctx" id="ctx"></span>
  <span class="back" id="back">← 変える</span>
 </div>
 <div class="pad" id="pad2"></div>
 <div class="op"><b>実施者用</b>　今日の暑さ
  <span class="seg" id="wbgtsel"><button data-wbgt="29" aria-pressed="true">WBGT 29</button><button
   data-wbgt="31.5" aria-pressed="false">31.5</button></span>
  　URL で切替：<code>?wbgt=31.5</code></div>
</div>

<script>__JS__</script></body></html>"""

js = (JS.replace('__DATA__', json.dumps(payload, ensure_ascii=False))
        .replace('__COMPUTED__', json.dumps(COMPUTED, ensure_ascii=False))
        .replace('__LABEL__', json.dumps(LABEL, ensure_ascii=False))
        .replace('__SUBST__', json.dumps(SUBST, ensure_ascii=False)))
js = ('const SPEED = ' + json.dumps(SPEED) + ';\n'
      + 'const TIP = ' + json.dumps(TIP, ensure_ascii=False) + ';\n'
      + 'const DISC = ' + json.dumps(DISC, ensure_ascii=False) + ';\n'
      + 'const DIS = ' + json.dumps(DIS_HTML, ensure_ascii=False) + ';\n'
      + 'const LVL = ' + json.dumps(LVL_HTML, ensure_ascii=False) + ';\n'
      + 'const GATE_SRC = ' + json.dumps(GATE_SRC, ensure_ascii=False) + ';\n'
      + 'const WARN28 = ' + json.dumps(WARN28, ensure_ascii=False) + ';\n'
      + 'const WARN28_SRC = ' + json.dumps(WARN28_SRC, ensure_ascii=False) + ';\n' + js)

out = HTML.replace('__CSS__', CSS).replace('__JS__', js)
for p in (paths.build('kokage-v0-mobile.html'),
          paths.pages('kokage-v0-mobile.html')):
    open(p, 'w', encoding='utf-8').write(out)
print('written', len(out) // 1024, 'KB ×2 (build/ と pages/)')
