import json,sys
d=json.load(open(sys.argv[1]))
for k,v in d.items():
    print('=====',k)
    if 'error' in v: print(v); continue
    if 'data' in v:
        for p in v['data']:
            if 'snippet' in p:
                print('  SNIP',p['paper'].get('title'),'|',p['snippet'].get('text','')[:700]); continue
            print('  ',p.get('year'),p.get('title'),p.get('venue'),p.get('externalIds',{}).get('DOI'),p.get('externalIds',{}).get('ArXiv'),(p.get('openAccessPdf') or {}).get('url'))
        continue
    print(v.get('year'),v.get('title'),'|',v.get('venue'),'|',v.get('externalIds'),'|OA:',(v.get('openAccessPdf') or {}).get('url'),(v.get('openAccessPdf') or {}).get('status'))
    print('AUTH:',[a['name'] for a in v.get('authors',[])])
    print('ABS:',(v.get('abstract') or '')[:1800])
    print('TLDR:',(v.get('tldr') or {}).get('text'))
