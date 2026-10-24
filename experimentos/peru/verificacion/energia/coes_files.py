"""Lista archivos (tabla) de una carpeta del browser COES. Uso: coes_files.py '<ruta>' '<base>'"""
import sys, re, html, urllib.request, urllib.parse
url, base = sys.argv[1], sys.argv[2]
data = urllib.parse.urlencode({"baseDirectory": base, "url": url, "indicador": "S"}).encode()
req = urllib.request.Request("https://www.coes.org.pe/Portal/browser/vistadatos", data=data,
                             headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0"})
h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
for r in re.findall(r"<tr.*?</tr>", h, re.S)[1:]:
    c = [html.unescape(re.sub(r"<[^>]+>|\s+", " ", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
    c = [x for x in c if x]
    print(" | ".join(c[:4]))
