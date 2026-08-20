import paths
import sys, json, math; import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from matplotlib.patches import Polygon as MP
from matplotlib.lines import Line2D
from datetime import datetime
from shapely.geometry import box as sbox
from shadow import load_buildings, load_links, shadow, sun, TZ, FWD
import bridge
fp='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
plt.rcParams['font.family']=fm.FontProperties(fname=fp).get_name()

B=load_buildings('ikebukuro_bldg_lod0.json'); L=load_links('ikebukuro_link.geojson')
E=json.load(open('bridge_eval.json')); r0,r1=E['r0'],E['r1']
decks=bridge.load_decks()
dt=pd.DatetimeIndex([datetime(2026,8,12,14,0,tzinfo=TZ)]); alt,az=sun(dt)
bs=bridge.deck_shadow(decks,alt,az); ud=bridge.under_deck(decks)

CX,CY=FWD.transform(139.71700,35.73050); R=330
bx=sbox(CX-R,CY-R,CX+R,CY+R)
fig,ax=plt.subplots(figsize=(12,12.8))
for p,h,_ in B:
    if p.intersects(bx):
        ax.add_patch(MP(np.array(p.exterior.coords),closed=True,facecolor='#eceef1',edgecolor='#d3d8de',lw=.3,zorder=1))
def draw(g,**kw):
    gs=list(g.geoms) if hasattr(g,'geoms') else [g]
    for p in gs:
        if p.is_empty or not p.intersects(bx): continue
        ax.add_patch(MP(np.array(p.exterior.coords),closed=True,**kw))
S=[shadow(p.simplify(0.3),h,alt,az) for p,h,_ in B]
for s in S:
    if s.intersects(bx): draw(s,facecolor='#b9c0c9',edgecolor='none',alpha=.55,zorder=2)
draw(bs,facecolor='#5f3dc4',edgecolor='none',alpha=.45,zorder=3)
draw(ud,facecolor='#5f3dc4',edgecolor='#3b0a75',lw=1.2,alpha=.85,zorder=4)
for k,(ls,pr) in enumerate(L):
    if not ls.intersects(bx): continue
    d=r1[k]-r0[k]
    x,y=ls.xy
    if d>0.5:   ax.plot(x,y,color='#e8590c',lw=5.0,solid_capstyle='round',zorder=7)
    elif d>0.1: ax.plot(x,y,color='#f59f00',lw=4.0,solid_capstyle='round',zorder=6)
    else:       ax.plot(x,y,color='#868e96',lw=1.8,solid_capstyle='round',zorder=5)
for lab,lo,la in [('O1',139.71649,35.73191),('O2',139.71660,35.73154),('O3',139.71702,35.73102),('O4',139.71723,35.72937)]:
    x,y=FWD.transform(lo,la)
    ax.plot(x,y,marker='o',ms=18,color='#1864ab',mec='white',mew=2,zorder=9)
    ax.text(x,y,lab,ha='center',va='center',color='white',fontsize=9,fontweight='bold',zorder=10)
ax.set_xlim(CX-R,CX+R); ax.set_ylim(CY-R,CY+R); ax.set_aspect(1); ax.axis('off')
ax.set_title('こかげ｜高架（首都高5号池袋線）の影を入れると歩道の日陰率がどう変わるか　2026-08-12 14:00',fontsize=13.5,pad=10)
h=[MP(np.zeros((3,2)),facecolor='#b9c0c9',alpha=.55,label='建物の影'),
   MP(np.zeros((3,2)),facecolor='#5f3dc4',alpha=.45,label='高架デッキの影（新規）'),
   MP(np.zeros((3,2)),facecolor='#5f3dc4',ec='#3b0a75',alpha=.85,label='高架の真下（常時日陰・屋根あり）'),
   Line2D([],[],color='#e8590c',lw=5,label='日陰率が50pt以上増えた歩道（55本）'),
   Line2D([],[],color='#f59f00',lw=4,label='同 10pt以上（82本）'),
   Line2D([],[],color='#868e96',lw=1.8,label='変化なし')]
ax.legend(handles=h,loc='upper left',fontsize=10,framealpha=.95)
ax.plot([CX-R+25,CX-R+125],[CY-R+22,CY-R+22],color='#212529',lw=3); ax.text(CX-R+75,CY-R+30,'100 m',ha='center',fontsize=9)
fig.text(.5,.028,'O1〜O3周辺（半径200m・264本）の日陰率 46.7% → 51.8%（+5.1pt）。ネットワーク全体では 46.4% → 48.7%（+2.3pt）。'
                 '\n高さは建物 lod1Solid の最小zから求めた地盤高（中央値30.1m）で場所ごとに補正。デッキ影は側面掃引なしの平行移動のみ。',
         ha='center',fontsize=11.5,fontweight='bold',color='#3b0a75',
         bbox=dict(boxstyle='round,pad=0.45',fc='#f3f0ff',ec='#b197fc'))
fig.text(.5,.005,'データ：東京都3Dデジタルマップ（PLATEAU仕様）豊島区2025 udx/brid・udx/bldg（東京都・CC BY 4.0）／'
                 '歩行空間ネットワークデータ 池袋駅周辺（国土交通省）',ha='center',fontsize=8,color='#555')
plt.tight_layout(rect=[0,.062,1,1]); plt.savefig('bridge_shadow.png',dpi=140,facecolor='white'); print('ok')
