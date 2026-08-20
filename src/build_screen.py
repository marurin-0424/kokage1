# -*- coding: utf-8 -*-
"""こかげ v0（ヒアリング用）：単一HTMLを組み立てる。
CSS・JS・SVG をすべてインラインにする（spec.md §5-3 の静的配信方針）。
"""
import paths
import json, html

D = json.load(open(paths.out('screen_cases.json')))
SV = json.load(open(paths.cache('screen_svgs.json')))

STATUS = {'ほぼ安全': '#0ca30c', '注意': '#0ca30c', '警戒': '#fab219',
          '厳重警戒': '#ec835a', '危険': '#d03b3b'}

DISCLAIMER = ('これは公開データからの<b>推定値</b>です。医学的な判断ではありません。'
              'お子様の様子を見て、のどの渇きに応じて自由に飲めるようにしてください。')

payload = {}
for k, c in D['cases'].items():
    m = c['main']
    payload[k] = dict(
        origin=c['origin_label'], sub=c['origin_sub'], hour=c['hour'], wbgt=c['wbgt'],
        level=c['level'], advice=c['advice'], rest=c['rest'], gate=c['gate'],
        alt_deg=c['alt_deg'], name=m['name'], total=m['total'], move=m['move'],
        stay=m['stay'], dist=m['dist'], shade=m['shade'], sun_min=m['sun_min'],
        minutes=m['minutes'], acc=m['acc'], gap=m['gap'], indoor=m['indoor'],
        alt=c['alt'], ranking=c['ranking'], n_park=c['n_park'], n_l1=c['n_l1'],
        n_cand=c['n_cand'], reach=c['reach'], excluded=c.get('excluded', []),
        n_luse=c.get('n_luse', 0), svg=SV[k])
payload['outrange'] = dict(outrange=True, origin='地下鉄 雑司が谷駅', sub='東京メトロ副都心線',
                           svg=SV['outrange'])

CSS = """
:root{
  --surface:#fcfcfb; --plane:#f4f4f1; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --hair:#e1e0d9; --ring:rgba(11,11,11,.10);
  --sun:#eb6834; --shade:#2a78d6; --deck:#4a3aa7; --park:#1baf7a;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--plane);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif;
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.app{width:1600px;height:900px;margin:0 auto;background:var(--surface);display:flex;
  flex-direction:column;overflow:hidden;box-shadow:0 1px 3px var(--ring)}
@media(max-width:1620px){.app{width:100%;height:auto;min-height:100vh}}

header{display:flex;align-items:center;gap:20px;padding:14px 28px;border-bottom:1px solid var(--hair);flex:0 0 auto}
.logo{font-size:23px;font-weight:800;letter-spacing:.06em}
.tag{font-size:13.5px;color:var(--ink2)}
.spacer{flex:1}
.ctrl{display:flex;align-items:center;gap:8px}
.ctrl label{font-size:12px;color:var(--muted)}
select,.seg button{font:inherit;font-size:14px;color:var(--ink);background:var(--surface);
  border:1px solid var(--ring);border-radius:8px;padding:7px 11px;cursor:pointer}
.seg{display:flex;border:1px solid var(--ring);border-radius:8px;overflow:hidden}
.seg button{border:0;border-radius:0;padding:7px 15px}
.seg button+button{border-left:1px solid var(--hair)}
.seg button[aria-pressed=true]{background:var(--ink);color:#fff;font-weight:700}

main{flex:1;display:grid;grid-template-columns:640px 1fr;min-height:0}
.answer{padding:22px 28px 16px;overflow:auto;border-right:1px solid var(--hair)}
.mapwrap{padding:16px 22px;display:flex;flex-direction:column;min-height:0;background:var(--surface)}

.eyebrow{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--ink2);margin-bottom:14px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--ring);border-radius:999px;
  padding:3px 11px;font-size:12.5px;background:var(--surface)}
.dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.lead{font-size:14px;color:var(--ink2);margin:0 0 2px}
h1{font-size:35px;line-height:1.2;margin:0 0 12px;letter-spacing:.01em}
.hero{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.hero .n{font-size:66px;font-weight:800;line-height:1;letter-spacing:-.02em}
.hero .u{font-size:26px;font-weight:700}
.hero .c{font-size:14.5px;color:var(--ink2)}
.disc{font-size:14.5px;line-height:1.5;color:var(--ink2);background:var(--plane);
  border-left:3px solid var(--muted);padding:8px 13px;border-radius:0 8px 8px 0;margin:9px 0 15px}
.disc b{color:var(--ink)}

.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}
.tile{border:1px solid var(--hair);border-radius:10px;padding:11px 13px;background:var(--surface)}
.tile .k{font-size:12px;color:var(--muted);margin-bottom:3px}
.tile .v{font-size:25px;font-weight:700;line-height:1.15}
.tile .s{font-size:12px;color:var(--ink2)}
.tile .v small{font-size:14px;font-weight:600;margin-left:2px}

.rows{border-top:1px solid var(--hair)}
.row{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--hair);font-size:14.5px}
.row .k{color:var(--muted);flex:0 0 132px;font-size:13px}
.row .v{flex:1}
.note{font-size:13px;color:var(--ink2);margin-top:12px}
details{margin-top:14px;border:1px solid var(--hair);border-radius:10px;padding:0 14px}
summary{cursor:pointer;padding:11px 0;font-size:14px;font-weight:700;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"＋ ";color:var(--muted)}
details[open] summary::before{content:"− "}
table{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:12px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--hair)}
th{color:var(--muted);font-weight:600;font-size:12px}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.cond{display:flex;flex-wrap:wrap;gap:5px;margin-top:14px;padding-top:12px;border-top:1px solid var(--hair)}
.cond .chip{font-size:11.5px;padding:2px 9px;color:var(--ink2)}
.cond .chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}

.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:12.5px;color:var(--ink2);margin:10px 2px 6px}
.legend i{display:inline-block;width:18px;height:4px;border-radius:2px;margin-right:6px;vertical-align:middle}
.legend .sw{display:inline-block;width:13px;height:13px;border-radius:3px;margin-right:6px;vertical-align:-2px}
.src{font-size:11px;color:var(--muted);margin-top:auto;padding-top:8px;line-height:1.5}
.mapbox{border:1px solid var(--hair);border-radius:12px;overflow:hidden;min-height:0}
.gate{background:#fff4f0;border:1px solid #f3c3ae;border-radius:12px;padding:12px 16px;margin-bottom:10px}
.gate .t{font-size:20px;font-weight:800;color:#a82a2a;margin-bottom:2px}
.warn{background:#fff8e8;border:1px solid #f0dca8;border-radius:10px;padding:11px 14px;font-size:14px;margin:12px 0}
"""

JS = """
const D = __DATA__;
let origin='ikebukuro_east', hour=14, wbgt=29;
const $=s=>document.querySelector(s);
function key(){ if(origin==='metro_zoshigaya') return 'outrange';
  if(wbgt===31.5) return 'gate'; return origin+'_'+hour; }
function pct(x){ return Math.round(x*100)+'%'; }
function render(){
  const c=D[key()];
  $('#map').innerHTML=c.svg;
  const a=$('#answer');
  document.querySelectorAll('#hoursel button').forEach(b=>b.setAttribute('aria-pressed', b.dataset.hour==String(hour)));
  document.querySelectorAll('#wbgtsel button').forEach(b=>b.setAttribute('aria-pressed', b.dataset.wbgt==String(wbgt)));
  const out = origin==='metro_zoshigaya';
  $('#hoursel').style.visibility = out?'hidden':'visible';
  $('#wbgtsel').style.visibility = out?'hidden':'visible';
  if(c.outrange){ a.innerHTML=outrangeHTML(c); $('#legend').innerHTML=legendOut(); return; }
  a.innerHTML=answerHTML(c); $('#legend').innerHTML=legendMap();
}
function answerHTML(c){
  const col={'ほぼ安全':'#0ca30c','注意':'#0ca30c','警戒':'#fab219','厳重警戒':'#ec835a','危険':'#d03b3b'}[c.level]||'#898781';
  const acc = c.acc==='L1'
    ? '<span class="chip">精度 L1 ／ 実際の歩道をたどった経路</span>'
    : '<span class="chip" style="border-color:#f0dca8;background:#fff8e8">精度 L3 ／ 最後の'+c.gap+'mは直線距離からの概算</span>';
  return `
  <div class="eyebrow">
    <span class="chip"><span class="dot" style="background:${col}"></span>WBGT ${c.wbgt}（${c.level}）</span>
    <span class="chip">8月12日 ${c.hour}:00 ／ 太陽高度 ${c.alt_deg}°</span>
    <span class="chip">${c.origin} から</span>
  </div>
  ${c.gate?`<div class="gate"><div class="t">今日は、外に出ない方がいいです</div>
     <div style="font-size:14.5px;color:#52514e">${c.advice}（日本スポーツ協会「熱中症予防運動指針」）</div></div>
     <p class="note" style="margin:-6px 0 12px">v0では、この暑さの日は<b>都電雑司ヶ谷駅・14:00</b>の1ケースだけ事前計算しています。</p>
     <p class="lead">屋内にするなら</p>`:'<p class="lead">今日、この時間に連れて行くなら</p>'}
  <h1>${c.name}</h1>
  <div class="hero"><span class="n">${c.total}</span><span class="u">mL</span>
    <span class="c">この子が、行って・遊んで・帰るまでに<br>飲むことになる見込みの量です</span></div>
  <div class="disc">__DISC__</div>
  <div class="tiles">
    <div class="tile"><div class="k">片道</div><div class="v">${c.dist}<small>m</small></div><div class="s">往復＋滞在 ${Math.round(c.minutes)}分</div></div>
    <div class="tile"><div class="k">行き帰り</div><div class="v">${c.move}<small>mL</small></div><div class="s">日なたにいる時間 ${Math.round(c.sun_min)}分</div></div>
    <div class="tile"><div class="k">滞在60分</div><div class="v">${c.stay}<small>mL</small></div><div class="s">${c.indoor?'屋内':'日陰率 '+pct(c.shade)}</div></div>
  </div>
  <div class="rows">
    <div class="row"><div class="k">給水のタイミング</div><div class="v">${c.rest?`<b>${c.rest}分ごと</b>を目安に、こまめに`:'休憩をこまめに'}</div></div>
    ${c.alt?`<div class="row"><div class="k">だめなら屋内</div><div class="v">${c.alt.name}（合計 ${c.alt.total}mL）</div></div>`:''}
    <div class="row"><div class="k">この答えの精度</div><div class="v">${acc}</div></div>
  </div>
  <details><summary>計算の内訳と、比べた行き先</summary>
    <table><thead><tr><th>行き先</th><th class="num">片道</th><th class="num">日陰率</th><th class="num">合計</th><th>精度</th></tr></thead><tbody>
    ${c.ranking.map((r,i)=>`<tr${i===0?' style="font-weight:700"':''}><td>${r.name}</td><td class="num">${r.dist}m</td><td class="num">${pct(r.shade)}</td><td class="num">${r.total}mL</td><td>${r.acc}</td></tr>`).join('')}
    </tbody></table>
    <p class="note">歩ける範囲のノード ${c.reach}点／比べた候補 ${c.n_cand}件（公園 ${c.n_park}件のうち ${c.n_l1}件は実経路）。
    水分量は WBGT・活動強度（METs）・体重15kg・日なた/日陰の別から積み上げています。</p>
    ${(c.excluded&&c.excluded.length)?`<p class="note" style="border-left:3px solid #d03b3b;padding-left:10px">
    <b>日陰を計算できなかった公園が ${c.excluded.length}件あります。</b>
    ${c.excluded.map(e=>`${e.name}（${e.reason}）`).join('・')}。</p>`:''}
    <p class="note" style="border-left:3px solid #1baf7a;padding-left:10px">
    <b>公園の形は、3D都市モデルの土地利用「公共空地」から取っています</b>（${c.n_luse}件）。
    豊島区の公園データ自体は<b>「点」と「面積」だけで、形がありません</b>。
    2026-08-13に山吹の里公園・高田一丁目児童遊園で実物と照合し、形が合うことを確認しました。</p>
    <p class="note" style="border-left:3px solid #fab219;padding-left:10px">
    <b>★ サンシャインシティは、3D都市モデルでは「底面30,255㎡・高さ234.1mの1つの箱」</b>として
    入っています。実際は低層部と高層タワーに分かれるので、<b>その周りの日陰は多めに出ます</b>。
    東池袋中央公園の日陰率は、この箱の高さを60mに下げると 61.8%→45.4% になります。</p>
  </details>
  <div class="cond">
    <span class="chip on">外で遊ばせたい</span><span class="chip">涼みたい</span><span class="chip">授乳・おむつ替え</span>
    <span class="chip">滞在 60分</span><span class="chip">ベビーカー なし</span><span class="chip">体重 15kg</span>
  </div>`;
}
function outrangeHTML(c){
  return `
  <div class="eyebrow"><span class="chip"><span class="dot" style="background:#d03b3b"></span>収録範囲の外</span>
  <span class="chip">${c.origin} から</span></div>
  <p class="lead">この出発地では</p>
  <h1>答えを出せません</h1>
  <div class="hero"><span class="n">442</span><span class="u">m</span>
    <span class="c">歩行空間ネットワークに<br>収録された最寄りの地点まで</span></div>
  <div class="warn"><b>歩いて3分の雑司が谷公園にも、答えられません。</b>
  その公園から歩行空間ネットワークまでは 628m あり、直線距離での概算（精度L3）の上限 400m も超えています。</div>
  <div class="rows">
    <div class="row"><div class="k">なぜ</div><div class="v">歩行空間ネットワークは<b>都内17地区でしか整備されていません</b>。仕様書にも「優先的に整備対象とすることができる／段階的に進めることができる」と書かれています</div></div>
    <div class="row"><div class="k">同じ町なのに</div><div class="v"><b>都電雑司ヶ谷駅は、収録範囲まで8m。</b>2つの駅は463mしか離れていません</div></div>
    <div class="row"><div class="k">どうすれば</div><div class="v">OpenStreetMap の歩道データを重ねれば23区に広げられます（ODbL・帰属表示が必要）</div></div>
  </div>
  <p class="note">これは不具合ではなく、<b>いま公開されているデータの範囲そのもの</b>です。こかげはこれを隠さずに出します。</p>`;
}
function legendMap(){ return `
  <span><i style="background:#eb6834"></i>経路：日なたが半分以上</span>
  <span><i style="background:#2a78d6"></i>経路：日陰が半分以上</span>
  <span><span class="sw" style="background:#b9b8b0"></span>建物の影</span>
  <span><span class="sw" style="background:#4a3aa7;opacity:.45"></span>高架の影・高架の下</span>
  <span><span class="sw" style="background:#1baf7a;opacity:.3;border:1px solid #1baf7a"></span>行き先</span>
  <span><i style="background:#898781"></i>直線距離での概算（L3）</span>`; }
function legendOut(){ return `
  <span><span class="sw" style="background:#2a78d6;opacity:.25;border:1px dashed #2a78d6"></span>歩行空間ネットワークの収録範囲</span>
  <span><span class="sw" style="background:#0ca30c;border-radius:50%"></span>範囲の中</span>
  <span><span class="sw" style="background:#d03b3b;border-radius:50%"></span>範囲の外</span>`; }
document.addEventListener('DOMContentLoaded',()=>{
  $('#origin').addEventListener('change',e=>{origin=e.target.value;render();});
  document.querySelectorAll('#hoursel button').forEach(b=>b.addEventListener('click',()=>{hour=+b.dataset.hour;wbgt=29;render();}));
  document.querySelectorAll('#wbgtsel button').forEach(b=>b.addEventListener('click',()=>{
    wbgt=+b.dataset.wbgt;
    if(wbgt===31.5){origin='toden_zoshigaya';hour=14;$('#origin').value=origin;}
    render();}));
  render();
});
"""

HTML = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<title>こかげ — 今日、どこへ連れて行くか（v0 ヒアリング用）</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>__CSS__</style></head>
<body><div class="app">
<header>
  <span class="logo">こかげ</span>
  <span class="tag">夏の午後、3〜5歳を連れてどこで遊ばせるかを、1つだけ答えます</span>
  <span class="spacer"></span>
  <span class="ctrl"><label for="origin">出発地</label>
    <select id="origin">
      <option value="ikebukuro_east">池袋駅東口</option>
      <option value="toden_zoshigaya">都電雑司ヶ谷駅</option>
      <option value="metro_zoshigaya">地下鉄 雑司が谷駅</option>
    </select></span>
  <span class="ctrl" id="hoursel"><label>出発時刻</label>
    <span class="seg"><button data-hour="12" aria-pressed="false">12:00</button>
    <button data-hour="14" aria-pressed="true">14:00</button></span></span>
  <span class="ctrl" id="wbgtsel"><label>今日の暑さ</label>
    <span class="seg"><button data-wbgt="29" aria-pressed="true">WBGT 29</button>
    <button data-wbgt="31.5" aria-pressed="false">31.5</button></span></span>
</header>
<main>
  <section class="answer" id="answer"></section>
  <section class="mapwrap">
    <div class="mapbox" id="map"></div>
    <div class="legend" id="legend"></div>
    <p class="src">データ：東京都3Dデジタルマップ（PLATEAU仕様）豊島区2025 建築物・橋梁（東京都／CC BY 4.0）／
      歩行空間ネットワークデータ 池袋駅周辺（国土交通省／公共データ利用規約（第1.0版））／
      豊島区 公共施設一覧・都市公園（豊島区）／暑さ指数WBGT（環境省）。
      日影は 2026-08-12 の太陽位置による計算値です。<b>v0（ヒアリング用）— 入力6つのうち、出発地と時刻だけが動きます。</b></p>
  </section>
</main>
</div>
<script>__JS__</script></body></html>"""

out = (HTML.replace('__CSS__', CSS)
       .replace('__JS__', JS.replace('__DATA__', json.dumps(payload, ensure_ascii=False))
                .replace('__DISC__', DISCLAIMER)))
open(paths.build('kokage-v0.html'), 'w', encoding='utf-8').write(out)
print('written', len(out) // 1024, 'KB')
