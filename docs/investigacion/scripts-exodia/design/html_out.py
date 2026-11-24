import json, sys, io
import pandas as pd
nb = json.load(open(sys.argv[1]))
cells = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv)>2 else range(len(nb['cells']))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
for i in cells:
    c = nb['cells'][i]
    if c['cell_type']!='code': continue
    for o in c.get('outputs', []):
        d = o.get('data', {})
        if 'text/html' in d and 'Styler' in ''.join(d.get('text/plain','')) or ('text/html' in d and '...' in ''.join(d.get('text/plain',''))):
            html = ''.join(d['text/html'])
            try:
                for t in pd.read_html(io.StringIO(html)):
                    print(f"=== cell {i} ==="); print(t.to_string())
            except Exception as e:
                print(f"cell {i} parse error {e}")
