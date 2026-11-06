"""Lista una carpeta del file browser del COES. Uso: coes_browse.py '<ruta relativa>' [base]"""
import sys, re, html, urllib.request, urllib.parse
url = sys.argv[1]; base = sys.argv[2] if len(sys.argv) > 2 else url
data = urllib.parse.urlencode({"baseDirectory": base, "url": url, "indicador": "S"}).encode()
req = urllib.request.Request("https://www.coes.org.pe/Portal/browser/vistadatos", data=data,
                             headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0"})
h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
items = re.findall(r"<li class=\"infolist-item[^>]*>(.*?)</li>", h, re.S)
seen = set()
for it in items:
    m = re.search(r"openBlob\('([^']+)',\s*'(\w)',\s*'([^']*)'\)", it)
    txt = html.unescape(re.sub(r"<[^>]+>|\s+", " ", it)).strip()
    if m and m.group(1) not in seen:
        seen.add(m.group(1))
        print(m.group(2), html.unescape(m.group(1)), "|", txt[:160])
