import sys, pyarrow as pa, numpy as np
for p in sys.argv[1:]:
    with open(p, 'rb') as f:
        t = pa.ipc.open_stream(f).read_all()
    print('==', p.split('/')[-1], t.num_rows, t.schema.names)
    for r in t.slice(0, 3).to_pylist():
        tgt = np.asarray(r['target'], dtype=float)
        if tgt.ndim > 1: tgt = tgt[0]
        print('  ', r.get('item_id'), r.get('start'), r.get('freq'), 'len', tgt.size, 'mean', np.nanmean(tgt).round(1), 'min', np.nanmin(tgt).round(1), 'max', np.nanmax(tgt).round(1), 'first', tgt[:4].round(1))
