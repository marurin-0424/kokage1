# -*- coding: utf-8 -*-
"""現地確認シート：公園の日陰率の予測を、時刻ごとの地図つきで出す。"""
import sys, json, math; sys.path.insert(0,'.')
from datetime import datetime
import pandas as pd
from shapely.geometry import Point, box
from shapely.ops import unary_union
from shadow import load_buildings, shadow, sun, TZ, FWD

W,H = 620, 620
PARKS = [('山吹の里公園','豊島区高田1-10-5', 139.71806, 35.71413, 603.0),
         ('高田一丁目児童遊園','豊島区高田1-23-33', 139.71724, 35.71547, None)]
HOURS = [9, 10]
SPAN = 190.0
B = load_buildings('takada_bldg_lod0.json')
FOOT = unary_union([p.simplify(0.5) for p,h,_ in B])

def svg(cx, cy, U, R, az, alt):
    k = W/SPAN; parts=[]
    bx = box(cx-SPAN/2, cy-SPAN/2, cx+SPAN/2, cy+SPAN/2)
    def px(x,y): return ((x-cx)*k+W/2, H/2-(y-cy)*k)
    def poly(g, **a):
        gs = list(g.geoms) if hasattr(g,'geoms') else [g]
        d=[]
        for p in gs:
            if p.is_empty or p.geom_type!='Polygon': continue
            for ring in [p.exterior]+list(p.interiors):
                c=list(ring.coords)
                if len(c)<3: continue
                pts=[px(x,y) for x,y in c]
                d.append('M'+' L'.join(f'{a_:.0f},{b_:.0f}' for a_,b_ in pts)+'Z')
        if d:
            at=' '.join(f'{k2.replace("_","-")}="{v}"' for k2,v in a.items())
            parts.append(f'<path d="{"".join(d)}" {at} fill-rule="evenodd"/>')
    poly(U.intersection(bx).simplify(0.6), fill='#98a0a8', opacity='0.62', stroke='none')
    for p,h,_ in B:
        if h>=3 and p.area>=25 and p.intersects(bx):
            poly(p.intersection(bx).simplify(0.6), fill='#f6f5f2', stroke='#dcdbd4', stroke_width='0.6')
    X,Y = px(cx,cy)
    parts.append(f'<circle cx="{X}" cy="{Y}" r="{R*k:.1f}" fill="#1baf7a" opacity="0.16" stroke="#1baf7a" stroke-width="2.5" stroke-dasharray="6 4"/>')
    parts.append(f'<circle cx="{X}" cy="{Y}" r="5" fill="#1baf7a" stroke="#fff" stroke-width="2"/>')
    # 太陽の方向（方位角）
    ar=math.radians(az); L=W*0.30
    sx,sy = X+L*math.sin(ar), Y-L*math.cos(ar)
    parts.append(f'<line x1="{X}" y1="{Y}" x2="{sx:.0f}" y2="{sy:.0f}" stroke="#eb6834" stroke-width="2.5" stroke-dasharray="8 5"/>'
                 f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="11" fill="#eb6834"/>'
                 f'<text x="{sx:.0f}" y="{sy+4:.0f}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">日</text>')
    parts.append(f'<path d="M{W-28},{18} L{W-34},{38} L{W-28},{33} L{W-22},{38} Z" fill="#0b0b0b"/>'
                 f'<text x="{W-28}" y="{52}" text-anchor="middle" font-size="11" fill="#898781">N</text>')
    m=50; parts.append(f'<line x1="16" y1="{H-18}" x2="{16+m*k:.0f}" y2="{H-18}" stroke="#0b0b0b" stroke-width="2.5"/>'
                       f'<text x="{16+m*k/2:.0f}" y="{H-24}" text-anchor="middle" font-size="11">{m} m</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block;background:#fcfcfb">'+''.join(parts)+'</svg>'

cards=[]
for nm, addr, lon, lat, area in PARKS:
    X,Y = FWD.transform(lon, lat)
    R = math.sqrt(area/math.pi) if area else 15.0
    for hh in HOURS:
        dt = pd.DatetimeIndex([datetime(2026,8,13,hh,0,tzinfo=TZ)])
        alt, az = sun(dt)
        U = unary_union([shadow(p.simplify(0.5), h, alt, az) for p,h,_ in B])
        c = Point(X,Y).buffer(R); ground = c.difference(FOOT)
        bcov = 1.0 - ground.area/c.area
        sh_old = U.intersection(c).area / c.area
        sh = U.difference(FOOT).intersection(c).area / max(ground.area,1e-9)
        cards.append(dict(name=nm, addr=addr, hour=hh, alt=round(alt,1), az=round(az,1),
                          R=round(R,1), shade=round(sh,3), shade_old=round(sh_old,3),
                          bcov=round(bcov,3), assumed=(area is None),
                          svg=svg(X,Y,U,R,az,alt)))
        print(nm, hh, f'{sh:.1%}', flush=True)
json.dump(cards, open('park_cards.json','w'), ensure_ascii=False)
