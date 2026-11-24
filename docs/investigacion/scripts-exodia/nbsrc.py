import json,sys
nb=json.load(open(sys.argv[1]))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    src=''.join(c['source'])
    if any(k in src for k in sys.argv[2].split('|')):
        print(f"===== cell {i}"); print(src[:4000])
        for o in c.get('outputs',[]):
            t=''.join(o.get('text',[])) if 'text' in o else ''.join(o.get('data',{}).get('text/plain',[]))
            if t: print('--- out:', t[:1500])
