import json,sys,time,urllib.request,urllib.parse
for t in sys.argv[1:]:
    url="https://api.semanticscholar.org/graph/v1/paper/search/match?query="+urllib.parse.quote(t)+"&fields=title,citationCount"
    for a in range(4):
        try:
            d=json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research-bot'}),timeout=60));break
        except Exception as e: d=None; time.sleep(5)
    if d and d.get('data'): x=d['data'][0]; print(x['paperId'],x.get('citationCount'),x['title'])
    else: print('NOTFOUND',t)
    time.sleep(2)
