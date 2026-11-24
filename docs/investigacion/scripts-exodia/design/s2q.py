import json, os, sys, time, urllib.request, urllib.parse
KEY = open(os.path.expanduser('~/.config/semanticscholar/api_key')).read().strip()
OUT = sys.argv[1]
reqs = json.load(open(sys.argv[2]))  # list of [name, path_with_query]
res = {}
for name, path in reqs:
    url = 'https://api.semanticscholar.org' + path
    r = urllib.request.Request(url, headers={'x-api-key': KEY, 'User-Agent': 'lit-audit/1.0'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as f:
                res[name] = json.loads(f.read())
            break
        except Exception as e:
            body = ''
            try: body = e.read().decode()[:300]
            except Exception: pass
            res[name] = {'error': str(e), 'body': body}
            if '429' not in str(e): break
            time.sleep(3 * (attempt + 1))
    time.sleep(1.5)
json.dump(res, open(OUT, 'w'), indent=1)
print('done', len(res))
