import paths
import sys, json; import destination as D
ORIG = {'ikebukuro_east':(139.71150,35.72950), 'toden_zoshigaya':(139.717760,35.724081)}
FS = [1.0, 0.6, 0.3, 0.0]
out={}
for ok,o in ORIG.items():
    for f in FS:
        r = D.recommend(hour=14, wbgt=29.0, stay_min=60.0, stroller=False, bw=15.0,
                        purpose='outdoor_play', origin=o, top=300, sun_frac=f)
        parks=[x for x in r['all'] if x['kind']=='park']
        parks.sort(key=lambda x:x['total'])
        out[f'{ok}_{f}']=dict(main=r['main']['name'], total=round(r['main']['total']),
                              order=[x['name'] for x in parks],
                              totals={x['name']:round(x['total'],1) for x in parks})
        print(ok,f,'->',r['main']['name'],round(r['main']['total']),'mL  n=',len(parks),flush=True)
json.dump(out, open(paths.out('cloudiness_eval.json'),'w'), ensure_ascii=False)
# 順位の入替を数える
for ok in ORIG:
    base=out[f'{ok}_1.0']['order']
    print(f'\n== {ok} ==  1位(f=1.0): {out[f"{ok}_1.0"]["main"]}')
    for f in FS[1:]:
        cur=out[f'{ok}_{f}']['order']
        moved=sum(1 for i,n in enumerate(base) if cur.index(n)!=i)
        print(f'  f={f}: 1位={out[f"{ok}_{f}"]["main"]}  順位が動いた公園 {moved}/{len(base)}件')
print('DONE')
