/* こかげ v1c「暑い日の例」の煙テスト（2026-09-06 新設）
   なぜ：秋・冬に開くと6時刻すべてが28未満になり、この作品の中核である
   「暑さ指数31以上の時刻には屋外の行き先を出さない」が画面に一度も現れない。
   そこで、涼しい日にだけ「暑い日の例」への入口を出している（既定は変えていない）。
   夏に出てしまう／戻せない／今日の値だと誤解される、のどれかが起きたら失敗。

   使い方：
     cd <publish のコピー> && python3 -m http.server 8099 &
     node smoke_hotday.mjs http://127.0.0.1:8099/
   ★ fetch を使うので file:// では動かない。必ず HTTP で開く。
   ★ 暑さ指数は共有URLの `?w=` で差し替えている（自動取得を待たずに条件を作れる）。 */
import { chromium } from 'playwright';

const B = (process.argv[2] || 'http://127.0.0.1:8099/') + 'kokage-v1c-mobile.html';
let ng = 0;
const ok = (n, c, d = '') => { console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  :: ' + d : ''}`); if (!c) ng++; };

const b = await chromium.launch(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {});
const p = await b.newPage({ viewport: { width: 430, height: 900 } });
const errs = [];
p.on('pageerror', e => errs.push(String(e).slice(0, 180)));

const snap = () => p.evaluate(() => ({
  ex:   !document.querySelector('#hotEx')?.classList.contains('hidden'),
  bar:  !document.querySelector('#hotBar')?.classList.contains('hidden'),
  wv:   document.querySelector('#wbgtV')?.textContent,
  reds: [...document.querySelectorAll('#hours .hr')].filter(x => x.textContent.includes('おすすめしません')).length,
  mls:  [...document.querySelectorAll('#hours .hr')].map(x => (x.textContent.match(/(\d+)\s*mL/) || [])[1]).join('/'),
}));
const open = async (q) => { await p.goto(B + q, { waitUntil: 'load' }); await p.waitForTimeout(6000); };

/* 涼しい日（6時刻すべて28未満） */
await open('?w=22');
const cool = await snap();
ok('H-1 涼しい日は入口が出て、帯は出ていない', cool.ex && !cool.bar, JSON.stringify(cool));

/* 暑い日（28以上の時刻がある） */
await open('?w=29');
const hot = await snap();
ok('H-2 28以上の時刻がある日は入口を出さない', !hot.ex && !hot.bar, JSON.stringify(hot));

/* 例を開く */
await open('?w=22');
await p.click('#hotExBtn');
await p.waitForTimeout(2500);
const ex = await snap();
ok('H-3 押すと帯が出て 31.5 になり、赤が4行・数字が2行残る',
   ex.bar && !ex.ex && ex.wv === '31.5' && ex.reds === 4, JSON.stringify(ex));

/* 今日の値に戻す */
await p.click('#hotBack');
await p.waitForTimeout(2500);
const back = await snap();
ok('H-4 戻すと元の値に戻り、6時刻の数字も一致する',
   !back.bar && back.ex && back.wv === cool.wv && back.reds === 0 && back.mls === cool.mls,
   JSON.stringify(back));

ok('H-5 JavaScript の例外が出ていない', errs.length === 0, errs.join(' | '));

await b.close();
console.log(ng ? `\nNG ${ng} 件` : '\nすべて PASS');
process.exit(ng ? 1 : 0);
