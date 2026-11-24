import json,sys,re
def ab(inv):
    if not inv: return ''
    pos={}
    for w,ps in inv.items():
        for p in ps: pos[p]=w
    return ' '.join(pos[i] for i in sorted(pos))
for f in sys.argv[1:]:
    d=json.load(open(f))
    for w in d['results']:
        a=ab(w.get('abstract_inverted_index'))
        t=w.get('title') or ''
        hit=re.search(r'tet[ou]+an|t[ée]touan|tetuan|amendis|morocc',(t+' '+a),re.I)
        print('###',('HIT' if hit else '---'),w['publication_year'],w['id'][21:],w.get('doi'),'|',t)
        if hit:
            for m in re.finditer(r'[^.]*(tet[ou]+an|tetuan|amendis|morocc|ahead|horizon|R2|R\^2|R²|step)[^.]*\.',a,re.I):
                print('   >',m.group(0).strip()[:400])
