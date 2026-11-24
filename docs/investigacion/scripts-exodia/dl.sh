#!/bin/bash
# usage: dl.sh name url
S=/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad
d=$S/downloads/$1; mkdir -p "$d"
curl -sL -m 60 -A "Mozilla/5.0 (X11; Linux x86_64) research-bot" -o "$d/file" "$2"
t=$(file -b "$d/file" | cut -c1-40)
if [[ "$t" == PDF* ]]; then pdftotext -layout "$d/file" "$d/text.txt" 2>/dev/null; else python3 -I -c "
import sys,re,html
s=open(sys.argv[1],'rb').read().decode('utf8','ignore')
s=re.sub(r'(?is)<(script|style).*?</\1>',' ',s); s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s); s=re.sub(r'\s+',' ',s)
open(sys.argv[2],'w').write(s)" "$d/file" "$d/text.txt"; fi
echo "$1: $t $(wc -c < $d/text.txt) chars"
