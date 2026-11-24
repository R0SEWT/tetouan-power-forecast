import json,sys
nb=json.load(open(sys.argv[1]))
for i,c in enumerate(nb['cells']):
    if c['cell_type']=='code':
        print(f"#### CELL {i}"); print(''.join(c['source']))
