"""Recalcula la energia de hibridacion de cada evidencia con ventanas de secuencia.

Para cada evidencia con las dos ventanas de binding (sRNA y blanco) corre:

- RNAduplex: solo apareamiento intermolecular.
- RNAcofold + RNAfold: MFE del complejo y de cada ventana por separado.
- IntaRNA: hibridacion con accesibilidad y semilla (parametros por defecto).

Las herramientas corren en contenedores de BioContainers con version fija, asi
que solo se necesita Docker. Cada par de secuencias distinto se calcula una vez.
La base no se modifica: el resultado queda en db/analisis/dg_recalculado.csv,
una fila por evidencia, con `estado` indicando por que falta un calculo.

Uso: python scripts\\recalcular_dg.py [--hilos N]
"""
import argparse
import csv
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "db" / "bactericidas.sqlite"
SALIDA = RAIZ / "db" / "analisis" / "dg_recalculado.csv"

VIENNA = "quay.io/biocontainers/viennarna:2.7.2--py312pl5321h245ea3e_1"
INTARNA = "quay.io/biocontainers/intarna:3.4.1--pl5321h077b44d_3"

LARGO_MIN = 7  # semilla por defecto de IntaRNA; debajo hay artefactos de coordenadas
LARGO_MAX_PAR = 1000  # suma de ambas ventanas; RNAcofold escala con el cubo del largo
VALIDA = re.compile(r"^[ACGU]+$")

CONSULTA = """
SELECT e.evidence_id, ss.sequence, ms.sequence, e.delta_g, d.delta_g
FROM interaction_evidence e
LEFT JOIN binding_site bs ON bs.evidence_id = e.evidence_id AND bs.molecule_role = 'sRNA'
LEFT JOIN binding_site bm ON bm.evidence_id = e.evidence_id AND bm.molecule_role = 'mRNA'
LEFT JOIN sequence ss ON ss.seq_id = bs.seq_id
LEFT JOIN sequence ms ON ms.seq_id = bm.seq_id
LEFT JOIN duplex_prediction d ON d.evidence_id = e.evidence_id
ORDER BY e.evidence_id
"""

INTARNA_SH = """#!/bin/sh
# argumentos: id srna blanco. IntaRNA llama id1 al blanco e id2 a la consulta.
IntaRNA -q "$2" -t "$3" --qId=srna --tId="$1" --threads=1 --outMode=C --outNumber=1 \\
  --outCsvCols=id1,E,E_hybrid,ED1,ED2,start1,end1,start2,end2 --outSep=';' 2>/dev/null \\
  | grep -v '^id1'
exit 0
"""


def rna(secuencia):
    return secuencia.upper().replace("T", "U") if secuencia else None


def clasificar(srna, blanco):
    if not srna or not blanco:
        return "sin_secuencia"
    if len(srna) < LARGO_MIN or len(blanco) < LARGO_MIN:
        return "ventana_corta"
    if len(srna) + len(blanco) > LARGO_MAX_PAR:
        return "ventana_larga"
    if not VALIDA.match(srna) or not VALIDA.match(blanco):
        return "caracteres_no_validos"
    return "ok"


def docker(imagen, carpeta, comando):
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{carpeta}:/d", imagen, "sh", "-c", comando],
        check=True,
    )


def escribir(ruta, texto):
    # Fin de linea LF: los contenedores son Linux.
    with open(ruta, "w", newline="\n", encoding="ascii") as f:
        f.write(texto)


def leer_rnafold_csv(rutas):
    """Devuelve {id: (estructura, mfe)} de las salidas --output-format=D."""
    res = {}
    for ruta in rutas:
        with open(ruta, newline="") as f:
            for r in csv.DictReader(f):
                res[r["seq_id"]] = (r["mfe_struct"], float(r["mfe"]))
    return res


def leer_rnafold(rutas):
    """Devuelve {id: (estructura, mfe)} de la salida FASTA de RNAfold."""
    res = {}
    linea_mfe = re.compile(r"^(\S+)\s+\(\s*(-?\d+\.\d+)\)\s*$")
    for ruta in rutas:
        with open(ruta) as f:
            lineas = [x.strip() for x in f if x.strip()]
        for cab, valor in zip(lineas[::3], lineas[2::3]):
            m = linea_mfe.match(valor)
            res[cab[1:]] = (m.group(1), float(m.group(2)))
    return res


def leer_rnaduplex(rutas):
    res = {}
    energia = re.compile(r"\(\s*(-?\d+\.\d+)\)\s*$")
    for ruta in rutas:
        with open(ruta) as f:
            lineas = [x.strip() for x in f if x.strip()]
        for cab, valor in zip(lineas[::2], lineas[1::2]):
            res[cab[1:]] = float(energia.search(valor).group(1))
    return res


def en_paralelo(imagen, d, prefijo, entradas, comando, hilos):
    """Reparte `entradas` (bloques FASTA) en `hilos` procesos independientes.

    La salida de cada bloque va a /d/<prefijo>N.out y sus errores a .err, para
    poder diagnosticar si falta algun resultado.
    """
    for n in range(hilos):
        escribir(d / f"{prefijo}{n}.in", "".join(entradas[n::hilos]))
    partes = " ".join(
        f"({comando.format(n=n)} < /d/{prefijo}{n}.in > /d/{prefijo}{n}.out 2> /d/{prefijo}{n}.err) &"
        for n in range(hilos)
    )
    docker(imagen, str(d), f"{partes} wait")
    return [d / f"{prefijo}{n}.out" for n in range(hilos)]


def errores(d, prefijo):
    """Primeras lineas de error de un paso que no devolvio todos sus resultados."""
    lineas = []
    for ruta in sorted(d.glob(f"{prefijo}*.err")):
        lineas += [x for x in ruta.read_text(errors="replace").splitlines() if "WARNING" not in x]
    return lineas[:10]


def calcular(pares, ventanas, hilos):
    """pares: {id_par: (srna, blanco)}; ventanas: {id_ventana: secuencia}."""
    tmp = tempfile.mkdtemp(prefix="dg_")
    d = Path(tmp)
    try:
        ids = sorted(pares)
        print(f"RNAcofold: {len(ids)} pares", flush=True)
        salidas = en_paralelo(VIENNA, d, "cofold",
                              [f">{i}\n{pares[i][0]}&{pares[i][1]}\n" for i in ids],
                              "RNAcofold --noPS --output-format=D", hilos)
        cofold = leer_rnafold_csv(salidas)
        if len(cofold) != len(ids):
            raise SystemExit(f"RNAcofold: {len(cofold)} de {len(ids)}. {errores(d, 'cofold')}")

        print(f"RNAfold: {len(ventanas)} ventanas", flush=True)
        salidas = en_paralelo(VIENNA, d, "fold",
                              [f">{i}\n{s}\n" for i, s in sorted(ventanas.items())],
                              "RNAfold --noPS", hilos)
        fold = leer_rnafold(salidas)
        if len(fold) != len(ventanas):
            raise SystemExit(f"RNAfold: {len(fold)} de {len(ventanas)}. {errores(d, 'fold')}")

        print("RNAduplex", flush=True)
        salidas = en_paralelo(VIENNA, d, "duplex",
                              [f">{i}\n{pares[i][0]}\n{pares[i][1]}\n" for i in ids],
                              "RNAduplex --noconv", hilos)
        duplex = leer_rnaduplex(salidas)
        if len(duplex) != len(ids):
            raise SystemExit(f"RNAduplex: {len(duplex)} de {len(ids)}. {errores(d, 'duplex')}")

        print("IntaRNA", flush=True)
        escribir(d / "pares.tsv", "".join(f"{i}\t{pares[i][0]}\t{pares[i][1]}\n" for i in ids))
        escribir(d / "intarna.sh", INTARNA_SH)
        docker(INTARNA, tmp, f"xargs -P {hilos} -n 3 sh /d/intarna.sh < /d/pares.tsv > /d/intarna.out")
        intarna = {}
        with open(d / "intarna.out") as f:
            for linea in f:
                c = linea.strip().split(";")
                if len(c) == 9:
                    intarna[c[0]] = c[1:]
        return cofold, fold, duplex, intarna
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def intermolecular(estructura):
    """True si alguna base de la primera ventana se aparea con la segunda."""
    primera = estructura.split("&")[0]
    return primera.count("(") != primera.count(")")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hilos", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = ap.parse_args()

    filas = []
    con = sqlite3.connect(BASE)
    for eid, s, m, dg, dup in con.execute(CONSULTA):
        s, m = rna(s), rna(m)
        filas.append((eid, s, m, dg, dup, clasificar(s, m)))
    con.close()

    # Identificadores deterministas, derivados del orden de las secuencias.
    unicos = sorted({(s, m) for _, s, m, _, _, e in filas if e == "ok"})
    id_par = {p: f"P{i:06d}" for i, p in enumerate(unicos)}
    secuencias = sorted({x for p in unicos for x in p})
    id_ventana = {s: f"V{i:06d}" for i, s in enumerate(secuencias)}
    pares = {i: p for p, i in id_par.items()}
    ventanas = {i: s for s, i in id_ventana.items()}

    cofold, fold, duplex, intarna = calcular(pares, ventanas, args.hilos)

    faltan = [i for i in pares if i not in cofold or i not in duplex]
    faltan += [i for i in ventanas if i not in fold]
    if faltan:
        raise SystemExit(f"Faltan {len(faltan)} resultados, por ejemplo {faltan[:5]}")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    columnas = [
        "evidence_id", "estado", "largo_srna", "largo_blanco", "dg_original",
        "dg_duplex_compendio", "dg_rnaduplex", "dg_rnacofold", "dg_rnafold_srna",
        "dg_rnafold_blanco", "dg_union_cofold", "cofold_intermolecular",
        "dg_intarna", "dg_intarna_hibrido", "ed_intarna_blanco", "ed_intarna_srna",
        "intarna_inicio_blanco", "intarna_fin_blanco", "intarna_inicio_srna", "intarna_fin_srna",
    ]
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columnas)
        for eid, s, m, dg, dup, estado in filas:
            base = [eid, estado, len(s) if s else "", len(m) if m else "", "" if dg is None else dg,
                    "" if dup is None else dup]
            if estado != "ok":
                w.writerow(base + [""] * (len(columnas) - len(base)))
                continue
            p = id_par[(s, m)]
            estructura, mfe = cofold[p]
            fs, fm = fold[id_ventana[s]][1], fold[id_ventana[m]][1]
            ia = intarna.get(p, [""] * 8)
            w.writerow(base + [
                f"{duplex[p]:.2f}", f"{mfe:.2f}", f"{fs:.2f}", f"{fm:.2f}",
                f"{mfe - fs - fm:.2f}", int(intermolecular(estructura)),
                ia[0], ia[1], ia[2], ia[3], ia[4], ia[5], ia[6], ia[7],
            ])
    print(f"{len(filas)} evidencias, {len(unicos)} pares calculados -> {SALIDA}")


if __name__ == "__main__":
    main()
