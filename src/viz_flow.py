import paths
# -*- coding: utf-8 -*-
"""こかげ：データフロー1枚図（SVG）。入力6つ → データ → 6ステップ → 出力

★ 2026-08-31（P26）に v1c へ更新しました。旧版（2026-08-12 作成）との違い：
  ・例が「東池袋中央公園 593mL・公園の日陰率100%」だった。これは**円近似が
    サンシャインシティのLOD1の箱の中に入っていた頃の、誤った答え**（tasks.md ★−1）。
    → 同じ公園・同じ時刻で v1c を回した実値（577mL・日陰率72.1%）に差し替え。
  ・歩行速度 35 m/分 → **53.1 m/分**（2026-08-15 の実測に更新済みだった）
  ・入力の「ベビーカー」は v1c で廃止。代わりに「遊び方（METs）」が入力
  ・LOD2 実形状585棟・東京都の公園ポリゴン・給水スポットが未記載だった
  ・アメダスは「くもり係数 f の入力」として描いていたが、**時別値が推計しか無く
    答えには使っていない**（検証のみ）。灰色の列へ移動
  ・歩行空間ネットワークのライセンス表記が「公共データ利用規約」だった → CC BY 4.0
"""
W, H = 1400, 1000
INK, INK2, MUT, HAIR = '#0b0b0b', '#52514e', '#898781', '#e1e0d9'
SUN, SHADE, DECK, PARK = '#eb6834', '#2a78d6', '#4a3aa7', '#1baf7a'
p = []
L = []   # 線は別レイヤ（ボックスの下に敷く）
def rect(x,y,w,h,fill='#fcfcfb',stroke=HAIR,sw=1.2,r=10,op=1):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def txt(x,y,s,size=13,fill=INK,w=400,anchor='start',op=1):
    s=s.replace('&','&amp;').replace('<','&lt;')
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{w}" text-anchor="{anchor}" opacity="{op}">{s}</text>')
def link(x1,y1,x2,y2,col=MUT,sw=1.6,dash=None,op=.85):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    mx=(x1+x2)/2
    L.append(f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" fill="none" stroke="{col}" stroke-width="{sw}"{d} opacity="{op}"/>')

# ---- 列の位置
X1, X2, X3, X4 = 40, 330, 700, 1120
CW1, CW2, CW3, CW4 = 240, 320, 360, 240

txt(X1, 34, 'こかげ｜入力からmLが出るまで', 21, INK, 800)
txt(X1, 56, '2026-08-12 13:00・池袋駅東口発の「577mL」を例に（v1c の実測値）。灰色は取得済みだが答えには使っていないデータ', 12.5, INK2)

for x,w,lab in ((X1,CW1,'入力（利用者に聞く6つ）'),(X2,CW2,'データ'),(X3,CW3,'計算（6ステップ）'),(X4,CW4,'出力')):
    txt(x, 88, lab, 12, MUT, 700)

# ---- 入力
INP = [('出発地','池袋駅東口'),('出発時刻','13:00'),('目的','できれば屋外'),
       ('滞在時間','60分'),('遊び方','走り回る中心（METs 4.90）'),('体重','15kg')]
iy = []
for i,(k,v) in enumerate(INP):
    y = 104 + i*52
    rect(X1, y, CW1, 42)
    txt(X1+12, y+18, k, 13, INK, 700); txt(X1+12, y+34, v, 12, INK2)
    iy.append(y+21)
# 自動で入る2つ
y = 104 + 6*52 + 8
rect(X1, y, CW1, 80, '#f4f4f1', HAIR)
txt(X1+12, y+18, '★ 聞かずに自動で入る2つ', 12, MUT, 700)
txt(X1+12, y+36, '暑さ指数 29.0（環境省API）', 12, INK2)
txt(X1+12, y+51, '　練馬と東京の高い方', 11, MUT)
txt(X1+12, y+69, 'くもり係数 f = 1.0 固定（晴天前提）', 12, INK2)
auto_y = [y+32, y+66]

# ---- データ
DATA = [('PLATEAU 建築物 LOD1','21,381棟・高さ付き',1),
        ('★ PLATEAU 建築物 LOD2','585棟・実形状 面128,012枚',1),
        ('PLATEAU 橋梁 brid','高架デッキ679面',1),
        ('PLATEAU 地盤高 dem','51,910点',1),
        ('歩行空間ネットワーク','1,887ノード / 2,196リンク',1),
        ('豊島区 都市公園','62件・供用済面積',1),
        ('★ 東京都 公園ポリゴン','162件・公園の「形」',1),
        ('豊島区 公共施設一覧','558件・座標',1),
        ('赤ちゃん・ふらっと','34件→28件を突合',1),
        ('環境省 WBGT','ゲートと基準値',1),
        ('★ 東京都 給水スポット','836件→この範囲は2か所',1),
        ('気象庁 アメダス','検証のみ（時別値が推計）',0),
        ('都道の街路樹 4,687本','検証のみ（都道だけ）',0),
        ('PLATEAU frn 4,690点','ベンチ0・水飲み0',0),
        ('都営バス GTFS-JP','公園の位置説明のみ',0)]
dy=[]
for i,(k,v,on) in enumerate(DATA):
    y = 104 + i*52
    rect(X2, y, CW2, 42, '#fcfcfb' if on else '#f4f4f1', HAIR, op=1 if on else .75)
    txt(X2+12, y+18, k, 12.5, INK if on else MUT, 700)
    txt(X2+12, y+34, v, 11.5, INK2 if on else MUT)
    dy.append(y+21)

# ---- ステップ
STEP = [('① 暑さ指数のゲート','29.0 < 31.0 → 屋外の行き先を出してよい',72),
        ('② 影を作る','太陽高度 63.5° → L = 高さ×0.499\nLOD2は実形状／LOD1は箱の側面掃引／高架は平行移動',88),
        ('③ グラフを組む','2,196リンクを2m刻みでサンプリング → 日陰率\nコスト＝発汗率(mL/分)×分×日なた/日陰の按分',88),
        ('④ ダイクストラ','weight=cost（距離ではなくmL）\n候補41件（屋外24・屋内17）それぞれへ最小コスト経路',88),
        ('⑤ 経路の内訳','670m ÷ 53.1m/分 = 12.6分 ＋ 信号待ち2.0分（4回）\n日なた4.2分 ＋ 日陰8.4分／公園の縁まで さらに73m',88),
        ('⑥ 滞在を足す','公園の日陰率72.1% → 60分×7.38 = 443mL\nスコア＝往復134＋滞在443',88)]
sy=[]; y=104
for k,v,h in STEP:
    rect(X3, y, CW3, h, '#fcfcfb', HAIR, 1.6)
    txt(X3+14, y+22, k, 14, INK, 800)
    for j,line in enumerate(v.split('\n')):
        txt(X3+14, y+42+j*16, line, 11.5, INK2)
    sy.append(y+h/2); 
    if h>72: sy[-1]=y+h/2
    y += h + 12
step_top=[104]; yy=104
for k,v,h in STEP:
    step_top.append(yy); yy+=h+12

# ---- 出力
oy = 250
rect(X4, oy, CW4, 210, '#f2f8f2', '#bfe3bf', 1.6)
txt(X4+16, oy+30, '東池袋中央公園', 17, INK, 800)
txt(X4+16, oy+66, '577', 42, INK, 800); txt(X4+96, oy+66, 'mL', 17, INK, 700)
txt(X4+16, oy+92, '往復 134 ＋ 滞在 443', 12.5, INK2)
txt(X4+16, oy+114, '片道 742m ／ 35区間', 12, INK2)
txt(X4+16, oy+134, '経路の日陰率 66.7%', 12, SHADE, 700)
txt(X4+16, oy+154, '公園の日陰率 72.1%', 12, PARK, 700)
txt(X4+16, oy+176, '15分ごとに給水', 12, INK2)
txt(X4+16, oy+196, '精度 L2（縁まで73m）', 11.5, MUT)

rect(X4, oy+230, CW4, 92, '#fff4f0', '#f3c3ae', 1.4)
txt(X4+16, oy+254, 'WBGT 31 以上なら', 12.5, '#a82a2a', 700)
txt(X4+16, oy+276, '①で止まり、行き先ではなく', 12, INK2)
txt(X4+16, oy+294, '「今日は外に出ない方が', 12, INK2)
txt(X4+16, oy+312, 'いいです」を返す', 12, INK2)

# ---- 線：入力 → ステップ
E1, E2 = X1+CW1, X3
link(E1, iy[0], X3, step_top[4]+20)                      # 出発地→④
link(E1, iy[1], X3, step_top[2]+20, SUN, 2.0)            # 時刻→②
link(E1, iy[2], X3, step_top[4]+40, PARK, 1.8)           # 目的→④
link(E1, iy[2], X3, step_top[6]+30, PARK, 1.8)           # 目的→⑥
link(E1, iy[3], X3, step_top[6]+45, 2.0 and PARK, 2.0)   # 滞在→⑥
link(E1, iy[4], X3, step_top[3]+30)                      # ベビーカー→③
link(E1, iy[5], X3, step_top[3]+50)                      # 体重→③
link(E1, auto_y[0], X3, step_top[1]+20, '#d03b3b', 1.8)  # WBGT→①
link(E1, auto_y[1], X3, step_top[3]+60, DECK, 1.6, '5 4')# f→③

# ---- 線：データ → ステップ
D2 = X2+CW2
for i,(k,v,on) in enumerate(DATA):
    if not on: continue
    tgt = {0:1,1:1,2:1,3:1,4:2,5:3,6:3,7:3,8:3,9:0,10:4}[i]   # ステップ index
    col = {0:MUT,1:MUT,2:DECK,3:MUT,4:MUT,5:PARK,6:PARK,7:PARK,8:PARK,9:'#d03b3b',10:DECK}[i]
    link(D2, dy[i], X3, step_top[tgt+1]+26, col, 1.5, None, .6)

# ---- 線：⑥ → 出力
link(X3+CW3, step_top[6]+40, X4, oy+70, PARK, 2.4)
link(X3+CW3, step_top[1]+20, X4, oy+270, '#d03b3b', 2.0, '5 4')

# ---- 凡例
ly = H-92
txt(X1, ly, '線の色：', 12, MUT, 700)
for i,(c,lab) in enumerate([(SUN,'時刻＝影の形'),(SHADE,'—'),(DECK,'高架・くもり'),(PARK,'目的・候補地'),('#d03b3b','WBGT'),(MUT,'その他')]):
    if lab=='—': continue
    x = X1+60+i*130
    p.append(f'<line x1="{x}" y1="{ly-4}" x2="{x+22}" y2="{ly-4}" stroke="{c}" stroke-width="2.4"/>')
    txt(x+28, ly, lab, 12, INK2)
txt(X1, H-58, 'データ（いずれも丸山倫太朗が加工して利用）：3D都市モデル（Project PLATEAU）豊島区2025 建築物・橋梁・地盤高（東京都／CC BY 4.0）／歩行空間ネットワークデータ 池袋駅周辺（国土交通省／CC BY 4.0）', 10.5, MUT)
txt(X1, H-42, '　　　　／公共施設一覧・都市公園（豊島区／CC BY 2.1 日本）／赤ちゃん・ふらっと一覧（東京都福祉局／CC BY 4.0）／暑さ指数WBGT（環境省／CC BY 4.0）', 10.5, MUT)
txt(X1, H-26, '　　　　／Tokyowater Drinking Station 一覧（東京都水道局／CC BY 4.0）／公園・緑地等 緑のオープンデータ GISデータ（東京都都市整備局／クリエイティブ・コモンズ 表示（CC BY））　　日影は 2026-08-12 の太陽位置による計算値', 10.5, MUT)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'style="background:#ffffff;font-family:system-ui,-apple-system,\'Hiragino Sans\',sans-serif">'
       + ''.join(L) + ''.join(p) + '</svg>')
open(paths.build('dataflow.svg'),'w',encoding='utf-8').write(svg)
print('ok', len(svg)//1024, 'KB')
