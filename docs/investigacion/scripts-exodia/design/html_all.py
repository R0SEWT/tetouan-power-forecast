import json, sys, io
import pandas as pd
nb = json.load(open(sys.argv[1]))
cells = [int(x) for x in sys.argv[2].split(',')]
pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 300); pd.set_option('display.max_colwidth', 60)
for i in cells:
    c = nb['cells'][i]
    for o in c.get('outputs', []):
        d = o.get('data', {})
        if 'text/html' in d:
            html = ''.join(d['text/html'])
            try:
                for t in pd.read_html(io.StringIO(html)):
                    print(f"=== cell {i} ==="); print(t.to_string())
            except Exception as e:
                print(f"cell {i} parse error {e}")
