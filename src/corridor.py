import paths
import sys,csv,io,json,math; from shadow import FWD, load_links
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from sidewalk import find_pairs, bearing

def trees():
    raw=open(paths.raw('tokyo_gairoju.csv'),'rb').read().decode('cp932')
    r=csv.reader(io.StringIO(raw)); hdr=next(r); I={h:i for i,h in enumerate(hdr)}
    out=[]
    for x in r:
        if '豊島' not in x[I['行政区']]: continue
        out.append(dict(rosen=x[I['路線名']],tsusho=x[I['通称道路名']],
                        lon=float(x[I['経度']]),lat=float(x[I['緯度']]),
                        th=x[I['樹高(m)']],tw=x[I['枝張(m)']],kubun=x[I['区分']]))
    return out

T=trees(); L=load_links(paths.raw('ikebukuro_link.geojson'))
pairs=find_pairs(L); paired=set()
for i,j,sep,b,linked in pairs:
    if linked: paired.add(i); paired.add(j)
loose=set()
for i,j,sep,b,linked in pairs: loose.add(i); loose.add(j)

CORR={'明治通り':[t for t in T if t['tsusho']=='明治通り'],
      'グリーン大通り(音羽池袋線)':[t for t in T if t['rosen']=='音羽池袋線'],
      '西池袋通り':[t for t in T if t['tsusho']=='西池袋通り'],
      '山手通り':[t for t in T if t['tsusho']=='山手通り']}

for name,ts in CORR.items():
    pts=[Point(*FWD.transform(t['lon'],t['lat'])) for t in ts]
    if not pts: continue
    corr=unary_union([p.buffer(38) for p in pts])
    rows=[]
    for k,(ls,pr) in enumerate(L):
        if str(pr.get('rt_struct'))!='1': continue
        if ls.intersection(corr).length < ls.length*0.6: continue
        st='ペア確定' if k in paired else ('ゆるい判定のみ' if k in loose else '★対なし')
        c=ls.interpolate(0.5,normalized=True)
        rows.append((k,ls.length,st,bearing(ls),c))
    tot=sum(r[1] for r in rows)
    ok=sum(r[1] for r in rows if r[2]=='ペア確定')
    ng=[r for r in rows if r[2]=='★対なし']
    print(f'\n=== {name} ===  歩道リンク {len(rows)}本 / 延長 {tot:.0f}m')
    print(f'  ペア確定 {ok:.0f}m ({ok/tot:.0%}) / ゆるい判定のみ {sum(r[1] for r in rows if r[2]=="ゆるい判定のみ"):.0f}m / ★対なし {sum(r[1] for r in ng):.0f}m ({sum(r[1] for r in ng)/tot:.0%})')
    json.dump([[r[0],round(r[1],1),r[2],round(r[3],1)] for r in rows], open(paths.out(f'corr_{abs(hash(name))%10000}.json'),'w'))
    globals().setdefault('RES',{})[name]=rows
json.dump({k:[[r[0],round(r[1],1),r[2],round(r[3],1)] for r in v] for k,v in RES.items()}, open(paths.out('corridors.json'),'w'), ensure_ascii=False)
