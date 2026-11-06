"""Coherencia portal (30 min) vs Estadística Anual COES 2017, Cuadro 2.1. Uso: q_vs_estadistica.py <sein_csv> <cuadro_xlsx>"""
import sys
import pandas as pd
po = pd.read_csv(sys.argv[1], index_col=0, parse_dates=True)["EJECUTADO"]
y = po.loc["2017-01-01 00:30":"2018-01-01 00:00"]
# periodo-final: el valor de 00:00 pertenece al día anterior
yb = y.copy(); yb.index = yb.index - pd.Timedelta(minutes=30)
c = pd.read_excel(sys.argv[2], header=None, usecols=[0, 2, 5])
c.columns = ["mes", "E_est_GWh", "Pmax_est_MW"]
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
c = c[c.mes.isin(MESES)].reset_index(drop=True).astype({"E_est_GWh": float, "Pmax_est_MW": float})
mes = yb.index.month
e = (yb.groupby(mes).sum() * 0.5 / 1000).values
pmax = yb.groupby(mes).max().values
hp = yb[(yb.index.hour >= 17) & (yb.index.hour < 23)]  # horas punta 18:00-23:00 (periodo inicio 17:30..22:30)
hp = hp[(hp.index.hour * 60 + hp.index.minute >= 17 * 60 + 30)]
pmax_hp = hp.groupby(hp.index.month).max().values
c["E_portal_GWh"] = e; c["dE_%"] = 100 * (c.E_portal_GWh / c.E_est_GWh - 1)
c["Pmax_portal_HP"] = pmax_hp; c["dPhp_%"] = 100 * (c.Pmax_portal_HP / c.Pmax_est_MW - 1)
c["Pmax_portal_todo"] = pmax
print(c.round(2).to_string(index=False))
print("energía anual: portal", round(e.sum(), 1), "GWh | estadística", round(c.E_est_GWh.sum(), 1), "| dif %", round(100 * (e.sum() / c.E_est_GWh.sum() - 1), 2))
