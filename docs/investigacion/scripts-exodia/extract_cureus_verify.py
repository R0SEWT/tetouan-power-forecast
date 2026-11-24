import sys, re, html, json
src = open(sys.argv[1], encoding='utf-8', errors='replace').read()
m = re.findall(r'data-react-props="([^"]*)"', src)
out=[]
for s in m:
    t = html.unescape(s)
    out.append(t)
txt = "\n".join(out) if out else src
txt = re.sub(r'<[^>]+>', ' ', txt)
txt = html.unescape(txt)
txt = txt.replace('\\n','\n').replace('\\u003c','<').replace('\\u003e','>').replace('\\"','"')
txt = re.sub(r'<[^>]+>', ' ', txt)
txt = re.sub(r'[ \t]+', ' ', txt)
open(sys.argv[2],'w').write(txt)
print(len(txt))
