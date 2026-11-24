import sys,re,html,json
s=open(sys.argv[1],encoding='utf-8').read()
m=re.findall(r'data-react-props="([^"]*)"',s)
best=max(m,key=len) if m else s
t=html.unescape(best)
t=re.sub(r'<[^>]+>',' ',t)
t=t.replace('\\n','\n').replace('\\u003c','<').replace('\\u003e','>').replace('\\"','"')
t=re.sub(r'<[^>]+>',' ',t)
t=re.sub(r'[ \t]+',' ',t)
open(sys.argv[2],'w').write(t)
print(len(t))
