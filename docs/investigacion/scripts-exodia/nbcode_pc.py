import json,sys
nb=json.load(open(sys.argv[1]))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    s=''.join(c['source'])
    if any(k in s for k in ['Tetuan','reframe','fold_size','lookahead','resample','persistence','Persistence','yhat = test_x_load']):
        print('=== cell',i); print(s[:4000])
