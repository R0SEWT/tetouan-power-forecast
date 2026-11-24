import json, os, sys, urllib.request
KEY=open(os.path.expanduser('~/.config/semanticscholar/api_key')).read().strip()
ids=sys.argv[2:]
body=json.dumps({'ids':ids}).encode()
r=urllib.request.Request('https://api.semanticscholar.org/graph/v1/paper/batch?fields=paperId,title,year,externalIds,openAccessPdf',data=body,headers={'x-api-key':KEY,'Content-Type':'application/json','User-Agent':'lit-audit/1.0'})
res=json.loads(urllib.request.urlopen(r,timeout=60).read())
json.dump(res,open(sys.argv[1],'w'),indent=1)
for i,x in zip(ids,res):
    print(i,'->',None if x is None else (x['paperId'],(x.get('title') or '')[:60],(x.get('openAccessPdf') or {}).get('url')))
