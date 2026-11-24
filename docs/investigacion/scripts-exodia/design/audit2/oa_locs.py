import json,sys,time,urllib.request,urllib.parse
out=sys.argv[1]
dois=sys.argv[2:]
res={}
for d in dois:
    u='https://api.openalex.org/works/doi:'+d
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'lit-audit/1.0'}),timeout=60) as f: w=json.loads(f.read())
    except Exception as e:
        print(d,'ERR',e); continue
    res[d]=w
    print('==',d,'|',w.get('title','')[:90],'|',w.get('publication_year'),'| oa:',w.get('open_access',{}).get('oa_status'),w.get('open_access',{}).get('oa_url'))
    for l in w.get('locations',[]):
        print('    loc:',(l.get('source') or {}).get('display_name'),'|',l.get('landing_page_url'),'|',l.get('pdf_url'),'|',l.get('version'))
    print('    authors:', '; '.join(a['author']['display_name']+' ['+','.join(i['display_name'] for i in a.get('institutions',[]))+']' for a in w.get('authorships',[]))[:400])
    print('    cited_by:',w.get('cited_by_count'))
    time.sleep(0.3)
json.dump(res,open(out,'w'))
