import json,sys,glob
def ab(inv):
    if not inv: return ''
    pos={}
    for w,ps in inv.items():
        for p in ps: pos[p]=w
    return ' '.join(pos[i] for i in sorted(pos))
ids=set(sys.argv[2].split(','))
seen={}
for f in glob.glob(sys.argv[1]+'/*.json'):
    try: d=json.load(open(f))
    except: continue
    for w in d.get('results',[]):
        k=w['id'][21:]
        if k in ids and k not in seen and w.get('abstract_inverted_index') is not None:
            seen[k]=w
for k in ids:
    w=seen.get(k)
    if not w: print('=== ',k,'NO ABSTRACT'); continue
    print('===',k,w['publication_year'],w.get('doi'),'|',w['title']); print(ab(w['abstract_inverted_index'])[:1500]); print()
