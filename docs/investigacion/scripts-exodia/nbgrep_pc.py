import json,sys,re
nb=json.load(open(sys.argv[1]))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    s=''.join(c['source'])
    for ln in s.splitlines():
        if re.search(r'lookahead\s*=|lookback\s*=|epochs\s*=|batch_size\s*=|def build_|shuffle|fit\(', ln):
            print(i, ln.strip()[:200])
    if 'def build_PConvLSTM' in s or 'def build_P_ConvLSTM' in s or 'ConvLSTM2D' in s and 'Concatenate' in s:
        pass
    outs=c.get('outputs',[])
    for o in outs:
        t=''.join(o.get('text',[])) if 'text' in o else ''
        if 'shape' in s and '4-Fold' in s: print('OUT',i,t[:400])
