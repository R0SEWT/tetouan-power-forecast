"""Las tablas del informe, en Markdown, a partir de comparacion.csv, diario.parquet, umbral.csv y fuente.csv.

Uso: python -m experimentos.temperatura.tablas > tablas.md
"""

import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c
from experimentos.temperatura.evaluar import NOMBRES

TRAMOS = ["2025", "2026", "vivo"]
CANDIDATOS = ["c2linea_tp_cdd", "c2linea_tp_dcdd", "c2fija_tp_cdd", "c2fija_tp_dcdd", "c2cdd", "xgb_s_tobs",
              "xgb_s_tmix", "xgb_s_tcdd", "comb_tmix", "comb_tcdd", "comb_tobs"]


def _ic(f, met):
    if pd.isna(f.get(f"d_{met}")):
        return "—"
    return f"{f[f'd_{met}']:+.1f} [{f[f'd_{met}_bajo']:+.1f}, {f[f'd_{met}_alto']:+.1f}]"


def principal(comp, base="c2", area="CENTRO", horizonte="24h"):
    sel = comp[(comp["area"] == area) & (comp["horizonte"] == horizonte) & (comp["base"] == base)]
    lineas = ["| Modelo | Tramo | Días (10 % / 20 %) | Pico, base → modelo (10 %) | Δ 10 % [IC] | Pico (20 %) | Δ 20 % [IC] |",
              "|---|---|---|---|---|---|---|"]
    for m in CANDIDATOS + ["comb", "rf", "xgb_s"]:
        for t in TRAMOS:
            f10 = sel[(sel["modelo"] == m) & (sel["tramo"] == t) & (sel["subconjunto"] == "top10")]
            f20 = sel[(sel["modelo"] == m) & (sel["tramo"] == t) & (sel["subconjunto"] == "top20")]
            if f10.empty:
                continue
            a, b = f10.iloc[0], f20.iloc[0]
            lineas.append(f"| {NOMBRES.get(m, m)} | {t} | {a['dias']} / {b['dias']} | "
                          f"{a['error_pico_abs_base']:.0f} → {a['error_pico_abs']:.0f} | {_ic(a, 'error_pico_abs')} | "
                          f"{b['error_pico_abs_base']:.0f} → {b['error_pico_abs']:.0f} | {_ic(b, 'error_pico_abs')} |")
    return "\n".join(lineas)


def por_area(comp, modelos=("c2linea_tp_cdd", "xgb_s_tobs"), base=None):
    """El pico en los días cálidos para cada área y horizonte (cada modelo frente a su base)."""
    from experimentos.temperatura.evaluar import BASE

    lineas = ["| Modelo | Horizonte | Área | 2025: 10 % / 20 % | 2026: 10 % / 20 % | En vivo: 10 % / 20 % |",
              "|---|---|---|---|---|---|"]
    for m in modelos:
        b = base or BASE[m]
        for h in ("24h", "1h"):
            for a in ("CENTRO", "NORTE", "SUR"):
                celdas = []
                for t in TRAMOS:
                    f = comp[(comp["modelo"] == m) & (comp["base"] == b) & (comp["tramo"] == t) & (comp["horizonte"] == h)
                             & (comp["area"] == a)]
                    if f.empty:
                        celdas.append("—")
                        continue
                    x = {sub: f[f["subconjunto"] == sub].iloc[0] for sub in ("top10", "top20")}
                    celdas.append(f"{_ic(x['top10'], 'error_pico_abs')} / {_ic(x['top20'], 'error_pico_abs')}")
                lineas.append(f"| {NOMBRES.get(m, m)} | {h} | {a.capitalize()} | " + " | ".join(celdas) + " |")
    return "\n".join(lineas)


def guardas(comp, modelo, base="c2"):
    sel = comp[(comp["modelo"] == modelo) & (comp["base"] == base)]
    lineas = ["| Tramo | Horizonte | Área | MAE base | Δ MAE todos [IC] | Sesgo base → modelo | Δ MAE días normales [IC] | Δ pico días normales [IC] |",
              "|---|---|---|---|---|---|---|---|"]
    for t in TRAMOS:
        for h in ("24h", "1h"):
            for a in ("CENTRO", "NORTE", "SUR"):
                f = sel[(sel["tramo"] == t) & (sel["horizonte"] == h) & (sel["area"] == a)]
                todos, normal = f[f["subconjunto"] == "todos"], f[f["subconjunto"] == "normal"]
                if todos.empty:
                    continue
                x, n = todos.iloc[0], normal.iloc[0]
                lineas.append(f"| {t} | {h} | {a.capitalize()} | {x['mae_base']:.1f} | {_ic(x, 'mae')} | "
                              f"{x['sesgo_base']:+.1f} → {x['sesgo']:+.1f} | {_ic(n, 'mae')} | "
                              f"{_ic(n, 'error_pico_abs')} |")
    return "\n".join(lineas)


def dias_calidos(d, modelos=("c2", "c2linea_tp_cdd", "comb", "xgb_s", "xgb_s_tobs", "rf")):
    x = d[(d["area"] == "CENTRO") & (d["horizonte"] == "24h") & d["modelo"].isin(modelos)]
    lineas = ["| Tramo | Modelo | Días | Pico con signo | Pico absoluto | Hora del pico (h) | Sesgo del día | MAE del día |",
              "|---|---|---|---|---|---|---|---|"]
    for t in TRAMOS:
        sub = x[(x["tramo"] == t) & (x["top20"] | (t == "vivo"))]
        for m in modelos:
            g = sub[sub["modelo"] == m]
            if g.empty:
                continue
            lineas.append(f"| {t} | {NOMBRES.get(m, m)} | {len(g)} | {g['error_pico'].mean():+.0f} | "
                          f"{g['error_pico_abs'].mean():.0f} | {g['error_hora_pico'].mean():.1f} | "
                          f"{g['sesgo'].mean():+.0f} | {g['mae'].mean():.0f} |")
    return "\n".join(lineas)


def perdida(comp):
    lineas = ["| Comparación | Tramo | Δ pico 10 % [IC] | Δ pico 20 % [IC] | Δ MAE todos [IC] |", "|---|---|---|---|---|"]
    pares = [("xgb_s_tobs", "xgb_s_tobs_oraculo", "XGB + temp.: pronosticada − observada"),
             ("c2linea_tp_cdd", "c2linea_oraculo", "Corrección en línea: pronosticada − observada")]
    for m, oraculo, nombre in pares:
        for t in ("2025", "2026"):
            filas = comp[(comp["modelo"] == oraculo) & (comp["base"] == m) & (comp["tramo"] == t)
                         & (comp["area"] == "CENTRO") & (comp["horizonte"] == "24h")]
            if filas.empty:
                continue
            g = {s: filas[filas["subconjunto"] == s].iloc[0] for s in ("top10", "top20", "todos")}

            def neg(f, met):  # comp guarda oráculo − pronosticada; aquí se muestra pronosticada − oráculo
                return (f"{-f[f'd_{met}']:+.1f} [{-f[f'd_{met}_alto']:+.1f}, {-f[f'd_{met}_bajo']:+.1f}]")

            lineas.append(f"| {nombre} | {t} | {neg(g['top10'], 'error_pico_abs')} | "
                          f"{neg(g['top20'], 'error_pico_abs')} | {neg(g['todos'], 'mae')} |")
    return "\n".join(lineas)


def vivo_por_dia(d):
    x = d[(d["tramo"] == "vivo") & (d["area"] == "CENTRO") & (d["horizonte"] == "24h")]
    pv = x.pivot_table(index="dia", columns="modelo", values="error_pico")
    base = x[x["modelo"] == "c2"].set_index("dia")
    lineas = ["| Día | Temp. media (°C) | Pico real (MW) | Error del pico, Chronos-2 | Con corrección | XGB + temp. |",
              "|---|---|---|---|---|---|"]
    for dia, f in base.iterrows():
        lineas.append(f"| {dia:%d-%b} | {f['temp_dia']:.1f} | {f['real_max']:,.0f} | {pv.loc[dia, 'c2']:+.0f} | "
                      f"{pv.loc[dia, 'c2linea_tp_cdd']:+.0f} | {pv.loc[dia].get('xgb_s_tobs', np.nan):+.0f} |")
    return "\n".join(lineas)


def _md(df):
    """Una tabla Markdown simple (sin depender de tabulate)."""
    df = df.reset_index() if not isinstance(df.index, pd.RangeIndex) else df
    columnas = [" / ".join(map(str, x)) if isinstance(x, tuple) else str(x) for x in df.columns]
    filas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    filas += ["| " + " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in fila) + " |"
              for fila in df.itertuples(index=False)]
    return "\n".join(filas)


def main():
    comp = pd.read_csv(c.SALIDA / "comparacion.csv")
    d = pd.read_parquet(c.SALIDA / "diario.parquet")
    print("## Principal (frente a Chronos-2 ajustado)\n")
    print(principal(comp))
    print("\n## Principal (XGB frente a XGB + Simons sin temperatura)\n")
    print(principal(comp, base="xgb_s"))
    print("\n## Por área y horizonte\n")
    print(por_area(comp))
    print("\n## Guardas de la corrección en línea\n")
    print(guardas(comp, "c2linea_tp_cdd"))
    print("\n## Guardas de la corrección fija\n")
    print(guardas(comp, "c2fija_tp_cdd"))
    print("\n## Días cálidos\n")
    print(dias_calidos(d))
    print("\n## Pérdida por usar el pronóstico\n")
    print(perdida(comp))
    print("\n## En vivo por día\n")
    print(vivo_por_dia(d))
    u = pd.read_csv(c.SALIDA / "umbral.csv")
    print("\n## Umbral\n")
    print(_md(u.loc[u.groupby(["area", "demanda"])["sse"].idxmin()].reset_index(drop=True)))
    f = pd.read_csv(c.SALIDA / "fuente.csv")
    print("\n## Fuente\n")
    print(_md(f[f["desfase"] == 2].pivot_table(index=["area", "anio"], columns="modelo",
                                               values=["mae_ajustado", "sesgo_dias_sobre_umbral"])))


if __name__ == "__main__":
    main()
