import csv,sys,glob
f=glob.glob(sys.argv[1]+'/**/*.csv',recursive=True)[0]
r=list(csv.reader(open(f)))
h=r[0];print(h)
z=[[float(x[i]) for x in r[1:]] for i in (6,7,8)]
tot=[a+b+c for a,b,c in zip(*z)]
for name,v in zip(['z1','z2','z3','total'],z+[tot]):
    m=sum(v)/len(v);print(name,'mean %.0f min %.0f max %.0f range %.0f'%(m,min(v),max(v),max(v)-min(v)), 'RMSE925/mean %.4f /max %.4f /range %.4f'%(925.11/m,925.11/max(v),925.11/(max(v)-min(v))), 'MAE/mean %.4f'%(732.63/m))
