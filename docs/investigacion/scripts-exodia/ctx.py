import json,sys,time,urllib.request,urllib.parse
ids=sys.argv[1:]
for pid in ids:
    off=0
    found=False
    while True:
        url=f"https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(pid,safe=':/')}/citations?fields=title,contexts&limit=1000&offset={off}"
        for attempt in range(4):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research-bot'})
                d=json.load(urllib.request.urlopen(req,timeout=60)); break
            except Exception as e:
                d=None; time.sleep(5)
        if not d or not d.get('data'): break
        for r in d['data']:
            t=r['citingPaper'].get('title') or ''
            if 'Transformers and Recurrent Neural Networks in NARX' in t:
                found=True
                print('==',pid)
                for c in r.get('contexts',[]): print('  CTX:',c)
        if 'next' in d and d['next']: off=d['next']
        else: break
        time.sleep(2)
    if not found: print('-- none for',pid)
    time.sleep(3)
