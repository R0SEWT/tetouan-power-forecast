import json, sys
nb = json.load(open(sys.argv[1]))
for i, c in enumerate(nb['cells']):
    src = ''.join(c['source'])
    outs = ''
    for o in c.get('outputs', []):
        if 'text' in o: outs += ''.join(o['text'])
        elif 'data' in o: outs += ''.join(o['data'].get('text/plain', ''))
    if 'toto' in (src + outs).lower():
        print('CELL', i, c['cell_type']); print(src[:500]); print('OUT:', outs[:2500]); print('------')
