import json, sys
nb = json.load(open(sys.argv[1]))
maxout = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
for i, c in enumerate(nb["cells"]):
    src = "".join(c["source"])
    print(f"\n===== [{i}] {c['cell_type']} =====")
    print(src)
    for o in c.get("outputs", []):
        t = ""
        if o.get("output_type") == "stream":
            t = "".join(o.get("text", ""))
        elif "data" in o:
            d = o["data"]
            if "text/markdown" in d: t = "".join(d["text/markdown"])
            elif "text/plain" in d: t = "".join(d["text/plain"])
        elif o.get("output_type") == "error":
            t = "ERROR " + o.get("ename","") + ": " + o.get("evalue","")
        if t:
            print("--- out ---")
            print(t[:maxout])
