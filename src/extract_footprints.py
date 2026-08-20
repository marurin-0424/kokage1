import paths
import re, sys, json, os, zipfile
ZP=paths.raw('13116_toshima-ku_pref_2025_citygml_1_op.zip')
# 歩行空間NWの範囲 + 余裕300m(≈0.0033deg lat / 0.0033deg lon)
LON0,LON1 = 139.69534-0.004, 139.72292+0.004
LAT0,LAT1 = 35.72414-0.003, 35.73373+0.003

re_bldg = re.compile(r'<bldg:Building\b.*?</bldg:Building>', re.S)
re_id   = re.compile(r'gml:id="([^"]+)"')
re_h    = re.compile(r'<bldg:measuredHeight[^>]*>([\d.]+)</bldg:measuredHeight>')
re_roof = re.compile(r'<bldg:lod0RoofEdge>(.*?)</bldg:lod0RoofEdge>', re.S)
re_pos  = re.compile(r'<gml:posList>(.*?)</gml:posList>', re.S)
re_lod2 = re.compile(r'<bldg:lod2Solid>')
re_usage= re.compile(r'<bldg:usage[^>]*>([^<]*)</bldg:usage>')
re_st  = re.compile(r'<bldg:storeysAboveGround>(\d+)</bldg:storeysAboveGround>')
re_bid = re.compile(r'<uro:buildingID>([^<]*)</uro:buildingID>')

def run(mesh):
    z=zipfile.ZipFile(ZP)
    data=z.read('udx/bldg/%s_bldg_6697_op.gml'%mesh).decode('utf-8')
    out=[]; n=0; nlod2=0
    for m in re_bldg.finditer(data):
        blk=m.group(0); n+=1
        mh=re_h.search(blk)
        rf=re_roof.search(blk)
        if not mh or not rf: continue
        h=float(mh.group(1))
        # 外周リング＝lod0RoofEdge内の最初のposList（最大面積のものを選ぶ）
        rings=[]
        for p in re_pos.finditer(rf.group(1)):
            v=p.group(1).split()
            c=[(float(v[i+1]),float(v[i])) for i in range(0,len(v),3)]  # (lon,lat)
            rings.append(c)
        if not rings: continue
        def area(c):
            s=0.0
            for i in range(len(c)-1):
                s+=c[i][0]*c[i+1][1]-c[i+1][0]*c[i][1]
            return abs(s)/2
        ring=max(rings,key=area)
        lons=[p[0] for p in ring]; lats=[p[1] for p in ring]
        cx=sum(lons)/len(lons); cy=sum(lats)/len(lats)
        if not (LON0<=cx<=LON1 and LAT0<=cy<=LAT1): continue
        has2 = 1 if re_lod2.search(blk) else 0
        nlod2 += has2
        st=re_st.search(blk); bid=re_bid.search(blk); us=re_usage.search(blk)
        out.append({'id':re_id.search(blk).group(1),'h':h,'lod2':has2,
                    'st':int(st.group(1)) if st else None,
                    'bid':bid.group(1) if bid else None,
                    'us':us.group(1) if us else None,
                    'r':[[round(x,7),round(y,7)] for x,y in ring]})
    return out,n,nlod2

if __name__=='__main__':
    mesh=sys.argv[1]
    out,n,nl2=run(mesh)
    json.dump(out,open(paths.cache('b_%s.json'%mesh),'w'))
    print(mesh,'buildings_in_mesh',n,'kept',len(out),'lod2_in_kept',nl2,
          'maxH',max([b['h'] for b in out],default=0))
