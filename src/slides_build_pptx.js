const pptxgen = require('pptxgenjs');
const p = new pptxgen();
p.layout = 'LAYOUT_WIDE';           // 13.3 x 7.5 inch
p.author = '丸山 倫太朗';
p.title  = 'こかげ — 都知事杯オープンデータ・ハッカソン2026';

const INK='0B0B0B', INK2='3A3A38', MUT='8A8880', PARK='1BAF7A', SUN='EB6834', SHADE='2A78D6',
      PLANE='F6F6F3', CARD='FFFFFF', HAIR='E1E0D9';
const F='Meiryo';
const IMG = process.env.KOKAGE_FIG || '../fig/';   // ★ 画像は fig/ から読む（旧版は cwd 直書きで手元では動かなかった）
const W=13.3, H=7.5, M=0.62;

function base(dark){
  const s = p.addSlide();
  s.background = { color: dark ? '13211C' : PLANE };
  return s;
}
function kicker(s, t){
  s.addText(t, {x:M, y:0.44, w:6, h:0.3, fontFace:F, fontSize:11, bold:true, color:MUT, charSpacing:2, margin:0});
}
function title(s, runs, y){
  s.addText(runs, {x:M, y:y||0.82, w:W-2*M, h:0.95, fontFace:F, fontSize:30, bold:true, color:INK, margin:0, valign:'top'});
}
function pg(s, n){
  s.addText(n+' / 10', {x:W-1.6, y:H-0.52, w:1.0, h:0.3, fontFace:F, fontSize:9, color:'C2C0B9', align:'right', margin:0});
}
function note(s, t, y){
  s.addText(t, {x:M, y:y, w:W-2*M, h:0.9, fontFace:F, fontSize:11.5, color:INK2, lineSpacing:20, margin:0});
}
function card(s, x,y,w,h){
  s.addShape(p.ShapeType.roundRect, {x,y,w,h, rectRadius:0.09, fill:{color:CARD}, line:{color:HAIR, width:1},
    shadow:{type:'outer', angle:90, blur:10, offset:0.05, opacity:0.10, color:'000000'}});
}

/* 1 表紙 */
let s = base(true);
s.addText([{text:'こ',options:{color:'FFFFFF'}},{text:'か',options:{color:PARK}},{text:'げ',options:{color:'FFFFFF'}}],
  {x:M, y:2.0, w:7, h:1.5, fontFace:F, fontSize:66, bold:true, margin:0});
s.addText('建物の影から、子連れの夏の外出を変える',
  {x:M, y:3.45, w:7.6, h:0.5, fontFace:F, fontSize:21, color:'D8E6DE', margin:0});
s.addText('都知事杯オープンデータ・ハッカソン2026 ／ テーマ：気候変動\n個人参加・丸山 倫太朗　　私にも小さい子がいます',
  {x:M, y:4.15, w:7.6, h:0.9, fontFace:F, fontSize:13, color:'9FB5AC', lineSpacing:22, margin:0});
s.addImage({path:IMG+'x_hours.png', x:8.75, y:1.45, w:3.9, h:3.81, sizing:{type:'contain', w:3.9, h:3.81}});
pg(s,1);

/* 2 課題 */
s = base(); kicker(s,'01　課題');
title(s,'この酷暑で、子どもをどこで遊ばせるか');
s.addText([
 {text:'親の大きな悩みです。私も、この暑さで公園に連れて行っていいのかと迷います。', options:{bullet:true, breakLine:true}},
 {text:'屋内にするとしても、道中が暑い。', options:{bullet:true, breakLine:true}},
 {text:'水をどれだけ飲ませるかも、悩ましい。', options:{bullet:true}},
], {x:M, y:2.0, w:7.0, h:2.0, fontFace:F, fontSize:15, color:INK2, lineSpacing:26, paraSpaceAfter:8, margin:0});
card(s, 7.9, 1.95, 4.8, 2.4);
s.addText('「もう夏は諦めている」\n「行ったら自分が辛い」',
  {x:8.2, y:2.25, w:4.2, h:1.8, fontFace:F, fontSize:20, bold:true, color:INK, lineSpacing:40, margin:0});
s.addText('保護者へのヒアリング（1名）', {x:8.2, y:3.85, w:4.2, h:0.3, fontFace:F, fontSize:10.5, color:MUT, margin:0});
note(s,'★ 聞けたのは1名です。そのぶん、聞いた内容は全部そのまま出します。', 5.1);
pg(s,2);

/* 3 決定的な数字 */
s = base(); kicker(s,'02　決定的な数字');
/* ★★ 2026-08-20 事実監査：旧「31超えの日が43%」の43%は 3地点×31日＝93観測値のうちの割合で、
   「31日のうち43%の日」ではなかった。data-sources.md §4b の採用基準（最寄り2地点＝練馬・東京の
   高い方）で日単位に直すと 18/31＝58%。コードは x>=31 なので「超え」ではなく「以上」。
   また 77.1% は母数が全800名ではないため使わないと決定済み（旧版に残っていた）。
   3.8% は原文に母数の明示がないので、母数を断定する見出しは付けない。 */
title(s,[{text:'去年8月、13時に暑さ指数が '},{text:'31以上', options:{color:SUN}},{text:' だった日は '},{text:'58%', options:{color:SUN}}]);
s.addText([{text:'聞いた保護者は「昼食のあと13時ごろに出る」と答えました。'},
           {text:'31以上は「運動は原則中止」の線', options:{bold:true}},{text:'です（日本スポーツ協会）。'}],
  {x:M, y:2.0, w:8.2, h:0.6, fontFace:F, fontSize:16, color:INK, lineSpacing:26, margin:0});
s.addText([
 {text:'暑さ対策が「十分だ」と感じている親は 3.8%', options:{bullet:true, breakLine:true}},
 {text:'自身の子ども時代と比べ「暑さで外遊びができる日や時間が減った」 59.1%', options:{bullet:true}},
], {x:M, y:2.85, w:8.0, h:1.2, fontFace:F, fontSize:15, color:INK2, lineSpacing:28, paraSpaceAfter:6, margin:0});
card(s, 9.0, 1.95, 3.7, 1.9);
s.addText('58', {x:9.2, y:2.15, w:2.6, h:1.1, fontFace:F, fontSize:54, bold:true, color:SUN, margin:0});
s.addText('%', {x:11.3, y:2.62, w:0.6, h:0.5, fontFace:F, fontSize:22, bold:true, color:SUN, margin:0});
s.addText('31日のうち18日', {x:9.2, y:3.32, w:3.3, h:0.35, fontFace:F, fontSize:11, color:MUT, margin:0});
note(s,'暑さ指数：環境省 2025年8月・都内3地点の実測を自分で集計（hour_pick.log）。豊島区内に観測地点がないため、最寄りの練馬・東京の高い方を採り 31日中18日＝58%（3地点いずれかなら20日＝65%）。／31以上の線：日本スポーツ協会「熱中症予防運動指針」第6版 p.15／3.8%・59.1%：医師たちの気候変動啓発プロジェクト／東京科学大学 未来社会創成研究院（2025年7月16日公表・全国・n=800・インターネット調査）', 4.35);
pg(s,3);

/* 4 既存の限界 */
s = base(); kicker(s,'03　既存の限界');
title(s,'道のどこが日陰かは、どちらも教えてくれない');
[['天気予報','今日の暑さは教えてくれる'],['地図アプリ','近い公園は教えてくれる']].forEach((v,i)=>{
  const x = M + i*(5.9+0.35);
  card(s, x, 2.05, 5.9, 1.5);
  s.addText(v[0], {x:x+0.35, y:2.28, w:5.2, h:0.42, fontFace:F, fontSize:19, bold:true, color:INK, margin:0});
  s.addText(v[1], {x:x+0.35, y:2.78, w:5.2, h:0.4, fontFace:F, fontSize:14, color:MUT, margin:0});
});
s.addText([{text:'でも、'},{text:'その公園まで歩く道のどこが日陰か', options:{bold:true}},{text:'は、どちらも教えてくれません。'}],
  {x:M, y:4.05, w:W-2*M, h:0.7, fontFace:F, fontSize:20, color:INK, margin:0});
pg(s,4);

/* 5 解決 */
s = base(); kicker(s,'04　解決');
title(s,'大事なのは気温ではなく、暑さ指数');
/* ★ 事実監査：原典は「盛夏においては樹木の陰に入ると…2程度…低くなる場合があります」
   （環境省まちなかの暑さ対策ガイドライン p.5・一次は富樫ほか2020＝街路樹の実測）。
   「盛夏」「樹木の陰」「場合があります」の3つを落として断定にしていた。
   また WBGT を出しているのは環境省で、気象庁のアメダスは答えに入っていない。 */
s.addText([
 {text:'暑さ指数（WBGT）＝気温だけでなく、湿度と輻射熱（日射・照り返し）を合わせた指標', options:{bullet:true, breakLine:true, bold:true}},
 {text:'盛夏には、木陰に入ると 2程度下がる（環境省ガイドライン）', options:{bullet:true, breakLine:true}},
 {text:'31以上では運動は原則中止（日本スポーツ協会）', options:{bullet:true, breakLine:true}},
 {text:'幼児・学童には、一つ上の温度基準域を当てる（日本生気象学会）', options:{bullet:true}},
], {x:M, y:2.0, w:W-2*M, h:2.1, fontFace:F, fontSize:16, color:INK2, lineSpacing:30, paraSpaceAfter:6, margin:0});
card(s, M, 4.35, W-2*M, 1.35);
s.addText([{text:'この医学的な線に、'},{text:'環境省の暑さ指数の実測',options:{bold:true}},{text:'と、'},
           {text:'3D都市モデルから計算した建物と高架の影',options:{bold:true}},{text:'を重ねました。'}],
  {x:M+0.35, y:4.55, w:W-2*M-0.7, h:0.5, fontFace:F, fontSize:16, color:INK, margin:0});
s.addText('★ 2度下がるのは木陰の値です。こかげが計算しているのは建物と高架の影で、樹木は入っていません（③で自分から言います）。',
  {x:M+0.35, y:5.08, w:W-2*M-0.7, h:0.45, fontFace:F, fontSize:11, color:MUT, margin:0});
pg(s,5);

/* 6 時間 */
s = base(); kicker(s,'05　時間');
title(s,'時間を変えると、日なたを歩く時間が変わる');
[['歩く道の日陰','34% → 72%','13時 → 16時',SHADE],['必要な水分','560 → 322 mL','ほぼ半分',SUN]].forEach((v,i)=>{
  const x = M + i*(3.9+0.3);
  card(s, x, 2.0, 3.9, 1.72);
  s.addText(v[0], {x:x+0.3, y:2.18, w:3.3, h:0.3, fontFace:F, fontSize:11.5, color:MUT, margin:0});
  s.addText(v[1], {x:x+0.3, y:2.52, w:3.4, h:0.6, fontFace:F, fontSize:26, bold:true, color:v[3], margin:0});
  s.addText(v[2], {x:x+0.3, y:3.18, w:3.3, h:0.3, fontFace:F, fontSize:11, color:MUT, margin:0});
});
/* ★ 事実監査：旧「32%／30%」も 93観測値ベースだった。日単位（練馬・東京の高い方）に統一。 */
s.addText([{text:'★ 去年8月は、'},{text:'11時でも暑さ指数が31以上だった日が55%',options:{bold:true}},
           {text:'ありました（15時は48%）。午前中が涼しいわけではありません。'}],
  {x:M, y:3.95, w:8.2, h:0.6, fontFace:F, fontSize:13, color:INK2, lineSpacing:22, margin:0});
s.addText([{text:'★ ただし「待てば良くなる」わけでもありません。'},{text:'14時は13時より水が増えます',options:{bold:true}},
           {text:'（586 対 560 mL）。だから、'},{text:'待つ価値がある時刻と、悪くなる時刻の両方',options:{bold:true}},{text:'を出します。'}],
  {x:M, y:4.55, w:8.2, h:0.75, fontFace:F, fontSize:13, color:INK2, lineSpacing:22, margin:0});
s.addText('日陰率＝出発地から400m圏の歩行空間ネットワークを延長で重みづけ。太陽位置は2026年8月12日で固定／水分量＝その時刻にいちばん良い行き先どうしの比較（13時＝東池袋中央公園560mL、16時＝中池袋公園322mL）。入力の暑さ指数は29.0',
  {x:M, y:5.35, w:8.2, h:0.8, fontFace:F, fontSize:10, color:MUT, lineSpacing:16, margin:0});
s.addImage({path:IMG+'x_hours.png', x:8.9, y:1.95, w:3.75, h:3.67, sizing:{type:'contain', w:3.75, h:3.67}});
pg(s,6);

/* 7 プロダクト */
s = base(); kicker(s,'06　プロダクト');
title(s,'決めるのは時刻と道。行き先は決めません');
/* ★ 2026-08-20：②は案Bへ転換（推奨を出す）。「おすすめは付けません」は転換前の記述。 */
[['① 今日行けるか','暑さ指数31以上のときは、行き先を出しません'],
 ['② 何時に出るか','待つ価値がある時刻と、悪くなる時刻を出します'],
 ['③ どこへ行くか','候補3件を、公園の影の形とあわせて'],
 ['④ どの道で行くか','ここだけは、こかげが決めます']].forEach((v,i)=>{
  const y = 1.95 + i*0.92;
  card(s, M, y, 7.2, 0.78);
  s.addText(v[0], {x:M+0.3, y:y+0.09, w:3.0, h:0.32, fontFace:F, fontSize:15, bold:true, color:INK, margin:0});
  s.addText(v[1], {x:M+3.2, y:y+0.12, w:3.9, h:0.32, fontFace:F, fontSize:12, color:MUT, margin:0});
});
s.addImage({path:IMG+'x_p13.png', x:8.15, y:2.28, w:2.42, h:3.30, sizing:{type:'contain', w:2.42, h:3.30}});
s.addImage({path:IMG+'x_p16.png', x:10.28, y:2.28, w:2.42, h:3.30, sizing:{type:'contain', w:2.42, h:3.30}});
s.addText('13時', {x:8.15, y:1.92, w:2.42, h:0.3, fontFace:F, fontSize:12, bold:true, color:SUN, align:'center', margin:0});
s.addText('16時', {x:10.28, y:1.92, w:2.42, h:0.3, fontFace:F, fontSize:12, bold:true, color:SHADE, align:'center', margin:0});
s.addText('★ 日陰率のパーセントは出しません（現地で確かめたら9〜32ポイントずれていたため）。形だけを見せます。',
  {x:M, y:5.85, w:7.2, h:0.6, fontFace:F, fontSize:11, color:MUT, lineSpacing:18, margin:0});
pg(s,7);

/* 8 デモ */
s = base(); kicker(s,'07　デモ');
title(s,[{text:'1.8% の遠回りで、日なたが '},{text:'31%', options:{color:PARK}},{text:' 減る'}]);
/* ★ 事実監査：これは14時（route_bench_14.json）の値。13時は +3.0%／−27.2% で別の値。 */
s.addImage({path:IMG+'x_route.png', x:4.35, y:1.85, w:4.35, h:4.60, sizing:{type:'contain', w:4.35, h:4.60}});
s.addText([
 {text:'最短の道（赤）と、こかげが選ぶ道（緑）。', options:{breakLine:true}},
 {text:'道路のどちら側の歩道を歩くかまで出します。', options:{breakLine:true, bold:true}},
 {text:'', options:{breakLine:true}},
 {text:'移動の影は、現地に3回立って、3回とも概ね一致しました。ここが唯一「決める」部分です。', options:{}},
], {x:M, y:2.1, w:3.3, h:3.0, fontFace:F, fontSize:13, color:INK2, lineSpacing:22, margin:0});
s.addText('※ ここに60秒のデモ動画を差し込む（無音・テロップ）',
  {x:M, y:6.15, w:6, h:0.35, fontFace:F, fontSize:10.5, color:MUT, margin:0});
s.addText('14時・n=400 の中央値（距離は中央値+1.8%、日なたは中央値−31%。0.5分以上減るのは84%）。図はその一例で、+15m（+3.0%）の遠回りにより日なた 16.6分 → 3.9分、飲ませる量 70mL → 48mL と、中央値より大きく効いた例です。\n\n※ 図は 2026-08-12 時点の旧パラメータ（歩行速度35m/分・建築物LOD1）で描いています。現行の推定は 53.1m/分（3〜5歳連れの実測 n=3）・LOD2実形状585棟です。',
  {x:9.4, y:2.1, w:3.3, h:3.6, fontFace:F, fontSize:9.5, color:MUT, lineSpacing:15, margin:0});
pg(s,8);

/* 9 データ */
s = base(); kicker(s,'08　使ったデータ');
title(s,'5つのデータを重ねています');
[['東京都3Dデジタルマップ（3D都市モデル 豊島区2025）','東京都／CC BY 4.0'],
 ['歩行空間ネットワークデータ（池袋駅周辺）','国土交通省／公共データ利用規約1.0'],
 ['公共施設一覧','豊島区／CC BY 2.1 日本'],
 ['赤ちゃん・ふらっと一覧','東京都福祉局／CC BY 4.0'],
 ['熱中症予防情報（暑さ指数WBGT）','環境省／公共データ利用規約1.0']].forEach((v,i)=>{
  const y = 1.95 + i*0.78;
  card(s, M, y, W-2*M, 0.66);
  s.addText(v[0], {x:M+0.3, y:y+0.14, w:7.6, h:0.38, fontFace:F, fontSize:13.5, bold:true, color:INK, margin:0});
  s.addText(v[1], {x:M+8.0, y:y+0.17, w:3.7, h:0.34, fontFace:F, fontSize:11.5, color:MUT, align:'right', margin:0});
});
/* ★ 事実監査：「いずれも加工して利用」の係り先が検証4件になっていた。
   CC BY の「改変した旨の明記」義務がかかるのは上の5件なので、5件側に付け直す。 */
s.addText([{text:'上記5件は、いずれも加工して利用しています。', options:{bold:true, color:INK2, breakLine:true}},
           {text:'ほかに4件を検証にのみ使用しました（都道の街路樹／アメダス観測データ／緑のオープンデータ／都営バスGTFS-JP）。これらは作品には組み込んでいません。'}],
  {x:M, y:6.0, w:W-2*M, h:0.7, fontFace:F, fontSize:11, color:MUT, lineSpacing:17, margin:0});
pg(s,9);

/* 10 出口 */
s = base(true); kicker(s,'09　出口');
/* ★ 事実監査：「18件」は roadmap.md §5 の書き換え前の件数。取り下げ2件を除いた現行リストは20件以上。
   tasks.md E9（件数と中身の確定）が未了なので、確定するまでは「20件以上」に留める。 */
s.addText([{text:'作ってみて、足りないデータを '},{text:'20件以上', options:{color:PARK}},{text:' 記録しました'}],
  {x:M, y:0.82, w:W-2*M, h:0.9, fontFace:F, fontSize:30, bold:true, color:'FFFFFF', margin:0});
s.addText('「遊具の位置は覚えているから選べる」と言いました。覚えているしかないんです。',
  {x:M, y:1.95, w:W-2*M, h:0.55, fontFace:F, fontSize:19, bold:true, color:'FFFFFF', margin:0});
[['公園の遊具','東京都のカタログには 9,656 のデータセット（2026年8月時点）があるが、1件もない'],
 ['建物の本当の形','上階がすぼむ形。LOD2 は場所によって0件'],
 ['公園の木','都は2026年1月に緑のデータを14種類公開したが、樹林地は公園の開園区域を対象外']].forEach((v,i)=>{
  const y = 2.85 + i*1.0;
  s.addShape(p.ShapeType.roundRect, {x:M, y, w:W-2*M, h:0.86, rectRadius:0.09, fill:{color:'1D2F28'}, line:{color:'2B4038', width:1}});
  s.addText(v[0], {x:M+0.35, y:y+0.13, w:3.2, h:0.34, fontFace:F, fontSize:15, bold:true, color:PARK, margin:0});
  s.addText(v[1], {x:M+3.7, y:y+0.16, w:8.0, h:0.5, fontFace:F, fontSize:12.5, color:'CFE0D8', margin:0});
});
s.addText('精度を上げるのに必要なのは開発ではなく、これらが機械可読で出ることです。',
  {x:M, y:6.15, w:W-2*M, h:0.4, fontFace:F, fontSize:13, color:'9FB5AC', margin:0});
pg(s,10);

const OUT = process.env.KOKAGE_OUT || '../../../../build/kokage_slides_v0.pptx';
p.writeFile({fileName:OUT}).then(()=>console.log('written ->', OUT));
