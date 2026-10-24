"""Metadatos de un dataset de datosabiertos.gob.pe (HTML DKAN). Uso: da_dataset.py <slug>"""
import sys, re, html, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
slug = sys.argv[1]
url = "https://www.datosabiertos.gob.pe/dataset/" + urllib.parse.quote(slug)
h = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
txt = lambda s: html.unescape(re.sub(r"<[^>]+>|\s+", " ", s)).strip()
t = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S); print("TÍTULO:", txt(t.group(1)) if t else "?")
d = re.search(r'<div class="field field-name-body.*?>(.*?)</div>\s*</div>', h, re.S); print("DESC:", txt(d.group(1))[:500] if d else "?")
# tabla de info adicional
for k, v in re.findall(r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", h, re.S):
    k, v = txt(k), txt(v)
    if k and v: print(f"  {k}: {v[:160]}")
lic = re.search(r'(?i)licen[cs]e?[^<]{0,40}</[^>]+>\s*(?:<[^>]+>\s*)*([^<]{3,120})', h)
print("LICENCIA(heur):", lic.group(1).strip() if lic else "?")
res = re.findall(r'href="(https?://[^"]+\.(?:csv|xlsx?|zip|json|txt|rar)[^"]*)"', h, re.I)
print("RECURSOS:", len(set(res)))
for r in sorted(set(res))[:15]: print("   ", urllib.parse.unquote(r))
for a, tt in re.findall(r'<a[^>]+href="(/dataset/[^"]+/resource/[^"]+)"[^>]*>(.*?)</a>', h, re.S)[:15]:
    print("   res:", txt(tt)[:90], "|", urllib.parse.unquote(a))
