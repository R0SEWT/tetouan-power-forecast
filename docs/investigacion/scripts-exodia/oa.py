import sys,json,glob
seen={}
for f in sys.argv[1:]:
    d=json.load(open(f))
    print(f, d.get('meta',{}).get('count'))
    for w in d['results']:
        t=w['title'] or ''
        if 'etouan' in t.lower() or 'tetuan' in t.lower() or True:
            seen[w['id']]=(w['publication_year'],w['doi'],t,((w.get('primary_location') or {}).get('source') or {}).get('display_name'),w['type'])
for k,v in sorted(seen.items(),key=lambda x:-x[1][0]):
    print(v)
