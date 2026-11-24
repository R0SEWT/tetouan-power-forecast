import sys
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import pandas as pd
from load849 import load
df = load(sys.argv[1]).set_index("dt")
d = df[["Z1","Z2","Z3"]].resample("D").mean().round(0)
d["Z1+Z2"] = d.Z1 + d.Z2
d["dow"] = d.index.day_name().str[:3]
print(d["2017-10-20":"2017-11-04"].to_string())
