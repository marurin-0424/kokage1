/* こかげ v1c の共有URLの煙テスト（2026-09-06 新設）
   なぜ：結果をURLで共有できるようにした（P32）。状態8つを載せて復元するので、
   入力を1つ増やしたときに載せ忘れると、送った人と受け取った人で別の答えになる。
   往復（作る → 開き直す）で state・チップ・入力欄・出力文が一致することを見る。

   使い方：
     cd <publish のコピー> && python3 -m http.server 8099 &
     node smoke_share.mjs http://127.0.0.1:8099/
   ★ fetch を使うので file:// では動かない。必ず HTTP で開く。 */
import { chromium } from 'playwright';

const B = process.argv[2] || 'http://127.0.0.1:8099/';
let ng = 0;
const ok = (n, c, d = '') => { console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  :: ' + d : ''}`); if (!c) ng++; };

const b = await chromium.launch(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {});
const p = await b.newPage({ viewport: { width: 430, height: 900 } });
const errs = [];
p.on('pageerror', e => errs.push(String(e).slice(0, 180)));

/* 既定で開く。?fixed=1 は暑さ指数を自動取得させないため（数字を固定して比べる） */
await p.goto(B + 'kokage-v1c-mobile.html?fixed=1', { waitUntil: 'load' });
await p.waitForTimeout(6000);

/* ★ 2026-09-06：①の文言は「この6行が何か」までにする。
   「なぜ11〜16時なのか」は index.html 側（いま答えられる範囲）に置く、と決めた。
   審査員向けの説明を画面に持ち込むと、利用者に要らない文言が増えるため。 */
const lead = await p.evaluate(() => document.querySelector('#hoursLead')?.textContent.trim() || '');
ok('S-0 ①に説明文を置いていない（説明は index 側）', lead === '', lead.slice(0, 40));

/* 既定から全部ずらす：遊び方=半々(4.00)／滞在=90分／体重=18kg／15時／2件目 */
await p.evaluate(() => document.querySelector('#chipMets [data-v="4.00"]')?.click());
await p.waitForTimeout(1500);
await p.evaluate(() => [...document.querySelectorAll('#chipStay .chip')].find(x => x.dataset.v === '90')?.click());
await p.waitForTimeout(1500);
await p.evaluate(() => { const e = document.querySelector('#bw'); e.value = 18; e.dispatchEvent(new Event('change')); });
await p.waitForTimeout(1500);
await p.evaluate(() => document.querySelectorAll('#hours .hr')[4].click());
await p.waitForTimeout(2500);
await p.evaluate(() => document.querySelectorAll('#cards .card')[1].click());
await p.waitForTimeout(2500);

const snap = () => p.evaluate(() => {
  const s = window.kokage.state;
  return {
    u: window.kokage.shareUrl(),
    s: { h: s.hour, p: s.place, m: s.mets, st: s.stay, bw: s.bw, w: s.wbgt, d: s.pickIdx },
    bw: document.querySelector('#bw').value,
    mets: document.querySelector('#chipMets .chip.on')?.dataset.v,
    stay: document.querySelector('#chipStay .chip.on')?.dataset.v,
    wv: document.querySelector('#wbgtV').textContent,
    fc: document.querySelector('#fcSrc')?.textContent.slice(0, 40),
    r4: document.querySelector('#r4')?.textContent.trim(),
  };
});

const before = await snap();
ok('S-1 共有URLに8項目すべてが載る',
   ['o=', 'h=', 'p=', 'm=', 'st=', 'bw=', 'w=', 'd='].every(k => before.u.includes(k)),
   before.u.split('?')[1]);

/* 作ったURLで開き直す */
await p.goto(before.u, { waitUntil: 'load' });
await p.waitForTimeout(7000);
const after = await snap();

ok('S-2 state が一致する', JSON.stringify(before.s) === JSON.stringify(after.s), JSON.stringify(after.s));
ok('S-3 チップと入力欄の見た目も一致する',
   before.mets === after.mets && before.stay === after.stay && before.bw === after.bw && before.wv === after.wv,
   `${after.mets}／${after.stay}／${after.bw}／${after.wv}`);
ok('S-4 同じ行き先・同じ文が出る', before.r4 === after.r4, after.r4?.slice(0, 40));
ok('S-5 暑さ指数が共有された値であることを画面が言う', after.fc?.includes('共有された'), after.fc);
ok('S-6 JavaScript の例外が出ていない', errs.length === 0, errs.join(' | '));

await b.close();
console.log(ng ? `\nNG ${ng} 件` : '\nすべて PASS');
process.exit(ng ? 1 : 0);
