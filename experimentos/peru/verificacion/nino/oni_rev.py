import sys
SEAS=["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"]
def rd(p):
    d={}
    for l in open(p):
        x=l.split()
        if len(x)==4 and x[0] in SEAS: d[(int(x[1]),SEAS.index(x[0])+1)]=(float(x[2]),float(x[3]))
    return d
a=rd(sys.argv[1]); b=rd(sys.argv[2])
from collections import defaultdict
st=defaultdict(list)
for k in a:
    if k in b: st[k[0]//10*10].append((b[k][1]-a[k][1], b[k][0]-a[k][0]))
for dec in sorted(st):
    v=st[dec]; an=[x[0] for x in v]; tt=[x[1] for x in v]
    print(dec, "n=%d anom: media=%+.3f max|d|=%.2f | total(SST abs): media=%+.3f" % (len(v), sum(an)/len(an), max(abs(x) for x in an), sum(tt)/len(tt)))
# eventos ENSO clave
for k in [(1997,12),(2015,12),(2017,2),(2023,12),(2025,12),(2026,1)]:
    if k in a and k in b: print(k, "antes", a[k][1], "ahora", b[k][1])
