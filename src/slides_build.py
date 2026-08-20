# -*- coding: utf-8 -*-
"""2分プレゼンの骨格版スライドを 16:9 の PDF に書き出す（2026-08-20・D3）
   原稿は slides.md v3。作り込みは 8/22〜23。ここは「提出できる状態」を作るのが目的。

★ 2026-08-20 夜③ の改訂（slides.md v3 §6 の6件）
   1. P06 ②「おすすめは付けません」→ 案B（待つ価値がある時刻／悪くなる時刻）に差し替え
   2. P02 の 77.1% を削除（母数が全800名ではない。pitch.md §5-② の誤引用の罠）
   3. P02 の見出しを、原稿 30-45 で実際に口に出す「43%」に合わせた（3.8% は箇条書きへ）
   4. P06 タイトルを「決めるのは時刻と道。行き先は決めません」に（②が推奨に転換したため）
   5. P04「環境省と気象庁の実測」→「環境省の暑さ指数の実測」（アメダスは答えに入っていない）
   6. P05 の頻度に「去年8月は」を付け、案Bの非単調性（14時は13時より悪い）を追記
   ★ 画像は paths.fig() から読む（従来は /tmp/cap 直書きで、手元では動かなかった）
"""
import base64, os, pathlib
import paths
from playwright.sync_api import sync_playwright

FIG = pathlib.Path(os.environ.get('KOKAGE_FIG') or paths.FIG)
def b64(p):
    return 'data:image/png;base64,' + base64.b64encode((FIG/p).read_bytes()).decode()

def make_route_crop():
    """route_compare.png（1680×1778）を、凡例・2本の経路・縮尺だけに切り出す。
    ★ なぜ要るか：submit_cap3_route.png は 1600×900 のスライド1枚で、
      これをスライドの中に貼ると「スライドの中のスライド」になって地図が潰れる。
      P07 は2本の線が見えることが全てなので、地図そのものを縦長のまま置く。
    ★ 切り出し座標は route_compare.png の版に依存する。図を作り直したら取り直すこと
      （赤・緑の画素の外接矩形を見て決めた。2026-08-20）。"""
    src, dst = FIG / 'route_compare.png', FIG / 'route_compare_crop.png'
    if dst.exists() or not src.exists():
        return
    from PIL import Image
    Image.open(src).convert('RGB').crop((25, 105, 1200, 1612)).save(dst)


make_route_crop()

CAP3 = b64('submit_cap3_route.png')            # 提出用キャプチャ（1600×900・見出しつき）
ROUTE = b64('route_compare_crop.png')          # ★ P07 用。route_compare.png を経路まわりに切り出したもの
HOURS, P13, P16 = b64('s2_hours.png'), b64('s3_parks13.png'), b64('s4_parks16.png')

SLIDES = [
 # (kicker, title, body_html, right_html)
 ('', '<span class="lg"><i class="mark"></i><span class="lgt">こ<em>か</em>げ</span></span>',
  '<p class="lead">建物の影から、子連れの夏の外出を変える</p>'
  '<p class="meta">個人参加／丸山 倫太朗　　私にも小さい子がいます</p>', ''),

 ('01　課題', 'この酷暑で、子どもをどこで遊ばせるか',
  '<ul class="big"><li>親の大きな悩みです。私も、この暑さで公園に連れて行っていいのかと迷います</li>'
  '<li>屋内にしても、<b>道中が暑い</b></li>'
  '<li class="quote">「もう夏は諦めている」<br>「行ったら自分が辛い」</li>'
  '<li>水の量も悩ましい</li></ul>', ''),

 # ★★ 2026-08-20 の事実監査で直した最重要箇所。
 #   旧「31超えの日が43%」の 43% は hour_pick.py の p31＝3地点×31日＝93観測値のうちの割合で、
 #   「31日のうち43%の日」ではなかった。日単位に直すと、data-sources.md §4b が採ると決めた
 #   「最寄り2地点（練馬・東京）の高い方」で 18/31＝58%。>=31 なので「超え」ではなく「以上」。
 ('02　決定的な数字', '去年8月、13時に暑さ指数が <em>31以上</em> だった日は <em>58%</em>',
  '<p class="lead">聞いた保護者は「昼食のあと13時ごろに出る」と答えました。'
  '<b>31以上は「運動は原則中止」の線</b>です（日本スポーツ協会）。</p>'
  '<ul><li>暑さ対策が「十分だ」と感じている親は <b>3.8%</b></li>'
  '<li>自身の子ども時代と比べ「暑さで外遊びができる日や時間が減った」<b>59.1%</b></li></ul>'
  '<p class="src">暑さ指数：環境省 2025年8月・都内3地点の実測を自分で集計（hour_pick.log）。'
  '豊島区内に観測地点がないため、最寄りの練馬・東京の高い方を採り、31日中18日＝58%（3地点いずれかなら20日＝65%）／'
  '31以上の線：日本スポーツ協会「熱中症予防運動指針」第6版 p.15／'
  '3.8%・59.1%：医師たちの気候変動啓発プロジェクト／東京科学大学 未来社会創成研究院（2025年7月16日公表・全国・n=800）</p>', ''),

 ('03　既存の限界', '道のどこが日陰かは、どちらも教えてくれない',
  '<div class="two"><div class="box"><h3>天気予報</h3><p>今日の暑さは教えてくれる</p></div>'
  '<div class="box"><h3>地図アプリ</h3><p>近い公園は教えてくれる</p></div></div>'
  # ★「どのデータにも入っていません」→ 原稿（slides.md 45-55）の「どちらも教えません」に合わせた。
  #   「どのデータにも無い」は交通量のときと同じ型の言い過ぎになる（pitch.md「書かないと決めたこと」）。
  '<p class="big2">でも、<b>その公園まで歩く道のどこが日陰か</b>は、どちらも教えてくれません。</p>', ''),

 ('04　解決', '大事なのは気温ではなく、暑さ指数',
  # ★ 事実監査：原典は「盛夏に樹木の陰に入ると2程度低くなる場合があります」（環境省ガイドライン p.5）。
  #   限定を落として断定にすると、一次文献（富樫ほか2020＝街路樹の実測）まで辿られたときに崩れる。
  '<ul class="big"><li><b>暑さ指数（WBGT）</b>＝気温だけでなく<b>湿度と輻射熱（日射・照り返し）</b>を合わせた指標</li>'
  '<li>盛夏には、<b>木陰に入ると2程度下がる</b>（環境省ガイドライン）</li>'
  '<li><b>31以上では運動は原則中止</b>（日本スポーツ協会）／'
  '<b>幼児・学童には一つ上の温度基準域を当てる</b>（日本生気象学会）</li></ul>'
  '<p class="big2">この医学的な線に、<b>環境省の暑さ指数の実測</b>と、<b>3D都市モデルから計算した建物と高架の影</b>を重ねました。</p>'
  '<p class="note">★ 2度下がるのは木陰の値です。'
  '<b>こかげが計算しているのは建物と高架の影で、樹木は入っていません</b>（③で自分から言います）。</p>', ''),

 ('05　時間', '時間を変えると、日なたを歩く時間が変わる',
  '<div class="kpi"><div><span>歩く道の日陰</span><b>34% → 72%</b><small>13時 → 16時</small></div>'
  '<div><span>必要な水分</span><b>560 → 322 mL</b><small>ほぼ半分</small></div></div>'
  # ★ 事実監査：旧「32%／30%」も P02 と同じ 93観測値ベースだった。日単位（練馬・東京の高い方）に統一。
  '<p class="note">★ <b>去年8月は</b>、11時でも暑さ指数が31以上だった日が <b>55%</b> ありました（15時は48%）。'
  '午前中が涼しいわけではありません。<br>'
  '★ ただし「待てば良くなる」わけでもありません。<b>14時は13時より水が増えます</b>（586 対 560 mL）。'
  'だから、<b>待つ価値がある時刻と、悪くなる時刻の両方</b>を出します。</p>'
  '<p class="src">日陰率：出発地から400m圏の歩行空間ネットワークを延長で重みづけ。太陽位置は2026年8月12日で固定／'
  '水分量：その時刻にいちばん良い行き先どうしの比較（13時＝東池袋中央公園560mL、16時＝中池袋公園322mL）。'
  '入力の暑さ指数は29.0／31以上だった日の割合：環境省 2025年8月・練馬と東京の高い方</p>',
  f'<img src="{HOURS}" class="shot tall">'),

 ('06　プロダクト', '決めるのは時刻と道。行き先は決めません',
  '<ol class="steps"><li><b>今日行けるか</b>　暑さ指数31以上のときは<b>行き先を出しません</b></li>'
  '<li><b>何時に出るか</b>　11〜16時の6枚。<b>待つ価値がある時刻と、悪くなる時刻</b>を出します</li>'
  '<li><b>どこへ行くか</b>　候補3件を<b>公園の影の形</b>とあわせて</li>'
  '<li><b>どの道で行くか</b>　ここだけは、こかげが決めます</li></ol>'
  '<p class="note">③は「遊具の位置は覚えているから、影の形が分かれば自分で選べる」という保護者の言葉から。'
  '<b>日陰率のパーセントは出しません</b>（現地で確かめたら9〜32ポイントずれていたため）。</p>',
  f'<div class="pair"><img src="{P13}" class="shot"><img src="{P16}" class="shot"></div>'),

 # ★ この1枚が Before/After を作れる唯一の場所（slides.md §4 削ってはいけない #2）。
 #   図を右カラム（400px）に置くと2本の線が潰れるので、本文カラムいっぱいに置く。
 ('07　デモ', '最短の道と、こかげが選ぶ道',
  '<p class="big2" style="margin-top:0"><b>1.8% の遠回りで、往復の日なたが 31% 減ります</b><br>'
  '<span class="tiny">14時・n=400 の中央値。距離は中央値 +1.8%、日なたは中央値 −31%。0.5分以上減るのは 84%</span></p>'
  # ★ 事実監査：原典（data-sources.md §1d-3/§1d-4）はいずれも「概ね一致」。断定は原典より強い。
  '<p class="big2">道路の<b>どちら側の歩道</b>を歩くかまで出します。'
  '移動の影は、<b>現地に3回立って、3回とも概ね一致</b>しました。</p>'
  '<p class="note">※ 図は一例で、この経路では +15m（+3.0%）の遠回りにより'
  '日なた 16.6分 → 3.9分、飲ませる量 70mL → 48mL と、中央値より大きく効いています。<br>'
  '<span class="tiny">※ 図は 2026-08-12 時点の旧パラメータ（歩行速度35m/分・建築物LOD1）で描いています。'
  '現行の推定は 53.1m/分（3〜5歳連れの実測 n=3）・LOD2実形状585棟です。<br>'
  '※ ここに60秒のデモ動画を差し込む（無音・テロップ）</span></p>',
  f'<img src="{ROUTE}" class="shot tall">'),

 ('08　使ったデータ', '5つのデータを重ねています',
  '<ul class="data"><li>東京都3Dデジタルマップ（3D都市モデル 豊島区2025）／東京都／CC BY 4.0</li>'
  '<li>歩行空間ネットワークデータ（池袋駅周辺）／国土交通省／公共データ利用規約1.0</li>'
  '<li>公共施設一覧／豊島区／CC BY 2.1 日本</li>'
  '<li>赤ちゃん・ふらっと一覧／東京都福祉局／CC BY 4.0</li>'
  '<li>熱中症予防情報（暑さ指数WBGT）／環境省／公共データ利用規約1.0</li></ul>'
  # ★ 事実監査：「いずれも加工して利用」の係り先が検証4件になっていた。
  #   CC BY の「改変した旨の明記」義務がかかるのは上の5件なので、5件側に付け直す。
  '<p class="note"><b>上記5件は、いずれも加工して利用しています。</b><br>'
  'ほかに4件を<b>検証にのみ使用</b>しました（都道の街路樹／アメダス／緑のオープンデータ／都営バスGTFS）。'
  '<span class="tiny">これらは作品には組み込んでいません。</span></p>', ''),

 # ★ 事実監査：「18件」は roadmap.md §5 の書き換え前の件数。現行リストは取り下げ2件を除いて20件以上。
 #   tasks.md E9（件数と中身の確定）が未了なので、確定するまでは「20件以上」に留める。
 ('09　出口', '作ってみて、足りないデータを 20件以上 記録しました',
  '<p class="big2"><b>「遊具の位置は覚えているから選べる」と言いました。覚えているしかないんです。</b></p>'
  '<ul class="big"><li>東京都のオープンデータカタログには <b>9,656</b> のデータセットがありますが'
  '<span class="tiny">（2026年8月時点）</span>、<b>公園の遊具は1件もありません</b></li>'
  '<li><b>建物の本当の形</b>も足りません（上階がすぼむ形。LOD2は場所によって0件）</li>'
  '<li><b>公園の木</b>も。都は2026年1月に緑のデータを14種類公開しましたが、'
  '<b>樹林地は公園の開園区域を対象外</b>にしています</li></ul>'
  '<p class="note">精度を上げるのに必要なのは開発ではなく、これらが機械可読で出ることです。</p>', ''),
]

CSS = """
@page { size: 1280px 720px; margin: 0; }
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Noto Sans CJK JP","Noto Sans JP",sans-serif;color:#0b0b0b}
.s{width:1280px;height:720px;padding:56px 64px;position:relative;background:#f6f6f3;
page-break-after:always;overflow:hidden;display:flex;flex-direction:column}
.s.cover{justify-content:center;background:#fcfcfb}
.kicker{font-size:16px;letter-spacing:.14em;color:#898781;font-weight:700;margin-bottom:14px}
h2{font-size:40px;line-height:1.28;margin-bottom:22px;letter-spacing:-.01em}
h2 em{font-style:normal;color:#eb6834}
.lg{font-size:104px;font-weight:700;letter-spacing:.02em;display:flex;align-items:center;gap:26px}
.lg em{font-style:normal;color:#1baf7a}
/* ★ .lg は flex なので、文字は必ず .lgt で包むこと。裸のテキストノードは
   1文字ずつ flex アイテムになり、gap の分だけ字間が開く（2026-08-20 に踏んだ）。*/
.lgt{display:block}
/* 画面 v1b と同じロゴマーク（左上＝日なた／右下＝日陰の45度分割） */
.lg i.mark{width:84px;height:84px;border-radius:22px;flex:none;
background:linear-gradient(135deg,#eb6834 0 50%,#2a78d6 50% 100%)}
/* 07 デモ：2本のルート比較を本文カラムいっぱいに置く */
.hero{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;margin:6px 0 4px}
.hero img{max-width:100%;max-height:100%;object-fit:contain;
border:1px solid #e1e0d9;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.10);background:#fff}
.lead{font-size:28px;color:#52514e;margin-top:22px}
.meta{font-size:18px;color:#898781;margin-top:16px}
.cols{display:flex;gap:36px;flex:1;min-height:0}
.left{flex:1;min-width:0}
.right{width:400px;display:flex;gap:12px;align-items:flex-start;justify-content:center}
.right.full{width:560px}
ul,ol{margin-left:1.15em}
li{font-size:21px;line-height:1.75;color:#2a2a28;margin-bottom:8px}
ul.big li{font-size:23px}
li.quote{list-style:none;margin:16px 0 16px -1.15em;padding:14px 20px;background:#fff;border-left:5px solid #1baf7a;
font-size:25px;font-weight:700;line-height:1.6}
.big2{font-size:24px;line-height:1.7;margin-top:18px;color:#2a2a28}
.note{font-size:17px;line-height:1.7;color:#52514e;margin-top:18px}
.tiny{font-size:15px;color:#898781}
.src{font-size:15px;color:#898781;margin-top:20px;line-height:1.6}
.two{display:flex;gap:20px;margin-top:8px}
.box{flex:1;background:#fff;border:1px solid #e1e0d9;border-radius:12px;padding:18px 22px}
.box h3{font-size:22px;margin-bottom:6px}
.box p{font-size:18px;color:#52514e}
.kpi{display:flex;gap:22px;margin-top:6px}
.kpi>div{flex:1;background:#fff;border:1px solid #e1e0d9;border-radius:14px;padding:20px 22px}
.kpi span{display:block;font-size:16px;color:#898781}
.kpi b{display:block;font-size:38px;margin:6px 0 2px;letter-spacing:-.02em}
.kpi small{font-size:15px;color:#898781}
ol.steps li{font-size:22px;line-height:1.7;margin-bottom:10px}
ul.data li{font-size:18px;line-height:1.9}
.shot{border:1px solid #e1e0d9;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.10);background:#fff;
max-width:100%;object-fit:cover;object-position:top}
.shot.tall{max-height:470px}
.pair img{max-height:430px}
.pair{display:flex;gap:12px}
.shot.wide{width:100%;max-height:430px;object-fit:contain}
.pg{position:absolute;right:34px;bottom:22px;font-size:14px;color:#b6b4ad}
"""

def slide_html(i, s):
    k, t, body, right = s
    cover = ' cover' if i == 0 else ''
    kick = f'<div class="kicker">{k}</div>' if k else ''
    head = f'<h2>{t}</h2>' if i else f'<div>{t}</div>'
    if right:
        inner = f'<div class="cols"><div class="left">{body}</div><div class="right">{right}</div></div>'
    else:
        inner = body
    return f'<section class="s{cover}">{kick}{head}{inner}<div class="pg">{i+1} / {len(SLIDES)}</div></section>'

html = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>' + CSS + '</style></head><body>'
        + ''.join(slide_html(i, s) for i, s in enumerate(SLIDES)) + '</body></html>')
HTML_PATH = pathlib.Path(paths.build('kokage_slides.html'))
PDF_PATH = paths.build('kokage_slides_v0.pdf')
HTML_PATH.write_text(html, encoding='utf-8')

errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 720})
    pg.on('console', lambda m: errs.append(m.type + ':' + m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
    pg.goto(HTML_PATH.as_uri())
    pg.wait_for_timeout(900)
    pg.pdf(path=PDF_PATH, width='1280px', height='720px',
           print_background=True, margin={'top':'0','bottom':'0','left':'0','right':'0'})
    # 1枚ずつPNGでも出す（目視チェック用）
    for i in range(len(SLIDES)):
        pg.screenshot(path=paths.build('slide_%02d.png' % (i + 1)),
                      clip={'x': 0, 'y': i * 720, 'width': 1280, 'height': 720}, full_page=True)
    b.close()
print('pdf done ->', PDF_PATH)
print('console/page errors:', errs if errs else 'なし')
