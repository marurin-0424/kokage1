/* JS エンジン（画面）と Python（screen6.json）の答えを並べる
 * 使い方: node parity_test.mjs
 *
 * ★★ 2026-08-30（P37）に判定を作り直しました。
 *
 *   それまでは「1〜3位の顔ぶれと合計mLが一致するか」を PASS/FAIL にしていたため、
 *   **意図的な改良まで FAIL に数えて「不一致 22 / 36」と出ていました**（受け入れ試験に見えるが、
 *   実際には差分を見る道具でしかなかった）。切り分けた結果：
 *
 *     ・滞在 mL（stay）は 18件すべて完全一致（差 0）
 *       → 発汗モデル・METs・暑さ指数は JS と Python で同一。C52（METs の上書き）は無関係だった
 *         （screen6.py は暑さ指数 27.62〜29.0 しか計算せず、gate=31 が6時刻すべて False のため）
 *     ・移動 mL（move）だけが常に +12〜30mL 高く、精度ラベルが Python=L1 → JS=L2 に全件変わる
 *       → 2026-08-22 の終点スナップ変更（公園の点 → ポリゴンの縁）そのもの。
 *         縁までの gap × 迂回係数 1.3 を歩く分が、JS だけに乗っている＝**意図した改良**
 *
 *   そこで判定はこう変えました：
 *     PASS/FAIL に数えるのは **stay の一致だけ**（ここがずれたら本物の回帰）。
 *     move の差・順位の差は「意図的な差」として表示だけする。
 */
import fs from 'fs';
import { Kokage } from './kokage-engine.js';

/* ★ 公開用コピー：バンドルは publish/ の直下に置いてあるので、そこを見ます
   （作業リポジトリでは '../out/kokage_graph.json'。値は同一です） */
const bundle = JSON.parse(fs.readFileSync('../kokage_graph.json', 'utf8'));
const s6 = JSON.parse(fs.readFileSync('../out/screen6.json', 'utf8'));
const K = new Kokage(bundle);

const ORIGIN = { lat: 35.72950, lon: 139.71150 };   // 池袋駅東口（screen6.py と同じ）
const METS_PLAY = 4.9;
const OFFSET = { 11: -0.44, 12: -0.22, 13: 0.0, 14: -0.35, 15: -0.60, 16: -1.38 };

let ng = 0, n = 0, nameDiff = 0;
const moveDiffs = [];
console.log('時刻 公園            py_move js_move  差   | py_stay js_stay 差 | py_acc js_acc');
for (const h of bundle.meta.hours) {
  const wbgt = Math.round((29.0 + OFFSET[h]) * 100) / 100;
  const r = K.recommend({ ...ORIGIN, hour: h, wbgt, stayMin: 60, bw: 15, metsPlay: METS_PLAY });
  const jsByName = new Map(r.outdoor.map(x => [x.name, x]));
  const pyTop = s6.hours[String(h)].top, jsTop = r.outdoor.slice(0, 3);
  for (let i = 0; i < 3; i++) if (pyTop[i] && jsTop[i] && pyTop[i].name !== jsTop[i].name) nameDiff++;
  for (const a of pyTop) {
    const b = jsByName.get(a.name);
    if (!b) { console.log(`${h}   ${a.name.padEnd(14)} ★ JS の候補に無い`); ng++; n++; continue; }
    const dStay = b.stay - a.stay, dMove = b.move - a.move;
    const okStay = Math.abs(dStay) <= Math.max(1, a.stay * 0.01);
    n++; if (!okStay) ng++;
    moveDiffs.push(dMove);
    console.log(`${h}   ${a.name.padEnd(14)}${String(a.move).padStart(7)}${b.move.toFixed(0).padStart(8)}`
      + `${(dMove >= 0 ? '+' : '') + dMove.toFixed(0)}`.padStart(6)
      + ` |${String(a.stay).padStart(8)}${b.stay.toFixed(0).padStart(8)}${dStay.toFixed(0).padStart(4)}`
      + `${okStay ? '' : ' ★回帰'} | ${a.acc}    ${b.acc}`);
  }
}
const med = a => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
console.log(`\n［判定］滞在mLの一致 ${n - ng} / ${n}${ng ? `  ★ ${ng} 件が不一致＝回帰の疑い` : '  すべて一致'}`);
console.log(`［情報］移動mLの差（JS − Python）：中央値 ${med(moveDiffs).toFixed(0)}mL`
  + `／範囲 ${Math.min(...moveDiffs).toFixed(0)}〜${Math.max(...moveDiffs).toFixed(0)}mL`
  + `　＝ 終点スナップをポリゴンの縁に変えた分（意図的）`);
console.log(`［情報］1〜3位の顔ぶれが Python と違う枠：${nameDiff} / 18`
  + `　＝ 同じ理由による並び替え。順位の意味は tasks.md §4 の穴 #10 も参照`);
process.exit(ng ? 1 : 0);
