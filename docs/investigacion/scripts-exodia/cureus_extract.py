import re,html,json,sys
src,out=sys.argv[1],sys.argv[2]
s=open(src,encoding='utf-8',errors='ignore').read()
props=re.findall(r'data-react-props="([^"]*)"',s)
texts=[]
def walk(o):
    if isinstance(o,dict):
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
    elif isinstance(o,str) and len(o)>200:
        texts.append(o)
for p in props:
    try: walk(json.loads(html.unescape(p)))
    except Exception as e: print('err',e)
seen=set();res=[]
for t in texts:
    if t in seen: continue
    seen.add(t)
    t2=html.unescape(re.sub(r'<[^>]+>',' ',t))
    res.append(re.sub(r'[ \t]+',' ',t2))
open(out,'w').write('\n\n=====\n\n'.join(res))
print(len(res),sum(len(r) for r in res))
