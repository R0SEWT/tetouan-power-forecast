import sys
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import pandas as pd
from load849 import load
df = load(sys.argv[1]).set_index("dt")
w = df[["Z1","Z2","Z3","T"]].resample("W").mean().round(0)
w["sum"] = w[["Z1","Z2","Z3"]].sum(axis=1)
print(w["2017-09-01":"2017-12-31"].to_string())
d = df[["Z1","Z2","Z3"]].resample("D").mean().round(0)
print(d["2017-11-03":"2017-11-24"].to_string())
