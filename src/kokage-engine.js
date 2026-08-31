/* こかげ：ブラウザ側の経路探索エンジン（B-2：出発地を任意地点に）2026-08-21 新設
 *
 * ★ 何をしているか
 *   Python 側（route.py / destination.py / hydration.py）の計算のうち、
 *   「出発地に依存しない部分」＝リンクと公園の時刻別日陰率 は事前計算して
 *   out/kokage_graph.json に固めてある。ここでは
 *     ① 任意地点を最寄りノードにスナップ
 *     ② 暑さ指数・遊び方・体重から各リンクの mL を作る
 *     ③ ダイクストラ
 *     ④ 公園ごとに 往復mL ＋ 滞在mL を出して並べる
 *   だけを行う。サーバは要らない。
 *
 * ★ Python と一致していること（定数はすべて hydration.py / route.py / destination.py と同値）
 */
export const C = {
  DELTA_WBGT_SHADE: -2.0,
  DELTA_WBGT_CHILD_NORMAL: 0.3,
  DELTA_WBGT_CHILD_HARSH: 2.0,
  WBGT_INDOOR: 25.0,
  SR_REF_ML_PER_MIN: 10.8,
  BW_REF_KG: 60.0,
  METS_REF: 3.0,
  WBGT_REF: 28.0,
  BETA_PER_DEG: 0.165,
  BSA_EXPONENT: 2 / 3,
  K_CHILD: 1.0,
  GATE_WBGT: 31.0,
  SPEED_M_PER_MIN: 53.1,
  SIGNAL_WAIT_SEC: 30.0,
  SNAP_M: 80.0,
  ORIGIN_MAX: 200.0,   // 出発地がここより遠いと計算しない
  FALLBACK_M: 400.0,
  /* 直線距離→実距離の迂回係数。［事実］[R-19] 腰塚・小林(1983)「R = 1.3u」。
     ★ 2026-08-30（P35）：この街の歩行空間ネットワーク上でも実測した。
       中央値 1.291（n=89,427・IQR 1.174〜1.440）＝ 文献値と一致するので 1.3 のまま。
       出力での感度と入れ替わりの境界は `detour_measure.mjs` を参照。 */
  DETOUR: 1.3,
  BLDG_COVER_MAX: 0.50,
/* ★ 2026-08-22（tasks.md C15）：子連れ歩行の METs を 2.0 → 2.8 に直した。
     [R-09c] 厚労省「生活活動のメッツ表」の 2.0 の行は「ゆっくりした歩行（平地、非常に遅い＝53m/分未満）」で、
     B3 の実測 53.1 m/分（n=3・51.6/53.8/54.5・距離加重）はこの条件から外れている。
     隣の行「ゆっくりした歩行（平地、遅い＝53m/分）2.8」が実測とほぼ一致する。
     ★ 実測3本のうち 51.6 の1本は 53 未満で、境界をまたいでいる。断定はできないので、
       画面と資料には「n=3・51.6〜54.5 m/分」のばらつきを併記すること。 */
  METS: { walk_slow: 2.8, stand: 1.8, sit: 1.3, play_active: 5.8, play_light: 2.8, play_sit: 2.2 },
};

/* hydration.effective_wbgt と同じ */
export function effectiveWbgt(base, { sunlit, harsh = true, indoor = false }, sunFrac = 1.0) {
  if (indoor) return C.WBGT_INDOOR;
  const f = Math.min(Math.max(sunFrac, 0), 1);
  let w = base;
  if (!sunlit) w += C.DELTA_WBGT_SHADE * f;
  const child = sunlit && harsh ? C.DELTA_WBGT_CHILD_HARSH : C.DELTA_WBGT_CHILD_NORMAL;
  w += C.DELTA_WBGT_CHILD_NORMAL + (child - C.DELTA_WBGT_CHILD_NORMAL) * f;
  return w;
}

/* hydration.sweat_rate と同じ */
export function sweatRate(wbgtEff, mets, bwKg) {
  const body = Math.pow(bwKg / C.BW_REF_KG, C.BSA_EXPONENT);
  const act = mets / C.METS_REF;
  const env = Math.max(1.0 + C.BETA_PER_DEG * (wbgtEff - C.WBGT_REF), 0.2);
  return C.SR_REF_ML_PER_MIN * act * body * C.K_CHILD * env;
}

/* 平面直角座標（EPSG:6677）への簡易変換は使わず、
   バンドルが持つ x/y（Python 側で pyproj 変換済み）で距離を測る。
   任意地点（緯度経度）は、緯度1度=111,132m・経度1度=111,320*cos(lat) の局所近似で
   最寄りノードだけを求める（80m 以内の判定にしか使わないので誤差は無視できる）。 */
function localMeters(lat1, lon1, lat2, lon2) {
  const dy = (lat2 - lat1) * 111132.0;
  const dx = (lon2 - lon1) * 111320.0 * Math.cos((lat1 * Math.PI) / 180);
  return Math.hypot(dx, dy);
}

export class Kokage {
  constructor(bundle) {
    this.b = bundle;
    this.hours = bundle.meta.hours;
    this.scale = bundle.meta.shade_scale;
    const n = bundle.nodes.lat.length;
    this.n = n;
    // 隣接リスト
    this.adj = Array.from({ length: n }, () => []);
    const E = bundle.edges;
    this.m = E.u.length;
    for (let i = 0; i < this.m; i++) {
      this.adj[E.u[i]].push(i);
      this.adj[E.v[i]].push(i);
    }
    this._comp = null;
  }

  other(ei, node) {
    const E = this.b.edges;
    return E.u[ei] === node ? E.v[ei] : E.u[ei];
  }

  /* リンク1本の mL（往路片道） */
  edgeMl(ei, hi, wbgt, bw, sunFrac = 1.0) {
    const E = this.b.edges;
    const sh = E.shade[ei][hi] / this.scale;
    const walkMin = E.dist[ei] / C.SPEED_M_PER_MIN;
    const waitMin = E.wait[ei];
    let ml = 0;
    for (const [minutes, mets] of [[walkMin, C.METS.walk_slow], [waitMin, C.METS.stand]]) {
      if (minutes <= 0) continue;
      for (const [frac, sunlit] of [[1 - sh, true], [sh, false]]) {
        if (frac <= 0) continue;
        ml += sweatRate(effectiveWbgt(wbgt, { sunlit }, sunFrac), mets, bw) * minutes * frac;
      }
    }
    return ml;
  }

  /* 最寄りノード（maxd[m] 以内。届かなければ null） */
  nearest(lat, lon, maxd = C.SNAP_M, pool = null) {
    const N = this.b.nodes;
    let best = -1, bd = Infinity;
    for (let i = 0; i < this.n; i++) {
      if (pool && !pool.has(i)) continue;
      const d = localMeters(lat, lon, N.lat[i], N.lon[i]);
      if (d < bd) { bd = d; best = i; }
    }
    return bd <= maxd ? { node: best, gap: 0, dist: bd } : { node: best, gap: bd, dist: bd };
  }

  /* 連結成分（20ノード以上のものだけを使う。destination.recommend と同じ扱い） */
  components() {
    if (this._comp) return this._comp;
    const seen = new Int32Array(this.n).fill(-1);
    let cid = 0;
    const sizes = [];
    for (let s = 0; s < this.n; s++) {
      if (seen[s] >= 0) continue;
      const stack = [s]; seen[s] = cid; let cnt = 0;
      while (stack.length) {
        const u = stack.pop(); cnt++;
        for (const ei of this.adj[u]) {
          const v = this.other(ei, u);
          if (seen[v] < 0) { seen[v] = cid; stack.push(v); }
        }
      }
      sizes.push(cnt); cid++;
    }
    this._comp = { of: seen, sizes };
    return this._comp;
  }

  /* ダイクストラ（コスト＝mL）。dist[m] と sun_min も同時に積む */
  dijkstra(src, hi, wbgt, bw, sunFrac = 1.0) {
    const INF = Infinity;
    const ml = new Float64Array(this.n).fill(INF);
    const met = new Float64Array(this.n);
    const sun = new Float64Array(this.n);
    const prev = new Int32Array(this.n).fill(-1);
    const prevE = new Int32Array(this.n).fill(-1);
    ml[src] = 0;
    // 単純な二分ヒープ
    const heap = [[0, src]];
    const push = (x) => { heap.push(x); let i = heap.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (heap[p][0] <= heap[i][0]) break;[heap[p], heap[i]] = [heap[i], heap[p]]; i = p; } };
    const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let s = i; if (l < heap.length && heap[l][0] < heap[s][0]) s = l; if (r < heap.length && heap[r][0] < heap[s][0]) s = r; if (s === i) break;[heap[s], heap[i]] = [heap[i], heap[s]]; i = s; } } return top; };
    const E = this.b.edges;
    while (heap.length) {
      const [d, u] = pop();
      if (d > ml[u] + 1e-12) continue;
      for (const ei of this.adj[u]) {
        const v = this.other(ei, u);
        const w = this.edgeMl(ei, hi, wbgt, bw, sunFrac);
        if (ml[u] + w < ml[v]) {
          ml[v] = ml[u] + w;
          met[v] = met[u] + E.dist[ei];
          const sh = E.shade[ei][hi] / this.scale;
          sun[v] = sun[u] + (E.dist[ei] / C.SPEED_M_PER_MIN + E.wait[ei]) * (1 - sh);
          prev[v] = u; prevE[v] = ei;
          push([ml[v], v]);
        }
      }
    }
    return { ml, met, sun, prev, prevE };
  }

  /* 出発地周辺 r[m] の歩道の日陰率（長さ加重）。NW外区間の代用に使う */
  /* 入口までの数十mに当てる日陰率。そのノードに接するリンクの長さ加重平均 */
  edgeShadeAt(node,hi){const E=this.b.edges;let t=0,s=0;
    for(const ei of this.adj[node]){t+=E.dist[ei];s+=E.dist[ei]*(E.shade[ei][hi]/this.scale);}
    return t?s/t:0;}
  localShade(node, hi, r = 200) {
    const N = this.b.nodes, E = this.b.edges;
    let tot = 0, sh = 0;
    for (let i = 0; i < this.m; i++) {
      const u = E.u[i];
      if (Math.hypot(N.x[u] - N.x[node], N.y[u] - N.y[node]) > r) continue;
      tot += E.dist[i]; sh += E.dist[i] * (E.shade[i][hi] / this.scale);
    }
    return tot ? sh / tot : 0;
  }

  /* 本体：任意地点から候補地を並べる */
  recommend({ lat, lon, hour, wbgt, stayMin = 60, bw = 15, metsPlay = 4.9, sunFrac = 1.0, purpose = 'outdoor_play' }) {
    const hi = this.hours.indexOf(hour);
    if (hi < 0) throw new Error('この時刻は事前計算に入っていません: ' + hour);
    const comp = this.components();
    const usable = new Set();
    for (let i = 0; i < this.n; i++) if (comp.sizes[comp.of[i]] >= 20) usable.add(i);
    /* ★ 2026-08-22：歩行空間ネットワークの外は計算しない（destination.py と同じ 200m） */
    const o = this.nearest(lat, lon, 1e9, usable);
    if (o.node < 0 || o.dist > C.ORIGIN_MAX) return { error: 'outside', dist: o.dist };
    const reach = new Set();
    for (let i = 0; i < this.n; i++) if (comp.of[i] === comp.of[o.node]) reach.add(i);

    const gate = wbgt >= C.GATE_WBGT;
    /* ★ 2026-08-23（不具合修正）：ここは `gate ? C.METS.play_light : metsPlay` だった。
       31以上のとき、利用者が選んだ「遊び方」を黙って 2.8 METs に差し替えていた。
       遊び方を利用者が選べるようにした時点で、この仮定は勝手な上書きになる。
       ★ pages/b2/kokage-v1c-mobile.html と同じ修正。
       ★ destination.py 251行目にも同じ上書きが残っている（purpose ベースで、
          こちらは利用者の選択を受けないため、いまは実害なし。C52 で扱う）。 */
    const mets = metsPlay;
    const D = this.dijkstra(o.node, hi, wbgt, bw, sunFrac);

    const rows=[], seenName=new Set();
    for(const p of this.b.parks){
      /* ★ 2026-08-22：終点は「公園の点の最寄りノード」ではなく、
         「公園ポリゴンの縁から60m以内の候補ノードのうち、合計mLが最小のもの」。
         区の公園データは点＋面積しか無く、形は土地利用ポリゴンから拾っているため、
         点とポリゴンが最大146mずれる（東池袋中央公園の点は建物の中にあった）。 */
      const ent=p.entry||[], gaps=p.entry_gap||[];
      let pick=null;
      for(let i=0;i<ent.length;i++){
        const n=ent[i]; if(!reach.has(n)||D.ml[n]===Infinity) continue;
        /* ★ 歩行空間ネットワークは池袋駅周辺しか無い。網の外は直線×迂回係数で近似し、
           400m を超えたら候補にしない（destination.py の FALLBACK_M / DETOUR と同じ扱い）。 */
        if(gaps[i]>C.FALLBACK_M) continue;
        const gap=gaps[i]>0 ? gaps[i]*C.DETOUR : 0;
        let extra=0, exSun=0;
        if(gap>0){
          const lsh = gaps[i]<=60 ? this.edgeShadeAt(n,hi) : this.localShade(n,hi);
          const mins=gap/C.SPEED_M_PER_MIN;
          for(const [fr,su] of [[1-lsh,true],[lsh,false]]) if(fr>0)
            extra+=sweatRate(effectiveWbgt(wbgt,{sunlit:su},sunFrac),C.METS.walk_slow,bw)*mins*fr;
          exSun=mins*(1-lsh);
        }
        const tot=D.ml[n]+extra;
        if(!pick||tot<pick.tot) pick={node:n,gap,extra,exSun,tot};
      }
      if(!pick) continue;
      const acc = pick.gap===0 ? 'L1' : (pick.gap<=78 ? 'L2' : 'L3');
      const move=pick.tot, dist=D.met[pick.node]+pick.gap, sunMin=D.sun[pick.node]+pick.exSun;
      const shade=p.indoor?1:p.shade[hi]/this.scale;
      let stay=0;
      if(p.indoor) stay=sweatRate(C.WBGT_INDOOR,mets,bw)*stayMin;
      else for(const [fr,su] of [[1-shade,true],[shade,false]]) if(fr>0)
        stay+=sweatRate(effectiveWbgt(wbgt,{sunlit:su,indoor:false},sunFrac),mets,bw)*stayMin*fr;
      /* ★ 2026-08-22：公共施設一覧と赤ちゃん・ふらっとの両方に載っている施設は
         同じ名前で2件出る（区民ひろば南池袋）。画面では区別していないので名前で1件にする。 */
      if(seenName.has(p.name)) continue;
      seenName.add(p.name);
      rows.push({name:p.name,indoor:p.indoor,acc,node:pick.node,gap:pick.gap,
                 dist2:Math.round(dist*2),dist1:Math.round(dist),
                 move:move*2,stay,total:move*2+stay,shade,sunMin:sunMin*2,
                 cx:p.cx,cy:p.cy});}
    rows.sort((a, b) => a.total - b.total);
    return { gate, origin: o, hour, wbgt, n: rows.length,
             outdoor: rows.filter((r) => !r.indoor), indoor: rows.filter((r) => r.indoor), all: rows };
  }
}
