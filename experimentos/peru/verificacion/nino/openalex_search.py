import sys, json, urllib.request, urllib.parse, os
out = sys.argv[1]
queries = sys.argv[2:]
for q in queries:
    params = {"search": q, "per_page": "12", "mailto": "",
              "select": "id,doi,display_name,publication_year,cited_by_count,primary_location,open_access,type"}
    params.pop("mailto")
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        d = json.load(urllib.request.urlopen(url, timeout=60))
    except Exception as e:
        print("ERR", q, e); continue
    fn = os.path.join(out, q.replace(" ", "_")[:60] + ".json")
    json.dump(d, open(fn, "w"))
    print(f"\n### {q}  (total {d['meta']['count']})")
    for w in d["results"]:
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
        oa = (w.get("open_access") or {}).get("oa_url")
        print(f"- {w['publication_year']} | {w['display_name'][:120]} | {src} | cit={w['cited_by_count']} | {w.get('doi')} | oa={oa}")
