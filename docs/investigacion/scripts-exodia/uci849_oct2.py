import sys
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import pandas as pd
from load849 import load
df = load(sys.argv[1]).set_index("dt")
h = df[["Z1","Z2"]].resample("1h").mean()
dd = (h - h.shift(24*7)).round(0)
print(dd["2017-10-24 06:00":"2017-10-26 06:00"].to_string())
