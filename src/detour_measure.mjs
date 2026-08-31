/* P35：迂回係数 1.3 を、この街の歩行空間ネットワーク上で実測して検証する（2026-08-30 新設）
 * 使い方: node detour_measure.mjs
 *
 * ★ なぜ要るか
 *   1.3 は `[R-19]` 腰塚・小林(1983)「In Urban areas, R = 1.3u」に基づく［事実］だが、
 *   `how-it-works.md` §3 に **「歩行者ネットワーク限定の日本の実測値は存在しません」** と
 *   自分で書いてある。ここを、手元の歩行空間ネットワークで埋める。
 *
 * ★ しかも 2026-08-22 に終点スナップを「公園の点」→「ポリゴンの縁」に変えたことで、
 *   全候補の gap が 0 より大きくなり、DETOUR が例外ケースではなく毎回の答えに効くようになった。
 *
 * 測るもの
 *   A) 実際に使われている gap（生の直線距離）の分布
 *   B) 歩行空間ネットワーク上での「実経路長 ÷ 直線距離」（距離帯別）
 *   C) DETOUR を動かすと1〜3位が入れ替わるか（4つの出発地・出力での感度）
 *   D) 入れ替わりの境界を 0.01 刻みで詰める（既定値が境界からどれだけ離れているか）
 */
import fs from 'fs';
import { Kokage, C } from './kokage-engine.js';
/* ★ 公開用コピー：バンドルは publish/ の直下（作業リポジトリでは ../out/）。値は同一です */
const B = JSON.parse(fs.readFileSync('../kokage_graph.json', 'utf8'));
const OFF = { 11: -0.44, 12: -0.22, 13: 0.0, 14: -0.35, 15: -0.60, 16: -1.38 };
const MP = 4.9, BASE_WBGT = 29.0;
const q = (a, p) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(s.length * p))]; };
const f1 = x => x.toFixed(1), f3 = x => x.toFixed(3);
const nearXY = (x, y) => { let bi = 0, bd = Infinity;
  for (let i = 0; i < B.nodes.x.length; i++) { const d = Math.hypot(B.nodes.x[i] - x, B.nodes.y[i] - y); if (d < bd) { bd = d; bi = i; } }
  return { lat: B.nodes.lat[bi], lon: B.nodes.lon[bi] }; };
const ORIGINS = [
  ['池袋駅東口',     { lat: 35.72950, lon: 139.71150 }],
  ['都電雑司ヶ谷駅', nearXY(-10455.9, -30603.1)],
  ['東池袋四丁目駅', nearXY(-10207.4, -30462.8)],
  ['向原駅',         nearXY(-9808.7, -30066.7)],
];
const top3 = (K, O, h) => K.recommend({ ...O, hour: h, wbgt: Math.round((BASE_WBGT + OFF[h]) * 100) / 100,
  stayMin: 60, bw: 15, metsPlay: MP });

/* ---------- A) いま使われている gap ---------- */
const K0 = new Kokage(B), gapsUsed = [];
for (const h of B.meta.hours) for (const x of top3(K0, ORIGINS[0][1], h).outdoor) if (x.gap > 0) gapsUsed.push(x.gap / C.DETOUR);
const gapsAll = [];
for (const p of B.parks) for (const g of (p.entry_gap || [])) if (g > 0 && g <= C.FALLBACK_M) gapsAll.push(g);
console.log('■ A) gap（公園ポリゴンの縁 → 最寄りノードの直線距離・m）');
console.log(`  実際に採用された gap  n=${gapsUsed.length}  中央値 ${f1(q(gapsUsed,.5))}  25% ${f1(q(gapsUsed,.25))}  75% ${f1(q(gapsUsed,.75))}  最大 ${f1(Math.max(...gapsUsed))}`);
console.log(`  候補の全 entry_gap    n=${gapsAll.length}  中央値 ${f1(q(gapsAll,.5))}  75% ${f1(q(gapsAll,.75))}  95% ${f1(q(gapsAll,.95))}`);

/* ---------- B) ネットワーク上の 実経路長 ÷ 直線距離 ---------- */
const N = B.nodes.x.length, X = B.nodes.x, Y = B.nodes.y;
const adj = Array.from({ length: N }, () => []);
for (let e = 0; e < B.edges.u.length; e++) {
  const u = B.edges.u[e], v = B.edges.v[e], d = B.edges.dist[e];
  adj[u].push([v, d]); adj[v].push([u, d]);
}
function dijkstra(s) {
  const D = new Float64Array(N).fill(Infinity); D[s] = 0;
  const pq = [[0, s]];
  while (pq.length) {
    pq.sort((a, b) => b[0] - a[0]);
    const [d, u] = pq.pop();
    if (d > D[u]) continue;
    for (const [v, w] of adj[u]) if (d + w < D[v]) { D[v] = d + w; pq.push([D[v], v]); }
  }
  return D;
}
const BANDS = [[10,30],[30,60],[60,100],[100,200],[200,400],[400,800]];
const bucket = BANDS.map(() => []);
let seed = 20260829;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
const SRC = 200;
for (let k = 0; k < SRC; k++) {
  const s = Math.floor(rnd() * N), D = dijkstra(s);
  for (let t = 0; t < N; t++) {
    if (t === s || !isFinite(D[t])) continue;
    const dl = Math.hypot(X[t] - X[s], Y[t] - Y[s]);
    if (dl < 1) continue;
    for (let i = 0; i < BANDS.length; i++)
      if (dl >= BANDS[i][0] && dl < BANDS[i][1]) { bucket[i].push(D[t] / dl); break; }
  }
}
console.log(`\n■ B) 実経路長 ÷ 直線距離（歩行空間ネットワーク上・出発ノード${SRC}点・乱数の種は固定）`);
console.log('  直線距離帯        n      中央値   25%    75%    90%');
for (let i = 0; i < BANDS.length; i++) {
  const a = bucket[i]; if (!a.length) continue;
  console.log(`  ${String(BANDS[i][0]).padStart(4)}〜${String(BANDS[i][1]).padEnd(4)}m ${String(a.length).padStart(8)}   `
    + `${f3(q(a,.5))}  ${f3(q(a,.25))}  ${f3(q(a,.75))}  ${f3(q(a,.9))}`);
}
const lo = q(gapsUsed, .1), hi = q(gapsUsed, .9), inRange = [];
for (let i = 0; i < BANDS.length; i++) if (BANDS[i][1] > lo && BANDS[i][0] < hi) inRange.push(...bucket[i]);
console.log(`\n  ★ 採用 gap の 10〜90%（${f1(lo)}〜${f1(hi)}m）に重なる帯だけ：`
  + `n=${inRange.length}  中央値 ${f3(q(inRange,.5))}  25% ${f3(q(inRange,.25))}  75% ${f3(q(inRange,.75))}`);
console.log(`  比較：[R-19] 腰塚・小林(1983) R=1.3u ／ 理論値 4/π=1.273 ／ 森田ら(2014) 日本112都市平均 1.3035`);

/* ---------- C) 出発地4つ × DETOUR での出力の変化 ---------- */
console.log('\n■ C) DETOUR を動かすと1〜3位はどうなるか');
for (const [nm, O] of ORIGINS) {
  const base = {};
  const rows = [];
  for (const d of [1.0, 1.1, 1.2, 1.29, 1.3, 1.4, 1.6, 2.0]) {
    C.DETOUR = d; const K = new Kokage(B);
    let flip = 0; const ml = [];
    for (const h of B.meta.hours) {
      const r = top3(K, O, h), t = r.outdoor.slice(0, 3).map(x => x.name).join('>');
      if (d === 1.3) base[h] = t; else if (base[h] && base[h] !== t) flip++;
      ml.push(r.outdoor[0] ? r.outdoor[0].total.toFixed(0) : '-');
    }
    rows.push(`  DETOUR=${d.toFixed(2)}  1位mL ${ml.join('/')}  1〜3位が1.3と違う時刻 ${d === 1.3 ? '（基準）' : flip + '/6'}`);
  }
  console.log(` ● ${nm}`); rows.forEach(r => console.log(r));
}

/* ---------- D) 入れ替わりの境界 ---------- */
console.log('\n■ D) 入れ替わりの境界（0.01刻み・1.00〜2.00）');
for (const [nm, O] of ORIGINS) {
  const prev = {}; const hits = [];
  for (let d = 1.00; d <= 2.001; d = Math.round((d + 0.01) * 100) / 100) {
    C.DETOUR = d; const K = new Kokage(B);
    for (const h of B.meta.hours) {
      const r = top3(K, O, h), t = r.outdoor.slice(0, 3).map(x => x.name).join('>');
      if (prev[h] !== undefined && prev[h] !== t) hits.push(`${d.toFixed(2)}(${h}時${prev[h].split('>')[0] !== t.split('>')[0] ? '・1位' : ''})`);
      prev[h] = t;
    }
  }
  console.log(` ● ${nm}  境界: ${hits.length ? hits.join(' ') : 'なし'}`);
}
C.DETOUR = 1.3;
console.log('\n★ 既定 1.3 は、上の境界のどこからいちばん近いかで評価すること（how-it-works.md §3）。');
