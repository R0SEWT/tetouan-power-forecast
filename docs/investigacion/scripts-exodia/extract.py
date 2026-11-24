import json,sys,re
p=sys.argv[1]; raw=open(p,encoding='utf-8',errors='replace').read()
try:
    j=json.loads(raw); cells=j.get('cells',[])
    code="\n".join(''.join(c['source']) if isinstance(c['source'],list) else c['source'] for c in cells if c.get('cell_type')=='code')
    md="\n".join(''.join(c['source']) if isinstance(c['source'],list) else c['source'] for c in cells if c.get('cell_type')=='markdown')
    outs=[]
    for c in cells:
        for o in c.get('outputs',[]) or []:
            t=o.get('text') or (o.get('data',{}) or {}).get('text/plain')
            if t: outs.append(''.join(t) if isinstance(t,list) else t)
    outtxt="\n".join(outs)
except Exception:
    code=raw; md=''; outtxt=''
pat=re.compile(r'train_test_split|shuffle|TimeSeriesSplit|KFold|cross_val|\.shift\(|lag|rolling|r2_score|mean_absolute|mean_squared|split|iloc\[:|<\s*[\'"]20|>=?\s*[\'"]20|lookback|window|horizon|n_steps|look_back|drop\(|X\s*=|y\s*=|features|FEATURES|TARGET|target|initial_split|lm\(|lag\(',re.I)
print("### CODE hits")
for i,l in enumerate(code.splitlines()):
    if pat.search(l) and len(l)<250: print(i,l)
print("### OUTPUT metric-ish lines")
for l in outtxt.splitlines():
    if re.search(r'r2|r\^2|R2|R-squared|MAE|RMSE|MAPE|score',l) and len(l)<200: print(l)
