import paths
# -*- coding: utf-8 -*-
"""こかげ：データフロー1枚図（SVG）。入力6つ → データ9種 → 6ステップ → 出力"""
W, H = 1400, 900
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
txt(X1, 56, '2026-08-12 14:00・都電雑司ヶ谷駅発の「593mL」を例に。灰色は取得済みだが今回使わないデータ', 12.5, INK2)

for x,w,lab in ((X1,CW1,'入力（利用者に聞く6つ）'),(X2,CW2,'データ'),(X3,CW3,'計算（6ステップ）'),(X4,CW4,'出力')):
    txt(x, 88, lab, 12, MUT, 700)

# ---- 入力
INP = [('出発地','都電雑司ヶ谷駅'),('出発時刻','14:00'),('目的','外で遊ばせたい'),
       ('滞在時間','60分'),('ベビーカー','なし'),('体重','15kg')]
iy = []
for i,(k,v) in enumerate(INP):
    y = 104 + i*52
    rect(X1, y, CW1, 42)
    txt(X1+12, y+18, k, 13, INK, 700); txt(X1+12, y+34, v, 12, INK2)
    iy.append(y+21)
# 自動で入る2つ
y = 104 + 6*52 + 8
rect(X1, y, CW1, 62, '#f4f4f1', HAIR)
txt(X1+12, y+18, '★ 聞かずに自動で入る2つ', 12, MUT, 700)
txt(X1+12, y+35, 'WBGT 29.0（環境省API）', 12, INK2)
txt(X1+12, y+51, 'くもり係数 f = 1.0（アメダス日照）', 12, INK2)
auto_y = [y+30, y+50]

# ---- データ
DATA = [('PLATEAU 建築物 LOD1','21,378棟・高さ付き',1),
        ('PLATEAU 橋梁 brid','高架デッキ679面',1),
        ('PLATEAU 地盤高','51,910点',1),
        ('歩行空間ネットワーク','1,887ノード / 2,196リンク',1),
        ('都市公園（related.zip）','62件・供用済面積',1),
        ('豊島区 公共施設一覧','558件・座標',1),
        ('赤ちゃん・ふらっと','34件→28件を突合',1),
        ('環境省 WBGT','ゲートと基準値',1),
        ('気象庁 アメダス','日照時間 → f',1),
        ('都道の街路樹 4,687本','M7・未実装',0),
        ('PLATEAU frn 4,690点','柵・壁3,003・v2',0),
        ('都営バス GTFS-JP','v2',0)]
dy=[]
for i,(k,v,on) in enumerate(DATA):
    y = 104 + i*54
    rect(X2, y, CW2, 44, '#fcfcfb' if on else '#f4f4f1', HAIR, op=1 if on else .75)
    txt(X2+12, y+19, k, 12.5, INK if on else MUT, 700)
    txt(X2+12, y+35, v, 11.5, INK2 if on else MUT)
    dy.append(y+22)

# ---- ステップ
STEP = [('① WBGTゲート','29.0 < 31.0 → 屋外を出してよい',72),
        ('② 影を作る','L = 高さ ÷ tan(53.6°) = 高さ×0.740\n建物＝側面掃引あり／高架＝平行移動のみ',88),
        ('③ グラフを組む','リンクを2m刻みでサンプリング → 日陰率\nコスト＝発汗率(mL/分)×分×日なた/日陰の按分',88),
        ('④ ダイクストラ','weight=cost（距離ではなくmL）\n候補42件それぞれへ最小コスト経路',88),
        ('⑤ 経路の内訳','849m ÷ 35m/分 = 24.2分 ＋ 信号1.5分\n日なた29.2 ＋ 日陰44.0 ＋ 待ち3.6 = 片道76.8',88),
        ('⑥ 滞在を足す','公園の日陰率100% → 60分×7.33 = 440mL\nスコア＝往復154＋滞在440',88)]
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
txt(X4+16, oy+66, '593', 42, INK, 800); txt(X4+96, oy+66, 'mL', 17, INK, 700)
txt(X4+16, oy+92, '往復 154 ＋ 滞在 440', 12.5, INK2)
txt(X4+16, oy+114, '片道 849m ／ 38区間', 12, INK2)
txt(X4+16, oy+134, '経路の日陰率 71.8%', 12, SHADE, 700)
txt(X4+16, oy+154, '公園の日陰率 100%', 12, PARK, 700)
txt(X4+16, oy+176, '15分ごとに給水', 12, INK2)
txt(X4+16, oy+196, '精度 L1（実経路）', 11.5, MUT)

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
    tgt = {0:1,1:1,2:1,3:2,4:3,5:3,6:3,7:0,8:2}[i]     # ステップ index
    col = {0:MUT,1:DECK,2:MUT,3:MUT,4:PARK,5:PARK,6:PARK,7:'#d03b3b',8:DECK}[i]
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
txt(X1, H-44, 'データ：東京都3Dデジタルマップ（PLATEAU仕様）豊島区2025 建築物・橋梁（東京都／CC BY 4.0）／歩行空間ネットワークデータ 池袋駅周辺（国土交通省／公共データ利用規約（第1.0版））', 10.5, MUT)
txt(X1, H-26, '　　　　／豊島区 公共施設一覧・都市公園（豊島区）／赤ちゃん・ふらっと一覧（東京都福祉局）／暑さ指数WBGT（環境省）／アメダス（気象庁）　　日影は 2026-08-12 の太陽位置による計算値', 10.5, MUT)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'style="background:#ffffff;font-family:system-ui,-apple-system,\'Hiragino Sans\',sans-serif">'
       + ''.join(L) + ''.join(p) + '</svg>')
open(paths.build('dataflow.svg'),'w',encoding='utf-8').write(svg)
print('ok', len(svg)//1024, 'KB')
