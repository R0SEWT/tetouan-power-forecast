import sys, json, urllib.request
for doi in sys.argv[1:]:
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    try:
        w = json.load(urllib.request.urlopen(url, timeout=60))
    except Exception as e:
        print("ERR", doi, e); continue
    inv = w.get("abstract_inverted_index") or {}
    pos = sorted((p, t) for t, ps in inv.items() for p in ps)
    ab = " ".join(t for _, t in pos)
    au = ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:4])
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    print(f"\n## {doi}\n{w['display_name']} ({w['publication_year']}) — {au} — {src}\n{ab[:1800]}")
