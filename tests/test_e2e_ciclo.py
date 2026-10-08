# -*- coding: utf-8 -*-
"""
Prueba end to end de la cadena completa, sobre una copia limpia del
repositorio en un directorio temporal (no toca la base ni los CSV del arbol
de trabajo).

  python tests/test_e2e_ciclo.py

Requiere "Full_data_set_en uso.csv" en la raiz y acceso a PubMed y Europe PMC.
Tarda unos 10 minutos.

  1. build_db -> load_gebhardt2023 -> exportar_exclusion: los archivos
     versionados que se regeneran (tablas de db/csv, reporte, bitacora de
     Gebhardt, publicaciones.csv) tienen que salir identicos a los del
     repositorio, y cada CSV de db/csv tiene que coincidir con su tabla de la
     base: mismo nombre, mismas columnas en el mismo orden y mismas filas.
  A. Base sin Gebhardt (solo build_db), exclusion y busqueda desde cero:
     Gebhardt 2023 aparece como candidato de prioridad 1.
  B. Cribado manual: decisiones sobre dos filas y una fila agregada a mano
     (paso 2b de la hoja de ruta).
  C. load_gebhardt2023, exclusion y busqueda otra vez: Gebhardt queda con
     en_base = si, el cribado y la fila manual se conservan, no hay claves
     duplicadas y la bitacora acumula las dos corridas.
"""
from __future__ import annotations
import csv, os, re, shutil, sqlite3, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUDO = "Full_data_set_en uso.csv"
GEB = "PMID:37285605"                       # Gebhardt et al. 2023
OTRA = "PMID:41405210"                      # RIL-seq en A. baumannii
MANUAL = "MANUAL:regulondb-001"
# salidas de los scripts que no se copian: tienen que regenerarse
NO_COPIAR = ("db/exclusion/", "db/candidatos/", "tests/")
VERSIONADOS = ["db/reporte_inconsistencias.md", "db/cambios_gebhardt2023.md",
               "db/cambios_gebhardt2023.csv", "db/exclusion/publicaciones.csv"]
csv.field_size_limit(10 ** 7)

fallas = []


def check(cond, msg):
    print("  [%s] %s" % ("OK" if cond else "FALLA", msg))
    if not cond:
        fallas.append(msg)


def copia_limpia(destino):
    archivos = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.splitlines()
    for f in archivos:
        if f.startswith(NO_COPIAR) or not os.path.exists(os.path.join(REPO, f)):
            continue
        os.makedirs(os.path.join(destino, os.path.dirname(f)), exist_ok=True)
        shutil.copy2(os.path.join(REPO, f), os.path.join(destino, f))
    shutil.copy2(os.path.join(REPO, CRUDO), os.path.join(destino, CRUDO))


def correr(copia, script):
    r = subprocess.run([sys.executable, os.path.join("scripts", script)], cwd=copia,
                       capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    print("  $ %s -> exit %d" % (script, r.returncode))
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("fallo %s" % script)
    return r.stdout


def mismo_texto(a, b):                      # ignora CRLF/LF (core.autocrlf)
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read().replace(b"\r\n", b"\n") == fb.read().replace(b"\r\n", b"\n")


def leer(cand):
    with open(cand, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def csv_vs_sqlite(copia):
    """Cada tabla de la base tiene su CSV en db/csv, con las mismas columnas y filas."""
    con = sqlite3.connect(os.path.join(copia, "db", "bactericidas.sqlite"))
    tablas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' "
                                        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    csvdir = os.path.join(copia, "db", "csv")
    archivos = sorted(f[:-4] for f in os.listdir(csvdir) if f.endswith(".csv"))
    check(archivos == tablas, "db/csv tiene un CSV por tabla y ninguno de mas")
    for t in sorted(set(tablas) & set(archivos)):
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
        filas = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
        with open(os.path.join(csvdir, t + ".csv"), encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd)
            n = sum(1 for _ in rd)
        check(hdr == cols and n == filas,
              "db/csv/%s.csv coincide con la tabla (%d columnas, %d filas)" % (t, len(cols), filas)
              if hdr == cols and n == filas else
              "db/csv/%s.csv: columnas %s, %d filas; tabla: %s, %d filas"
              % (t, hdr, n, cols, filas))
    con.close()


def resumen(out):
    return "\n".join("     " + l for l in out.strip().splitlines()
                     if l.startswith(("Ya en", "Candidatos", "  prioridad", "Consultas con")))


def main():
    if not os.path.exists(os.path.join(REPO, CRUDO)):
        print("Falta %s en la raiz del repositorio" % CRUDO)
        return 2
    copia = tempfile.mkdtemp(prefix="bactericidas_e2e_")
    try:
        copia_limpia(copia)
        cand = os.path.join(copia, "db", "candidatos", "candidatos.csv")
        log = os.path.join(copia, "db", "candidatos", "busquedas.csv")

        print("1. cadena de carga completa y determinismo")
        for s in ("build_db.py", "load_gebhardt2023.py", "exportar_exclusion.py"):
            correr(copia, s)
        csv_vs_sqlite(copia)
        tablas = sorted("db/csv/" + f for f in os.listdir(os.path.join(REPO, "db", "csv")))
        for f in tablas + VERSIONADOS:
            check(mismo_texto(os.path.join(copia, f), os.path.join(REPO, f)),
                  "%s identico al del repositorio" % f)

        print("A. base sin Gebhardt, busqueda desde cero")
        correr(copia, "build_db.py")
        correr(copia, "exportar_exclusion.py")
        out = correr(copia, "buscar_candidatos.py")
        print(resumen(out))
        A = leer(cand)
        a = {r["clave"]: r for r in A}
        check("Candidatos pendientes: %d " % len(A) in out, "el resumen cuenta todas las filas")
        check("Ya en la base (descartados por PMID o DOI): 4" in out,
              "descarta los 4 trabajos de 2022 de la base")
        check(GEB in a, "Gebhardt 2023 aparece como candidato cuando no esta cargado")
        check(a.get(GEB, {}).get("prioridad_sugerida") == "1", "Gebhardt queda con prioridad 1")
        check(len(A) == len(a), "sin claves duplicadas")
        check(all(r["fecha_alta"] for r in A), "todas las filas tienen fecha_alta")
        check(not any(r["en_base"] for r in A), "ninguna fila marcada en_base")

        print("B. cribado manual y fila de una base de interacciones (2b)")
        campos = list(A[0].keys())
        for r in A:
            if r["clave"] == GEB:
                r.update(decision="incluir", notas="RIL-seq PAO1")
            if r["clave"] == OTRA:
                r.update(decision="incluir", notas="A. baumannii")
        A.append(dict({c: "" for c in campos}, clave=MANUAL, titulo="fila agregada desde RegulonDB",
                      fuente_busqueda="manual:RegulonDB", decision="pendiente"))
        with open(cand, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            w.writerows(A)

        print("C. carga de Gebhardt, exclusion regenerada y nueva busqueda")
        correr(copia, "load_gebhardt2023.py")
        correr(copia, "exportar_exclusion.py")
        out = correr(copia, "buscar_candidatos.py")
        print(resumen(out))
        C = leer(cand)
        c = {r["clave"]: r for r in C}
        check("Ya en la base (descartados por PMID o DOI): 5" in out,
              "ahora descarta 5 (incluye Gebhardt)")
        check(c.get(GEB, {}).get("en_base") == "si", "Gebhardt queda marcado en_base = si")
        check(c.get(GEB, {}).get("decision") == "incluir"
              and c[GEB]["notas"] == "RIL-seq PAO1", "Gebhardt conserva su cribado")
        check(c.get(OTRA, {}).get("decision") == "incluir"
              and c[OTRA]["notas"] == "A. baumannii", "otra fila conserva su cribado")
        check(c.get(MANUAL, {}).get("fuente_busqueda") == "manual:RegulonDB",
              "la fila manual se conserva")
        check(sum(1 for r in C if r["en_base"]) == 1, "solo Gebhardt queda en_base")
        check(len(C) == len(c), "sin claves duplicadas")
        check(set(a) <= set(c), "ninguna fila de A se pierde")
        check(all(c[k]["fecha_alta"] == a[k]["fecha_alta"] for k in a),
              "fecha_alta de las filas previas no cambia")
        prios = re.findall(r"^  prioridad (\S+) ", out, re.M)
        check(len(prios) == len(set(prios)), "cada prioridad aparece una sola vez en el resumen")
        check("Candidatos pendientes: %d " % (len(C) - 1) in out,
              "pendientes = filas menos la cargada")
        with open(log, encoding="utf-8") as fh:
            n_log = sum(1 for _ in fh) - 1
        check(n_log == 24, "la bitacora acumula las dos corridas (12 + 12 consultas): %d" % n_log)
        nuevas = set(c) - set(a) - {MANUAL}
        print("  filas nuevas en C: %d (0 salvo que Europe PMC haya respondido distinto)"
              % len(nuevas))
    finally:
        shutil.rmtree(copia, ignore_errors=True)

    print("\nRESULTADO: %s" % ("TODO OK" if not fallas else "%d FALLAS" % len(fallas)))
    return 1 if fallas else 0


def test_e2e_ciclo():                       # para pytest
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
