import json,sys
j=json.load(open(sys.argv[1],encoding='utf-8',errors='replace'))
for i,c in enumerate(j['cells']):
    s=''.join(c['source']) if isinstance(c['source'],list) else c['source']
    print(f"--- [{i}] {c['cell_type']}"); print(s[:int(sys.argv[2]) if len(sys.argv)>2 else 1500])
    for o in c.get('outputs',[]) or []:
        t=o.get('text') or (o.get('data',{}) or {}).get('text/plain')
        if t:
            t=''.join(t) if isinstance(t,list) else t
            print(">>OUT:", t[:600])
