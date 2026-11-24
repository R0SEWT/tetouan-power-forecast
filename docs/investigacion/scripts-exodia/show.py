import json,sys
ids=set(sys.argv[1].split(','))
for f in sys.argv[2:]:
  d=json.load(open(f))
  for w in d['results']:
    if w['id'][21:] in ids:
      ii=w.get('abstract_inverted_index') or {}
      pos=sorted((p,k) for k,v in ii.items() for p in v)
      print('==',w['id'][21:],w['publication_year'],w['doi'],w['title']); print(' '.join(k for p,k in pos)[:1800]); print()
