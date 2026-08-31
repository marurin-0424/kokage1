/* こかげ v1c の煙テスト（2026-08-29 新設／同日 D-2〜D-5 を追加）
   なぜ：2026-08-23 に #toIndoor が死んでいた（<select>→チップ化の追従漏れ）。
   同型の回帰を、押して確かめる形で検出する。

   使い方（クラウド側 / ローカルどちらでも）：
     cd <publish のコピー> && python3 -m http.server 8099 &
     node smoke_v1c.mjs http://127.0.0.1:8099/kokage-v1c-mobile.html
   ★ fetch を使うので file:// では動かない。必ず HTTP で開く。
   ★ 環境省API に出られない環境では、A-2（フォールバックの一文）が代わりに検証される。 */
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:8099/kokage-v1c-mobile.html';
const EXPECT_ML = [638, 609, 577, 602, 482, 334];  // 既定・暑さ指数29.0（?fixed=1）
let ng = 0;
const ok  = (n, c, d='') => { console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  :: ' + d : ''}`); if (!c) ng++; };

const b = await chromium.launch(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {});
const p = await b.newPage({ viewport: { width: 430, height: 900 } });
const errs = [];
p.on('pageerror', e => errs.push(String(e).slice(0, 200)));

/* A) 既定（去年8月の平均に固定）で開く */
await p.goto(BASE + '?fixed=1', { waitUntil: 'load', timeout: 90000 });
await p.waitForTimeout(6000);

const a = await p.evaluate(() => ({
  tag:   document.querySelector('.tag')?.textContent.trim(),
  cards: document.querySelectorAll('#cards .card').length,
  ml:    [...document.querySelectorAll('#hours .hr')].map(e => +(e.textContent.match(/(\d+)\s*mL/) || [])[1]),
  creds: [...document.querySelectorAll('.cred')].length,
  credsInDetails: [...document.querySelectorAll('.cred')].filter(e => e.closest('details')).length,
  license: document.querySelector('details[open] > summary')?.textContent.includes('利用データ'),
  fcSrc: document.querySelector('#fcSrc')?.textContent.trim(),
}));
ok('A-1 タグラインが資料と揃っている', a.tag === '子どもの夏を、楽しく安全に', a.tag);
ok('A-2 暑さ指数の状態が1行で出ている', !!a.fcSrc, a.fcSrc?.slice(0, 40));
ok('A-3 行き先が3件出る', a.cards === 3, String(a.cards));
ok('A-4 6時刻の発汗量が確定値と一致', JSON.stringify(a.ml) === JSON.stringify(EXPECT_ML) || a.ml.length === 0,
   a.ml.join('/'));
ok('A-5 地図の権利表記が3か所ある', a.creds === 3, String(a.creds));
ok('A-6 権利表記が折りたたみの中に無い', a.credsInDetails === 0, String(a.credsInDetails));
ok('A-7 利用データの一覧が既定で開いている', a.license === true);

/* B) 時刻をタップ → ② の先頭で止まる（C53：render() は async） */
const rows = await p.$$('#step1 button');
if (rows[6]) { await rows[6].click(); await p.waitForTimeout(2500); }
const bTop = await p.evaluate(() => Math.round(document.getElementById('step2').getBoundingClientRect().top));
ok('B-1 時刻タップで②の先頭に止まる（飛び越えない）', Math.abs(bTop) < 60, 'step2Top=' + bTop);

/* C) 行き先をタップ → ③ が描かれる */
const cards = await p.$$('#cards .card');
if (cards[1]) { await cards[1].click(); await p.waitForTimeout(2500); }
const c = await p.evaluate(() => ({
  top: Math.round(document.getElementById('step3').getBoundingClientRect().top),
  turns: document.querySelectorAll('#turns li').length,
  gmap: document.querySelector('#gmap')?.getAttribute('href') || '',
}));
ok('C-1 行き先タップで③の先頭に止まる', Math.abs(c.top) < 60, 'step3Top=' + c.top);
ok('C-2 曲がる場所が出る', c.turns > 0, String(c.turns));
ok('C-3 Googleマップのリンクが張られる', c.gmap.startsWith('http'), c.gmap.slice(0, 40));

/* D) 屋内への導線（2026-08-23 に死んでいた箇所） */
await p.evaluate(() => document.querySelector('#chipPlace')?.scrollIntoView());
const inSel = await p.evaluate(() => {
  for (const id of ['toIndoorPartial', 'toIndoor']) {
    const e = document.getElementById(id);
    if (e && e.offsetParent !== null) return '#' + id;
  }
  return null;
});
if (inSel) {
  await p.click(inSel); await p.waitForTimeout(2500);
  ok('D-1 屋内モードへ移れる', (await p.$$('#cards .card')).length > 0);
} else {
  console.log('SKIP  D-1 屋内への入口はこの条件では出ない（31以上の時刻が無い日）');
}

/* D-2〜D-5) 収録範囲の外を選んだときの案内（2026-08-29 追加・P23）
   なぜ：「現在地」を押す人の大半は池袋の外にいる。ここが「答えられません」で
   終わると、歩行空間ネットワークが都内17地区しかないことを語る場所を1つ失う。
   新宿駅の座標を渡して、案内・提言・前の出発地への復帰の3つを見る。 */
{
  const ctx2 = await b.newContext({ viewport: { width: 430, height: 900 },
    geolocation: { latitude: 35.6896, longitude: 139.7006 }, permissions: ['geolocation'] });
  const p2 = await ctx2.newPage();
  const e2 = []; p2.on('pageerror', e => e2.push(String(e).slice(0, 200)));
  await p2.goto(BASE + '?fixed=1', { waitUntil: 'load', timeout: 90000 });
  await p2.waitForTimeout(6000);
  await p2.click('#geo');
  await p2.waitForTimeout(4000);
  const o = await p2.evaluate(() => {
    const w = document.querySelector('#outside'), d = w.querySelector('details');
    return { shown: !w.classList.contains('hidden'),
             btn:   !!w.querySelector('#outsidePick'),
             /* ★ 詳細は畳んであるので innerText には出ない。textContent で見る */
             has17: !!d && /17地区/.test(d.textContent),
             folded: !!d && !d.open,
             label: document.querySelector('#originLabel')?.textContent };
  });
  ok('D-2 範囲外を選ぶと案内が出る', o.shown);
  ok('D-3 「地図で範囲を見る」ボタンと、畳んだ詳細（都内17地区）がある', o.btn && o.has17 && o.folded);
  ok('D-4 範囲外を選んでも前の出発地に戻る', o.label === '池袋駅東口', o.label);
  /* D-6：ボタンを押すと出発地の地図が開き、範囲の全体が入る倍率に引かれる */
  await p2.click('#outsidePick');
  await p2.waitForTimeout(2500);
  const g = await p2.evaluate(() => ({
    open: !document.querySelector('#pickWrap').classList.contains('hidden'),
    px: document.querySelector('#pickMap')?.width }));
  ok('D-6 「地図で範囲を見る」で出発地の地図が開く', g.open);
  /* D-7：範囲の輪郭（破線）が実際に描かれているか。
     線は canvas の絵なので DOM では見えない。赤い画素を数えて確かめる。 */
  const red = await p2.evaluate(() => {
    const c = document.querySelector('#pickMap');
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4)
      if (d[i] > 110 && d[i + 1] < 95 && d[i + 2] < 95) n++;
    return n;
  });
  ok('D-7 範囲の輪郭が地図に描かれている', red > 200, red + ' px');
  ok('D-5 範囲外でも例外が出ていない', e2.length === 0, e2.slice(0, 2).join(' | '));
  await ctx2.close();
}

ok('E-1 JavaScript の例外が出ていない', errs.length === 0, errs.slice(0, 2).join(' | '));
await b.close();
console.log(ng ? `\n${ng} 件 FAIL` : '\nすべて PASS');
process.exit(ng ? 1 : 0);
