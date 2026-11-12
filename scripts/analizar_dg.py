"""Compara las energias recalculadas por recalcular_dg.py con las de la base.

Genera db/analisis/resumen_dg_por_tecnica.csv y figs/13_dg_segun_largo_ventana.png
e imprime las cifras globales. A diferencia de los cargadores, requiere pandas y
matplotlib.

Uso: python scripts\\analizar_dg.py
"""
import sqlite3
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

RAIZ = Path(__file__).resolve().parent.parent
TOLERANCIA = 0.051  # los valores se informan con una o dos decimales

METODOS = [
    ("dg_rnaduplex", "RNAduplex", "solo apareamiento"),
    ("dg_union_cofold", "RNAcofold neto", "descuenta el plegado"),
    ("dg_intarna", "IntaRNA", "con accesibilidad"),
]


def spearman(tabla, a, b):
    x = tabla[[a, b]].dropna()
    return round(x[a].corr(x[b], method="spearman"), 3) if len(x) > 10 else None


def coinciden(tabla, a, b):
    x = tabla[[a, b]].dropna()
    return (len(x), round(float(((x[a] - x[b]).abs() < TOLERANCIA).mean()), 4) if len(x) else None)


def resumen(ok):
    filas = []
    for tec, g in ok.groupby("tecnica"):
        n_or, igual = coinciden(g, "dg_rnaduplex", "dg_original")
        filas.append({
            "tecnica": tec,
            "evidencias": len(g),
            "largo_srna_mediana": g.largo_srna.median(),
            "largo_blanco_mediana": g.largo_blanco.median(),
            "dg_rnaduplex_mediana": g.dg_rnaduplex.median(),
            "dg_union_cofold_mediana": g.dg_union_cofold.median(),
            "dg_intarna_mediana": g.dg_intarna.median(),
            "intarna_con_prediccion": round(g.dg_intarna.notna().mean(), 3),
            "n_con_dg_original": n_or,
            "igual_original_rnaduplex": igual,
            "spearman_largo_rnaduplex": spearman(g, "largo_total", "dg_rnaduplex"),
            "spearman_largo_union": spearman(g, "largo_total", "dg_union_cofold"),
            "spearman_largo_intarna": spearman(g, "largo_total", "dg_intarna"),
        })
    return pd.DataFrame(filas).sort_values("evidencias", ascending=False)


def figura(ok, destino):
    fondo, tinta, gris = "#fcfcfb", "#111111", "#555555"
    fig, ejes = plt.subplots(1, 3, figsize=(11, 4.2), sharex=True, sharey=True, facecolor=fondo)
    malla = None
    for eje, (col, nombre, detalle) in zip(ejes, METODOS):
        x = ok[[col, "largo_total"]].dropna()
        malla = eje.hexbin(x.largo_total, x[col].clip(lower=-100), gridsize=38, xscale="log",
                           cmap="Blues", mincnt=1, linewidths=0, norm=LogNorm(vmin=1, vmax=3000))
        rho = x[col].corr(x.largo_total, method="spearman")
        eje.set_title(f"{nombre}\n", loc="left", fontsize=11, fontweight="bold", color=tinta)
        eje.text(0, 1.02, f"{detalle} · ρ = {rho:.2f}".replace(".", ","),
                 transform=eje.transAxes, fontsize=9, color=gris)
        eje.set_facecolor(fondo)
        eje.set_xlabel("Largo sumado de las dos ventanas (nt)", color=gris)
        eje.grid(color="#e4e4e2", linewidth=0.7)
        eje.set_axisbelow(True)
        for lado in ("top", "right"):
            eje.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            eje.spines[lado].set_color("#d0d0ce")
        eje.tick_params(colors=gris, length=3)
    ejes[0].set_ylabel("ΔG (kcal/mol)", color=gris)
    barra = fig.colorbar(malla, ax=ejes, fraction=0.018, pad=0.015)
    barra.set_label("Evidencias por celda", color=gris)
    barra.ax.tick_params(colors=gris)
    barra.outline.set_visible(False)
    fig.text(0.02, -0.04, "Valores por debajo de −100 kcal/mol, recortados en el límite del eje.",
             fontsize=8.5, color=gris)
    fig.savefig(destino, dpi=170, bbox_inches="tight", facecolor=fondo)
    plt.close(fig)


def main():
    d = pd.read_csv(RAIZ / "db" / "analisis" / "dg_recalculado.csv")
    con = sqlite3.connect(RAIZ / "db" / "bactericidas.sqlite")
    tec = pd.read_sql(
        "SELECT e.evidence_id, COALESCE(t.technique_name, 'Sin técnica') AS tecnica "
        "FROM interaction_evidence e LEFT JOIN technique t USING (technique_id)", con)
    con.close()
    ok = d[d.estado == "ok"].merge(tec, on="evidence_id")
    ok["largo_total"] = ok.largo_srna + ok.largo_blanco

    print(d.estado.value_counts().to_string())
    print("RNAduplex = compendio:", coinciden(ok, "dg_rnaduplex", "dg_duplex_compendio"))
    print("RNAduplex = original:", coinciden(ok, "dg_rnaduplex", "dg_original"))
    print("IntaRNA con prediccion:", int(ok.dg_intarna.notna().sum()), "de", len(ok))
    for col, nombre, _ in METODOS:
        print(f"Spearman largo ~ {nombre}:", spearman(ok, "largo_total", col))
    print("Spearman RNAduplex ~ original:", spearman(ok, "dg_rnaduplex", "dg_original"))

    tabla = resumen(ok)
    tabla.to_csv(RAIZ / "db" / "analisis" / "resumen_dg_por_tecnica.csv", index=False, lineterminator="\n")
    print(tabla.to_string(index=False))
    figura(ok, RAIZ / "figs" / "13_dg_segun_largo_ventana.png")


if __name__ == "__main__":
    main()
