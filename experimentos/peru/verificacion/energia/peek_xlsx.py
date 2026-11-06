import sys, openpyxl
p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
for ws in wb.worksheets:
    print("== sheet", ws.title, ws.max_row, ws.max_column)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= n: break
        print(row)
