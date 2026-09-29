# -*- coding: utf-8 -*-
"""
Exporta la lista de exclusion: lo que ya esta cargado en la base, para descartar
de forma automatica publicaciones e interacciones conocidas al buscar fuentes
nuevas (paso 1 de docs/hoja_de_ruta_nuevas_interacciones.md).

  python scripts/exportar_exclusion.py

Se corre despues de build_db.py y de los cargadores (scripts/load_*.py), y
cada vez que se incorpora una fuente nueva.

Salidas (db/exclusion/)
  * publicaciones.csv: una fila por publicacion, con PMID y DOI normalizado
    (minusculas, sin prefijo https://doi.org/) y lo que aporta a la base.
  * pares.csv: una fila por interaccion sRNA -> blanco, con especie, cepa,
    genoma, las claves normalizadas de ambos ARN y los PMID y metodos que la
    respaldan.
  * alias.csv: todas las formas conocidas de cada ARN (nombre, sinonimos,
    locus tag de NCBI y BioCyc, proteina) con su clave de comparacion. Sirve
    para resolver los nombres que usa un trabajo nuevo a un rna_id existente.

La clave de comparacion es la misma match_key de load_gebhardt2023.py:
minusculas, solo letras y digitos, sin ceros a la izquierda (Sr063 = Sr63,
PA0001 = PA1). Es deliberadamente laxa: un falso "ya existe" se revisa a mano,
un falso "nuevo" termina duplicado en la base.
"""
from __future__ import annotations
import csv, os, re, sqlite3, sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "db", "bactericidas.sqlite")
OUT = os.path.join(BASE, "db", "exclusion")


def name_key(n):                    # identica a build_db.name_key
    return re.sub(r"[^a-z0-9]", "", n.lower()) if n else None


def match_key(n):                   # identica a load_gebhardt2023.match_key
    k = name_key(n)
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", k) if k else None


def norm_doi(d):
    if not d:
        return ""
    d = d.strip().lower()
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d)


def join(values):
    return "|".join(sorted({str(v) for v in values if v not in (None, "")}))


def write(fn, header, rows):
    with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print("  %-18s %6d filas" % (fn, len(rows)))


if not os.path.exists(DB):
    sys.exit("No existe %s: correr antes scripts/build_db.py" % DB)
os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
q = lambda sql: con.execute(sql).fetchall()

# --------------------------------------------------------------- ARN y alias
species_of_strain = {r["strain_id"]: (r["species_name"], r["strain_name"]) for r in q(
    "SELECT st.strain_id, st.strain_name, sp.species_name FROM strain st "
    "LEFT JOIN species sp ON sp.species_taxid = st.species_taxid")}

synonyms = defaultdict(set)
for r in q("SELECT rna_id, synonym FROM rna_synonym"):
    synonyms[r["rna_id"]].add(r["synonym"])

rna, alias_rows, rna_keys = {}, [], defaultdict(set)
for r in q("SELECT * FROM rna ORDER BY rna_id"):
    rid = r["rna_id"]
    rna[rid] = r
    forms = [("nombre", r["rna_name"])] + [("sinonimo", s) for s in sorted(synonyms[rid])]
    forms += [("ncbi_id", r["ncbi_id"]), ("biocyc_id", r["biocyc_id"]),
              ("protein_id", r["protein_id"])]
    seen = set()
    for origen, alias in forms:
        k = match_key(alias)
        if not k or (origen, k) in seen:
            continue
        seen.add((origen, k))
        rna_keys[rid].add(k)
        sp, strain = species_of_strain[r["strain_id"]]
        alias_rows.append([sp, strain, r["strain_id"], rid, r["rna_name"],
                           r["is_srna"], r["is_target"], origen, alias, k])

# claves que en una misma cepa apuntan a mas de un ARN: el cotejo no las
# puede resolver solo y hay que decidir a mano
owners = defaultdict(set)
for row in alias_rows:
    owners[(row[2], row[9])].add(row[3])
ambiguous = {key for key, ids in owners.items() if len(ids) > 1}
for row in alias_rows:
    row.append(int((row[2], row[9]) in ambiguous))

# ------------------------------------------------------ respaldo de cada par
support = defaultdict(lambda: {"ev": set(), "pmid": set(), "met": set(), "tec": set()})
for r in q("""
    SELECT e.interaction_id, e.evidence_id, p.pmid, m.method_name, t.technique_name
    FROM interaction_evidence e
    LEFT JOIN technique t           ON t.technique_id = e.technique_id
    LEFT JOIN study s               ON s.evidence_id = e.evidence_id
    LEFT JOIN publication p         ON p.publication_id = s.publication_id
    LEFT JOIN experimental_method m ON m.method_id = s.method_id"""):
    d = support[r["interaction_id"]]
    d["ev"].add(r["evidence_id"])
    d["pmid"].add(r["pmid"])
    d["met"].add(r["method_name"])
    d["tec"].add(r["technique_name"])

# --------------------------------------------------------------------- pares
pair_rows = []
for r in q("""
    SELECT i.interaction_id, i.genome_id, g.accession_raw, g.strain_id,
           i.srna_rna_id, i.target_rna_id
    FROM interaction i JOIN genome g ON g.genome_id = i.genome_id
    ORDER BY i.interaction_id"""):
    s, t = rna[r["srna_rna_id"]], rna[r["target_rna_id"]]
    sp, strain = species_of_strain[r["strain_id"]]
    d = support[r["interaction_id"]]
    pair_rows.append([
        r["interaction_id"], sp, strain, r["strain_id"], r["genome_id"], r["accession_raw"],
        s["rna_id"], s["rna_name"], match_key(s["rna_name"]), join(rna_keys[s["rna_id"]]),
        t["rna_id"], t["rna_name"], match_key(t["rna_name"]), t["ncbi_id"] or "",
        t["biotype"] or "", join(rna_keys[t["rna_id"]]),
        len(d["ev"]), join(d["pmid"]), join(d["met"]), join(d["tec"])])

# ------------------------------------------------------------- publicaciones
pub_int, pub_ev, pub_sp, pub_met = (defaultdict(set) for _ in range(4))
for r in q("""
    SELECT s.publication_id, e.interaction_id, e.evidence_id, sp.species_name, m.method_name
    FROM study s
    JOIN interaction_evidence e     ON e.evidence_id = s.evidence_id
    JOIN interaction i              ON i.interaction_id = e.interaction_id
    JOIN genome g                   ON g.genome_id = i.genome_id
    JOIN strain st                  ON st.strain_id = g.strain_id
    LEFT JOIN species sp            ON sp.species_taxid = st.species_taxid
    LEFT JOIN experimental_method m ON m.method_id = s.method_id
    WHERE s.publication_id IS NOT NULL"""):
    pid = r["publication_id"]
    pub_int[pid].add(r["interaction_id"])
    pub_ev[pid].add(r["evidence_id"])
    pub_sp[pid].add(r["species_name"])
    pub_met[pid].add(r["method_name"])

pub_rows = []
for r in q("SELECT * FROM publication ORDER BY publication_id"):
    pid = r["publication_id"]
    pub_rows.append([pid, r["pmid"] or "", norm_doi(r["doi"]), r["year"] or "",
                     r["first_author"] or "", r["title"] or "", r["journal"] or "",
                     len(pub_int[pid]), len(pub_ev[pid]), join(pub_sp[pid]),
                     join(pub_met[pid])])

# ------------------------------------------------------------------- salidas
print("Lista de exclusion en %s" % os.path.relpath(OUT, BASE))
write("publicaciones.csv",
      ["publication_id", "pmid", "doi", "year", "first_author", "title", "journal",
       "n_interacciones", "n_evidencias", "especies", "metodos"], pub_rows)
write("pares.csv",
      ["interaction_id", "especie", "cepa", "strain_id", "genome_id", "genoma",
       "srna_id", "srna_nombre", "srna_clave", "srna_claves",
       "blanco_id", "blanco_nombre", "blanco_clave", "blanco_locus", "blanco_biotipo",
       "blanco_claves", "n_evidencias", "pmids", "metodos", "tecnicas"], pair_rows)
write("alias.csv",
      ["especie", "cepa", "strain_id", "rna_id", "rna_nombre", "is_srna", "is_target",
       "origen", "alias", "clave", "clave_ambigua"], alias_rows)

# ---------------------------------------------------------------- resumen
sin_pmid = sum(1 for r in pub_rows if not r[1])
sin_doi = sum(1 for r in pub_rows if not r[2])
sin_datos = [r[0] for r in pub_rows if r[7] == 0]
print()
print("Publicaciones: %d (sin PMID: %d, sin DOI: %d, sin interacciones asociadas: %d)"
      % (len(pub_rows), sin_pmid, sin_doi, len(sin_datos)))
if sin_datos:
    print("  sin interacciones: %s" % ", ".join(sin_datos))
print("Anos: %s" % ", ".join("%s: %d" % kv for kv in sorted(
    Counter(r[3] for r in pub_rows).items(), key=lambda kv: str(kv[0]))))
print("Pares: %d en %d especies" % (len(pair_rows), len({r[1] for r in pair_rows})))
print("Claves ambiguas (misma clave para mas de un ARN en una cepa): %d" % len(ambiguous))
