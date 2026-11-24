import sys,json,urllib.request,re
out=sys.argv[1]
for doi in sys.argv[2:]:
    url="https://api.openalex.org/works/https://doi.org/"+doi
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research-bot'})
        w=json.load(urllib.request.urlopen(req,timeout=30))
    except Exception as e:
        print(doi,'ERR',e);continue
    inv=w.get('abstract_inverted_index') or {}
    pos=[]
    for k,v in inv.items():
        for p in v: pos.append((p,k))
    ab=' '.join(k for p,k in sorted(pos))
    auth=', '.join(a['author']['display_name'] for a in w.get('authorships',[])[:3])
    src=((w.get('primary_location') or {}).get('source') or {}).get('display_name')
    print('=== ',doi,'|',w.get('publication_year'),'|',src,'|',w['title'])
    print('  authors:',auth,'| OA:',(w.get('open_access') or {}).get('oa_url'))
    print('  TETOUAN in abstract:', bool(re.search('t[eé]tou?an|tetuan',ab,re.I)))
    print('  ',ab[:1500])
