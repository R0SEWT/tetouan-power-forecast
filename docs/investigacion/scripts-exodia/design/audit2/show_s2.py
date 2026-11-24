import json,sys
for fn in sys.argv[1:]:
    d=json.load(open(fn))
    print('#####',fn)
    for k,v in d.items():
        print('==',k)
        if 'error' in v: print('  ERR',v['error'],v.get('body','')[:150]); continue
        if 'data' in v:
            for x in v['data'][:10]:
                if 'snippet' in x:
                    p=x.get('paper',{}); print('  [snip]',p.get('title','')[:80],'|',p.get('corpusId'),'|',x['snippet'].get('text','')[:400].replace('\n',' '))
                elif 'papers' in x:
                    print('  [author]',x.get('name'),x.get('paperCount'))
                    for pp in x['papers'][:40]: print('     ',pp.get('year'),pp.get('title','')[:90],(pp.get('externalIds') or {}).get('DOI'),(pp.get('openAccessPdf') or {}).get('url'))
                else:
                    print('  ',x.get('year'),x.get('title','')[:90],(x.get('externalIds') or {}).get('DOI'),(x.get('openAccessPdf') or {}).get('url'))
        else:
            print('  ',v.get('year'),v.get('venue'),'|',v.get('title'),'| corpus',(v.get('externalIds') or {}).get('CorpusId'),'| OA',v.get('openAccessPdf'))
            if v.get('abstract'): print('   ABS:',v['abstract'][:700])
            if v.get('tldr'): print('   TLDR:',(v['tldr'] or {}).get('text'))
