"""Busca en datosabiertos.gob.pe (HTML). Uso: da_search.py 'query' [paginas]"""
import sys, re, html, urllib.request, urllib.parse
q = sys.argv[1]; pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
for p in range(pages):
    url = "https://www.datosabiertos.gob.pe/search/type/dataset?" + urllib.parse.urlencode({"query": q, "page": p})
    h = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
    if p == 0:
        m = re.search(r"([\d.,]+)\s+(?:resultados|Resultados|conjuntos de datos|results)", h)
        print(f"## '{q}' total:", m.group(1) if m else "?")
    for a, t in re.findall(r'<h2[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        print("  ", html.unescape(re.sub(r"<[^>]+>|\s+", " ", t)).strip(), "|", urllib.parse.unquote(a))
