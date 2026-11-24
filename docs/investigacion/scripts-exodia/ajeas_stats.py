import sys, csv, statistics as st
p=sys.argv[1]
rows=list(csv.reader(open(p,encoding='utf-8-sig')))
h=rows[0]; d=rows[1:]
print(h); print("n rows",len(d), d[0][0], d[-1][0])
for j,name in enumerate(h[1:],1):
    v=[float(r[j]) for r in d]
    print(f"{name}: min={min(v):.2f} max={max(v):.2f} mean={st.mean(v):.2f} sd={st.pstdev(v):.2f}")
