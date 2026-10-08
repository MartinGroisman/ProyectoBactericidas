# -*- coding: utf-8 -*-
"""
Normalizacion de "Full_data_set_en uso.csv" -> base de datos relacional.

Toma la tabla plana (32.677 filas x 52 columnas) con la que se venia trabajando,
limpia las inconsistencias detectadas y la reparte en tablas normalizadas.

Identificadores nuevos que se crean aca:
  * rna_id  ('RNA-000001')   -> una fila por molecula de ARN (la "sustancia") por cepa
  * seq_id  ('SEQ-<sha1x12>')-> una fila por secuencia nucleotidica unica
  * ademas: strain_id, genome_id, replicon_id, interaction_id, evidence_id,
            publication_id, technique_id, method_id, study_id, binding_site_id

Salida: db/csv/*.csv, db/bactericidas.sqlite, db/schema.sql,
        db/reporte_inconsistencias.md
"""
from __future__ import annotations
import ast, csv, hashlib, os, re, sqlite3, unicodedata
from collections import Counter, OrderedDict, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "Full_data_set_en uso.csv")
OUT = os.path.join(BASE, "db")
CSVDIR = os.path.join(OUT, "csv")
os.makedirs(CSVDIR, exist_ok=True)
csv.field_size_limit(10 ** 7)

# ---------------------------------------------------------------- utilidades
ISSUES = []       # (source_row, column, issue_type, original_value, action) fila por fila
AGG = Counter()   # (column, issue_type, original_value, action) -> n   conversiones sistematicas


def log(row, col, kind, val, action):
    ISSUES.append((row, col, kind, ("" if val is None else str(val))[:200], action))


def log_agg(col, kind, val, action):
    """Para conversiones sistematicas (miles de celdas): se cuentan, no se listan una por una."""
    AGG[(col, kind, ("" if val is None else str(val))[:200], action)] += 1


NULL_TOKENS = {"", "#n/d", "#n/a", "#value!", "#ref!", "#div/0!", "#name?",
               "na", "n/a", "none", "null", "nan", "nd", "."}
# artefacto de recodificacion: bytes '?','?',0xBD que reemplazaron a un caracter UTF-8
MOJIBAKE = re.compile("\\?\\?½|�")


def demojibake(s, repl=" "):
    return MOJIBAKE.sub(repl, s) if isinstance(s, str) else s


def clean(v, row=None, col=None, mojibake_repl=" "):
    """Limpieza generica de texto: trim, NULL canonico, arregla artefactos de encoding."""
    if v is None:
        return None
    s = str(v)
    raw = s
    if MOJIBAKE.search(s):
        s = demojibake(s, mojibake_repl)
        log(row, col, "encoding_artifact", raw, "reemplazado por '%s'" % mojibake_repl)
    s = unicodedata.normalize("NFKC", s).replace("\xa0", " ").strip()
    s = re.sub(r"\s{2,}", " ", s)
    if s.lower() in NULL_TOKENS:
        if raw.strip() != "":
            log_agg(col, "token_nulo", raw.strip(), "-> NULL")
        return None
    return s


def to_int(v, row=None, col=None):
    s = clean(v, row, col)
    if s is None:
        return None
    s2 = s.replace(",", "").replace(" ", "")
    if re.fullmatch(r"-?\d+", s2):
        return int(s2)
    if re.fullmatch(r"-?\d+[.,]0+", s2):
        return int(float(s2.replace(",", ".")))
    log(row, col, "entero_no_parseable", s, "-> NULL")
    return None


def to_float(v, row=None, col=None):
    s = clean(v, row, col)
    if s is None:
        return None
    s2 = s.replace(" ", "")
    if "None" in s2 or "}" in s2 or "{" in s2:   # residuos del JSON de pairing
        log(row, col, "residuo_json", s, "-> NULL")
        return None
    s2 = s2.replace(",", ".")
    try:
        return float(s2)
    except ValueError:
        log(row, col, "decimal_no_parseable", s, "-> NULL")
        return None


BOOL_MAP = {"verdadero": 1, "true": 1, "si": 1, "1": 1,
            "falso": 0, "false": 0, "no": 0, "0": 0}


def to_bool(v, row=None, col=None):
    s = clean(v, row, col)
    if s is None:
        return None
    b = BOOL_MAP.get(s.lower())
    if b is None:
        log(row, col, "booleano_invalido", s, "-> NULL")
        return None
    if s.lower() in ("verdadero", "falso"):
        log_agg(col, "booleano_es_a_entero", s, "-> %d" % b)
    return b


def to_strand(v, row=None, col=None):
    if v is None:
        return None
    s = str(v).strip()
    if s in ("+", "-"):
        return s
    s2 = clean(v, row, col)
    if s2 is None:
        return None
    low = s2.lower()
    if low in ("plus", "forward", "fw", "sense", "1", "+1"):
        log(row, col, "hebra_normalizada", s2, "-> +")
        return "+"
    if low in ("minus", "reverse", "rv", "antisense", "-1"):
        log(row, col, "hebra_normalizada", s2, "-> -")
        return "-"
    log(row, col, "hebra_invalida", s2, "-> NULL")
    return None


SEQ_OK = re.compile(r"^[ACGTUN]+$")


def to_seq(v, row=None, col=None):
    s = clean(v, row, col)
    if s is None:
        return None
    s2 = re.sub(r"[\s\-\.]", "", s).upper()
    if not s2:
        return None
    if not SEQ_OK.fullmatch(s2):
        log(row, col, "secuencia_invalida", s[:60], "-> NULL")
        return None
    if s2 != s:
        log_agg(col, "secuencia_normalizada", "", "trim / mayusculas")
    return s2


def coord_pair(v_start, v_end, row, c_start, c_end):
    """Devuelve (start, end). Repara rangos escritos en una sola celda ('637111-637250')."""
    s_raw = clean(v_start, row, c_start, mojibake_repl="-")
    if s_raw and re.fullmatch(r"\d+\s*-\s*\d+", s_raw):
        a, b = re.split(r"\s*-\s*", s_raw)
        log(row, c_start, "rango_en_una_celda", s_raw, "-> %s / %s" % (a, b))
        return int(a), int(b)
    return to_int(v_start, row, c_start), to_int(v_end, row, c_end)


class Registry:
    """Asigna identificadores nuevos, estables y deterministicos."""

    def __init__(self, prefix, width=4):
        self.prefix, self.width = prefix, width
        self.map, self.rows = OrderedDict(), []

    def get(self, key, make_row):
        if key not in self.map:
            nid = "%s-%0*d" % (self.prefix, self.width, len(self.map) + 1)
            self.map[key] = nid
            self.rows.append(make_row(nid))
        return self.map[key]


def write_csv(name, header, rows):
    p = os.path.join(CSVDIR, name + ".csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print("  %-24s %7d filas" % (name, len(rows)))
    return p


# ---------------------------------------------------------------- 1. lectura
print("1) Leyendo origen ...")
with open(SRC, "r", encoding="latin-1", newline="") as fh:
    rd = csv.DictReader(fh, delimiter=";")
    raw_rows = list(rd)
    COLS = rd.fieldnames
print("   %d filas x %d columnas" % (len(raw_rows), len(COLS)))

seen, rows, n_dup = set(), [], 0
for i, r in enumerate(raw_rows, start=2):           # numero de linea real del archivo
    key = tuple((r.get(c) or "") for c in COLS)
    if key in seen:
        n_dup += 1
        log(i, "*", "fila_duplicada_exacta", r.get("small_rna_name"), "eliminada")
        continue
    seen.add(key)
    r["__line__"] = i
    rows.append(r)
print("   %d filas duplicadas exactas eliminadas -> %d" % (n_dup, len(rows)))

# ---------------------------------------------------------- 2. taxonomia
print("2) Taxonomia, genomas y replicones ...")
phylum, genus, species = OrderedDict(), OrderedDict(), OrderedDict()
strain_reg, genome_reg, replicon_reg = Registry("STR", 4), Registry("GEN", 4), Registry("REP", 4)
strain_of_row, genome_of_row = {}, {}

acc_by_strain = defaultdict(Counter)
for r in rows:
    acc_by_strain[clean(r["microbe_strain_name"])][clean(r["microbe_genome_ncbi_id"])] += 1

for r in rows:
    ln = r["__line__"]
    ph_n = clean(r["microbe_phylum_name"], ln, "microbe_phylum_name")
    ph_t = to_int(r["microbe_phylum_taxid"], ln, "microbe_phylum_taxid")
    ge_n = clean(r["microbe_genus_name"], ln, "microbe_genus_name")
    ge_t = to_int(r["microbe_genus_taxid"], ln, "microbe_genus_taxid")
    sp_n = clean(r["microbe_species_name"], ln, "microbe_species_name")
    sp_t = to_int(r["microbe_species_taxid"], ln, "microbe_species_taxid")
    st_n = clean(r["microbe_strain_name"], ln, "microbe_strain_name")
    st_t = to_int(r["microbe_strain_taxid"], ln, "microbe_strain_taxid")
    gram = clean(r["microbe_gram_type_name"], ln, "microbe_gram_type_name")
    if ph_t:
        phylum.setdefault(ph_t, ph_n)
    if ge_t:
        genus.setdefault(ge_t, (ge_n, ph_t))
    if sp_t:
        species.setdefault(sp_t, (sp_n, ge_t))
    sid = strain_reg.get(st_n, lambda nid, a=st_n, b=st_t, c=sp_t, d=gram: (nid, a, b, c, d))
    strain_of_row[ln] = sid

    acc = clean(r["microbe_genome_ncbi_id"], ln, "microbe_genome_ncbi_id")
    if acc is None:
        log(ln, "microbe_genome_ncbi_id", "genoma_sin_accesion", st_n,
            "se crea un genoma placeholder para la cepa")

    def mk_genome(nid, sid=sid, acc=acc, st_n=st_n):
        parts = [a for a in re.split(r"[;,]\s*", acc) if a] if acc else []
        variants = len([a for a in acc_by_strain[st_n] if a])
        return (nid, sid, acc, len(parts), 1 if variants > 1 else 0)

    gid = genome_reg.get((sid, acc or "SIN_ACCESION"), mk_genome)
    genome_of_row[ln] = gid
    if acc:
        parts = [a for a in re.split(r"[;,]\s*", acc) if a]
        if len(parts) > 1:
            log(ln, "microbe_genome_ncbi_id", "accesiones_multiples_en_una_celda", acc,
                "separadas en %d replicones" % len(parts))
        for k, a in enumerate(parts):
            replicon_reg.get((gid, a), lambda nid, g=gid, a=a, k=k:
                             (nid, g, a, k + 1, "cromosoma" if k == 0 else "replicon_secundario"))

for st_n, c in acc_by_strain.items():
    real = [a for a in c if a]
    if len(real) > 1:
        log("", "microbe_genome_ncbi_id", "cepa_con_varios_ensamblados", "%s: %s" % (st_n, real),
            "un genoma por ensamblado; genome.has_multiple_assemblies=1")

# ------------------------------------------------------------- 3. secuencias
print("3) Secuencias y moleculas de ARN ...")
seq_rows, seq_map = [], {}


def seq_id(seq):
    if seq is None:
        return None
    if seq not in seq_map:
        sid = "SEQ-" + hashlib.sha1(seq.encode()).hexdigest()[:12].upper()
        seq_map[seq] = sid
        gc = sum(seq.count(b) for b in "GC") / float(len(seq))
        mtype = "RNA" if ("U" in seq and "T" not in seq) else "DNA"
        seq_rows.append((sid, len(seq), round(gc, 4), mtype, seq))
    return seq_map[seq]


def name_key(n):
    return re.sub(r"[^a-z0-9]", "", n.lower()) if n else None


rna = OrderedDict()
rna_key_to_id = {}
rna_seq_count = defaultdict(Counter)
rna_syn = defaultdict(set)
rna_locus_rows, locus_seen = [], set()
# atributos booleanos que el CSV repite en cada fila y a veces se contradicen:
# se resuelven por mayoria al final, no con la primera fila que aparezca.
VOTED = ("is_antisense", "is_plasmid_derived", "is_est_utr")
rna_votes = defaultdict(lambda: defaultdict(Counter))


def rna_upsert(ln, strain_id, genome_id, name, ncbi_id, biocyc_id, biotype, product,
               protein_id, synonyms, is_srna, antisense=None, plasmid_derived=None,
               plasmid_acc=None, est_utr=None, annotation_source=None,
               start=None, end=None, strand=None, left_gene=None, right_gene=None, seq=None):
    """Identidad de la molecula: (cepa, ncbi_id); si no hay ncbi_id, (cepa, nombre normalizado);
    y si tampoco hay nombre pero si secuencia, (cepa, seq_id)."""
    nk = name_key(name)
    sq = seq_id(seq)
    if ncbi_id:
        key = (strain_id, "id:" + ncbi_id.lower())
    elif nk:
        key = (strain_id, "nm:" + nk)
    elif biocyc_id:
        key = (strain_id, "bc:" + biocyc_id.lower())
        log(ln, "rna_ncbi_id/rna_name", "molecula_sin_nombre_ni_id_ncbi", biocyc_id,
            "identificada por su id de BioCyc")
    elif sq:
        key = (strain_id, "sq:" + sq)
        log(ln, "rna_name/rna_ncbi_id", "molecula_sin_nombre_ni_id", (seq or "")[:40],
            "identificada por su secuencia (%s)" % sq)
    else:
        return None
    rid = rna_key_to_id.get(key)
    if rid is None:
        rid = "RNA-%06d" % (len(rna_key_to_id) + 1)
        rna_key_to_id[key] = rid
        rna[rid] = dict(rna_id=rid, strain_id=strain_id,
                        rna_name=name, rna_name_key=nk, ncbi_id=ncbi_id, biocyc_id=biocyc_id,
                        biotype=biotype, product=product, protein_id=protein_id,
                        is_srna=0, is_target=0, is_antisense=None,
                        is_plasmid_derived=None, plasmid_ncbi_id=plasmid_acc,
                        is_est_utr=None, annotation_source=annotation_source, seq_id=None)
    e = rna[rid]
    for fld, val in (("is_antisense", antisense), ("is_plasmid_derived", plasmid_derived),
                     ("is_est_utr", est_utr)):
        if val is not None:
            rna_votes[rid][fld][val] += 1
    for fld, val in (("rna_name", name), ("ncbi_id", ncbi_id), ("biocyc_id", biocyc_id),
                     ("biotype", biotype), ("product", product), ("protein_id", protein_id),
                     ("plasmid_ncbi_id", plasmid_acc), ("annotation_source", annotation_source)):
        if val is None:
            continue
        if e[fld] is None:
            e[fld] = val
        elif e[fld] != val:
            if fld == "rna_name" and name_key(str(e[fld])) == name_key(str(val)):
                log_agg("rna_name", "variante_de_mayusculas", "%s / %s" % (e[fld], val),
                        "se conserva '%s'; rna_name_key unifica" % e["rna_name"])
            else:
                log(ln, fld, "valor_contradictorio_en_la_misma_molecula",
                    "%s: %s != %s" % (rid, e[fld], val), "se conserva el primero")
    if is_srna:
        e["is_srna"] = 1
    else:
        e["is_target"] = 1
    if synonyms:
        for s in re.split(r"[;,]\s*", synonyms):
            s = s.strip()
            if s and name_key(s) != nk:
                rna_syn[rid].add(s)
    if sq:
        rna_seq_count[rid][sq] += 1
    if start is not None or end is not None:
        lo, hi, flipped = start, end, 0
        if lo is not None and hi is not None and lo > hi:
            lo, hi, flipped = hi, lo, 1
            if strand is None:
                strand = "-"
        span = (hi - lo + 1) if (lo is not None and hi is not None) else None
        lk = (rid, genome_id, lo, hi, strand)
        if lk not in locus_seen:
            locus_seen.add(lk)
            rna_locus_rows.append(("LOC-%06d" % len(locus_seen), rid, genome_id, lo, hi, strand,
                                   span, flipped, left_gene, right_gene, annotation_source, sq))
            if span and seq and span != len(seq):
                log(ln, "coordenadas", "span_no_coincide_con_la_secuencia",
                    "%s span=%s len_seq=%d" % (rid, span, len(seq)),
                    "se guardan ambos (rna_locus.span_length vs sequence.seq_length)")
    return rid


srna_of_row, target_of_row = {}, {}
for r in rows:
    ln = r["__line__"]
    sid, gid = strain_of_row[ln], genome_of_row[ln]

    s_start, s_end = coord_pair(r["small_rna_start_coordinates"], r["small_rna_end_coordinates"],
                                ln, "small_rna_start_coordinates", "small_rna_end_coordinates")
    s_len_decl = to_int(r["small_rna_length"], ln, "small_rna_length")
    s_seq = to_seq(r["small_rna_sequence"], ln, "small_rna_sequence")
    if s_len_decl and s_seq and s_len_decl != len(s_seq):
        log(ln, "small_rna_length", "longitud_declarada_vs_secuencia",
            "%d != %d" % (s_len_decl, len(s_seq)),
            "se descarta la declarada; vale sequence.seq_length")
    srna_id = rna_upsert(ln, sid, gid,
                         clean(r["small_rna_name"], ln, "small_rna_name"),
                         clean(r["small_rna_ncbi_id"], ln, "small_rna_ncbi_id"),
                         clean(r["small_rna_biocyc_id"], ln, "small_rna_biocyc_id"),
                         None, None, None,   # el biotipo se completa al final ('sRNA')
                         clean(r["small_rna_synonym_names"], ln, "small_rna_synonym_names"),
                         True,
                         annotation_source=clean(r["small_rna_annotation_source"], ln,
                                                 "small_rna_annotation_source"),
                         start=s_start, end=s_end,
                         strand=to_strand(r["small_rna_strand"], ln, "small_rna_strand"),
                         left_gene=clean(r["small_rna_left_gene"], ln, "small_rna_left_gene"),
                         right_gene=clean(r["small_rna_right_gene"], ln, "small_rna_right_gene"),
                         seq=s_seq)
    srna_of_row[ln] = srna_id

    t_start, t_end = coord_pair(r["rna_start_coordinates"], r["rna_end_coordinates"],
                                ln, "rna_start_coordinates", "rna_end_coordinates")
    tgt_id = rna_upsert(ln, sid, gid,
                        clean(r["rna_name"], ln, "rna_name"),
                        clean(r["rna_ncbi_id"], ln, "rna_ncbi_id"),
                        clean(r["rna_biocyc_id"], ln, "rna_biocyc_id"),
                        clean(r["rna_biotype_name"], ln, "rna_biotype_name"),
                        clean(r["rna_product"], ln, "rna_product"),
                        clean(r["rna_protein_id"], ln, "rna_protein_id"),
                        clean(r["rna_synonym_names"], ln, "rna_synonym_names"),
                        False,
                        antisense=to_bool(r["rna_antisense"], ln, "rna_antisense"),
                        plasmid_derived=to_bool(r["rna_plasmid_derived"], ln, "rna_plasmid_derived"),
                        plasmid_acc=clean(r["rna_plasmid_ncbi_id"], ln, "rna_plasmid_ncbi_id"),
                        est_utr=to_bool(r["rna_ESTUTR"], ln, "rna_ESTUTR"),
                        start=t_start, end=t_end,
                        strand=to_strand(r["rna_strand"], ln, "rna_strand"),
                        seq=to_seq(r["rna_sequence"], ln, "rna_sequence"))
    target_of_row[ln] = tgt_id
    if srna_id and tgt_id and srna_id == tgt_id:
        log(ln, "small_rna_name/rna_name", "auto_interaccion", r["small_rna_name"],
            "interaction.is_self_interaction=1")

# atributos booleanos: mayoria simple; si hay empate/conflicto queda registrado
for rid, flds in rna_votes.items():
    for fld, cnt in flds.items():
        top = cnt.most_common()
        rna[rid][fld] = top[0][0]
        if len(top) > 1:
            log("", fld, "atributo_booleano_contradictorio",
                "%s (%s): %s" % (rid, rna[rid]["rna_name"], dict(cnt)),
                "resuelto por mayoria -> %s" % top[0][0])

# los sRNA que nunca fueron anotados como blanco no traen biotipo explicito
n_bt = 0
for e in rna.values():
    if e["biotype"] is None and e["is_srna"]:
        e["biotype"] = "sRNA"
        n_bt += 1
log_agg("rna_biotype_name", "biotipo_faltante_completado", "sRNA",
        "%d moleculas marcadas como sRNA por su rol" % n_bt)

rna_sequence_rows = []
for rid, cnt in rna_seq_count.items():
    top = cnt.most_common()
    rna[rid]["seq_id"] = top[0][0]
    if len(top) > 1:
        log("", "small_rna_sequence/rna_sequence", "molecula_con_varias_secuencias",
            "%s (%s): %d secuencias distintas" % (rid, rna[rid]["rna_name"], len(top)),
            "canonica = la mas frecuente; todas quedan en rna_sequence")
    for k, (sq, n) in enumerate(top):
        rna_sequence_rows.append((rid, sq, 1 if k == 0 else 0, n))

# ------------------------------------------- 4. interacciones y evidencias
print("4) Interacciones, evidencias, sitios de union y estudios ...")
tech_reg = Registry("TEC", 3)


def technique_id(name):
    if not name:
        return None
    m = re.match(r"^(.*?)\s+with\s+(.*)$", name, re.I)
    base, rbp = (m.group(1), m.group(2)) if m else (name, None)
    return tech_reg.get(name, lambda nid: (nid, name, base.strip(),
                                           (rbp or "").strip() or None))


inter_reg = Registry("INT", 6)
pub_reg, meth_reg, reg_reg = Registry("PUB", 4), Registry("MET", 3), Registry("REG", 3)
ev_rows, bind_rows, study_rows = [], [], []
genome_pub = defaultdict(Counter)
genome_batches = defaultdict(set)
ev_dup = set()

for r in rows:
    ln = r["__line__"]
    gid = genome_of_row[ln]
    si, ti = srna_of_row[ln], target_of_row[ln]
    if si is None or ti is None:
        log(ln, "small_rna_name/rna_ncbi_id", "fila_sin_par_identificable",
            "%s / %s" % (r["small_rna_name"], r["rna_ncbi_id"]), "fila descartada")
        continue
    iid = inter_reg.get((gid, si, ti), lambda nid, g=gid, a=si, b=ti:
                        (nid, g, a, b, 1 if a == b else 0))
    tid = technique_id(clean(r["technique"], ln, "technique"))

    p_id = p_energy = p_mre = None
    pairing = clean(r["pairing"])
    if pairing:
        try:
            d = ast.literal_eval(pairing)
            p_id = d.get("pairing_id")
            p_energy = d.get("pairing_energy")
            p_mre = clean(d.get("mre_binding_area"))
        except Exception:
            log(ln, "pairing", "json_no_parseable", pairing[:80], "-> NULL")

    dg = to_float(r["DeltaG"], ln, "DeltaG")
    region = clean(r["Region_involved_mRNA"], ln, "Region_involved_mRNA")
    studies_raw = clean(r["studies"])
    batch = "curado" if studies_raw else "genoma_nuevo"
    genome_batches[gid].add(batch)

    pn_raw = clean(r["publications_no"], ln, "publications_no")
    if pn_raw and not re.fullmatch(r"\d+", pn_raw):
        log(ln, "publications_no", "cita_bibliografica_en_columna_numerica", pn_raw,
            "el conteo se recalcula desde studies; la cita vive en publication")

    sb_s, sb_e = (to_int(r["sRNA_binding_start"], ln, "sRNA_binding_start"),
                  to_int(r["sRNA_binding_end"], ln, "sRNA_binding_end"))
    mb_s, mb_e = (to_int(r["mRNA_binding_start"], ln, "mRNA_binding_start"),
                  to_int(r["mRNA_binding_end"], ln, "mRNA_binding_end"))
    sb_seq = to_seq(r["sRNA_binding_sequence"], ln, "sRNA_binding_sequence")
    mb_seq = to_seq(r["mRNA_binding_sequence"], ln, "mRNA_binding_sequence")

    dupkey = (iid, tid, p_id, sb_s, sb_e, mb_s, mb_e, dg, studies_raw)
    if dupkey in ev_dup:
        log(ln, "*", "evidencia_duplicada", "%s / %s" % (iid, tid), "fila colapsada")
        continue
    ev_dup.add(dupkey)

    eid = "EVI-%06d" % (len(ev_rows) + 1)
    parsed_studies = []
    if studies_raw:
        try:
            parsed_studies = ast.literal_eval(studies_raw)
        except Exception:
            log(ln, "studies", "json_no_parseable", studies_raw[:80], "-> sin estudios")

    pubs_here, meths_here = set(), set()
    for st in parsed_studies:
        pub = st.get("publication") or {}
        pmid = pub.get("publication_PMID")
        doi = clean(pub.get("publication_doi"))
        pkey = str(pmid) if pmid else (doi or clean(pub.get("publication_title")))
        pid = None
        if pkey:
            pid = pub_reg.get(pkey, lambda nid, pub=pub, pmid=pmid, doi=doi: (
                nid, pmid, doi,
                demojibake(clean(pub.get("publication_title")) or "", "-") or None,
                clean(pub.get("publication_journal")),
                pub.get("publication_year"),
                clean(pub.get("publication_first_author")),
                clean(pub.get("publication_corresponding_author_mail"))))
            pubs_here.add(pid)
            genome_pub[gid][pid] += 1
        em = st.get("experimental_method") or {}
        mid = None
        if clean(em.get("experimental_method_name")):
            mid = meth_reg.get(clean(em.get("experimental_method_name")),
                               lambda nid, em=em: (nid,
                                                   clean(em.get("experimental_method_name")),
                                                   clean(em.get("experimental_method_type")),
                                                   clean(em.get("experimental_method_group"))))
            meths_here.add(mid)
        rt = clean((st.get("regulation_type") or {}).get("regulation_type_name"))
        rgid = reg_reg.get(rt, lambda nid, rt=rt: (nid, rt)) if rt else None
        study_rows.append(("STU-%06d" % (len(study_rows) + 1), eid, pid, mid, rgid,
                           clean(st.get("study_rbp")),
                           demojibake(clean(st.get("study_microbe_condition")) or "", "Δ") or None,
                           demojibake(clean(st.get("study_comments")) or "", "Δ") or None))

    n_met = len(meths_here)
    dn = to_int(r["exp_methods_no"], ln, "exp_methods_no")
    if dn is not None and dn != n_met:
        log(ln, "exp_methods_no", "conteo_declarado_incorrecto",
            "declarado=%d real=%d" % (dn, n_met), "se guarda el recalculado")

    ev_rows.append((eid, iid, tid, region, p_id, p_energy, p_mre, dg,
                    len(pubs_here), n_met, batch, ln))

    for role, st_, en_, sq_, rid_ in (("sRNA", sb_s, sb_e, sb_seq, si),
                                      ("mRNA", mb_s, mb_e, mb_seq, ti)):
        if st_ is None and en_ is None and sq_ is None:
            continue
        lo, hi, flipped = st_, en_, 0
        if lo is not None and hi is not None and lo > hi:
            lo, hi, flipped = hi, lo, 1
        span = (hi - lo + 1) if (lo is not None and hi is not None) else None
        if span and sq_ and span != len(sq_):
            log(ln, role + "_binding", "span_no_coincide_con_la_secuencia",
                "span=%d len=%d" % (span, len(sq_)), "se guardan ambos valores")
        frame = None if lo is None else ("genomico" if lo > 100000 else "relativo")
        bind_rows.append(("BND-%06d" % (len(bind_rows) + 1), eid, role, rid_, lo, hi,
                          to_strand(r[role + "_binding_strand"], ln, role + "_binding_strand"),
                          frame, flipped, span, seq_id(sq_)))

# --------------------------------------------- 5. publicaciones por genoma
print("5) Publicaciones por genoma ...")
strain_name_of_id = {v: k for k, v in strain_reg.map.items()}
genome_pub_rows = []
for gid, cnt in genome_pub.items():
    for pid, n in cnt.most_common():
        genome_pub_rows.append(("GPB-%05d" % (len(genome_pub_rows) + 1), gid, pid, n,
                                "derivada_de_studies", "publicada"))
for (sid, acc), gid in genome_reg.map.items():
    if gid not in genome_pub:
        genome_pub_rows.append(("GPB-%05d" % (len(genome_pub_rows) + 1), gid, None, 0,
                                "sin_referencia_en_el_dataset", "pendiente_de_curacion"))
        log("", "studies", "genoma_nuevo_sin_publicacion",
            "%s %s (%s)" % (gid, strain_name_of_id.get(sid), acc),
            "fila en genome_publication con status=pendiente_de_curacion")

# ------------------------------------------------------------- 6. escritura
print("6) Escribiendo CSVs ...")
write_csv("phylum", ["phylum_taxid", "phylum_name"], list(phylum.items()))
write_csv("genus", ["genus_taxid", "genus_name", "phylum_taxid"],
          [(k, v[0], v[1]) for k, v in genus.items()])
write_csv("species", ["species_taxid", "species_name", "genus_taxid"],
          [(k, v[0], v[1]) for k, v in species.items()])
write_csv("strain", ["strain_id", "strain_name", "strain_taxid", "species_taxid", "gram_type"],
          strain_reg.rows)
genome_rows = [tuple(g) + ("genoma_nuevo" if genome_batches.get(g[0]) == {"genoma_nuevo"}
                           else "curado",) for g in genome_reg.rows]
write_csv("genome", ["genome_id", "strain_id", "accession_raw", "n_replicons",
                     "has_multiple_assemblies", "data_batch"], genome_rows)
write_csv("replicon", ["replicon_id", "genome_id", "accession", "replicon_order", "replicon_role"],
          replicon_reg.rows)
write_csv("sequence", ["seq_id", "seq_length", "gc_content", "molecule_type", "sequence"], seq_rows)
RNA_COLS = ["rna_id", "strain_id", "rna_name", "rna_name_key", "ncbi_id", "biocyc_id",
            "biotype", "product", "protein_id", "is_srna", "is_target", "is_antisense",
            "is_plasmid_derived", "plasmid_ncbi_id", "is_est_utr", "annotation_source", "seq_id"]
write_csv("rna", RNA_COLS, [[e[c] for c in RNA_COLS] for e in rna.values()])
write_csv("rna_sequence", ["rna_id", "seq_id", "is_canonical", "n_records"], rna_sequence_rows)
write_csv("rna_synonym", ["rna_id", "synonym"],
          [(k, s) for k, v in rna_syn.items() for s in sorted(v)])
write_csv("rna_locus", ["locus_id", "rna_id", "genome_id", "start_coord", "end_coord", "strand",
                        "span_length", "coords_were_flipped", "left_gene", "right_gene",
                        "annotation_source", "seq_id"], rna_locus_rows)
write_csv("technique", ["technique_id", "technique_name", "base_method", "rbp"], tech_reg.rows)
write_csv("experimental_method", ["method_id", "method_name", "method_type", "method_group"],
          meth_reg.rows)
write_csv("regulation_type", ["regulation_type_id", "regulation_type_name"], reg_reg.rows)
write_csv("publication", ["publication_id", "pmid", "doi", "title", "journal", "year",
                          "first_author", "corresponding_author_mail"], pub_reg.rows)
write_csv("genome_publication", ["genome_publication_id", "genome_id", "publication_id",
                                 "n_evidences", "link_source", "status"], genome_pub_rows)
write_csv("interaction", ["interaction_id", "genome_id", "srna_rna_id", "target_rna_id",
                          "is_self_interaction"], inter_reg.rows)
write_csv("interaction_evidence", ["evidence_id", "interaction_id", "technique_id",
                                   "region_involved_mrna", "source_pairing_id", "pairing_energy",
                                   "mre_binding_area", "delta_g", "n_publications",
                                   "n_exp_methods", "data_batch", "source_line"], ev_rows)
write_csv("binding_site", ["binding_site_id", "evidence_id", "molecule_role", "rna_id",
                           "start_coord", "end_coord", "strand", "coord_frame",
                           "coords_were_flipped", "span_length", "seq_id"], bind_rows)
write_csv("study", ["study_id", "evidence_id", "publication_id", "method_id",
                    "regulation_type_id", "rbp", "microbe_condition", "comments"], study_rows)
# qc_issue = detalle fila por fila + una fila resumen por cada conversion sistematica
qc_rows = [(1, ln, col, kind, val, act) for (ln, col, kind, val, act) in ISSUES]
qc_rows += [(n, "(agregado)", col, kind, val, act)
            for (col, kind, val, act), n in AGG.most_common()]
# columnas en el orden de schema.sql; issue_id explicito, como el resto de las claves
write_csv("qc_issue", ["issue_id", "n_casos", "source_line", "column_name", "issue_type",
                       "original_value", "action"],
          [(i,) + r for i, r in enumerate(qc_rows, 1)])

# --------------------------------------------------------------- 7. sqlite
print("7) Construyendo SQLite ...")
SCHEMA = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"),
              encoding="utf-8").read()
with open(os.path.join(OUT, "schema.sql"), "w", encoding="utf-8") as fh:
    fh.write(SCHEMA)

dbp = os.path.join(OUT, "bactericidas.sqlite")
if os.path.exists(dbp):
    os.remove(dbp)
con = sqlite3.connect(dbp)
con.executescript(SCHEMA)
ORDER = ["phylum", "genus", "species", "strain", "genome", "replicon", "sequence", "rna",
         "rna_sequence", "rna_synonym", "rna_locus", "technique", "experimental_method",
         "regulation_type", "publication", "genome_publication", "interaction",
         "interaction_evidence", "binding_site", "study", "qc_issue"]
for t in ORDER:
    with open(os.path.join(CSVDIR, t + ".csv"), encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        data = [[(None if c == "" else c) for c in row] for row in rd]
    cols = ",".join(hdr)
    con.executemany("INSERT INTO %s (%s) VALUES (%s)" % (t, cols, ",".join("?" * len(hdr))), data)
con.commit()
bad = con.execute("PRAGMA foreign_key_check").fetchall()
print("   foreign_key_check:", "OK" if not bad else bad[:5])
counts = OrderedDict((t, con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]) for t in ORDER)
con.close()

# --------------------------------------------------------------- 8. reporte
print("8) Reporte ...")
by_type = Counter()
for x in ISSUES:
    by_type[x[2]] += 1
for (col, kind, val, act), n in AGG.items():
    by_type[kind] += n
with open(os.path.join(OUT, "reporte_inconsistencias.md"), "w", encoding="utf-8") as fh:
    fh.write("# Reporte de normalizacion\n\n")
    fh.write("Origen: `Full_data_set_en uso.csv` (%d filas x %d columnas)\n\n"
             % (len(raw_rows), len(COLS)))
    fh.write("## Filas por tabla\n\n| Tabla | Filas |\n|---|---:|\n")
    for t, n in counts.items():
        fh.write("| %s | %d |\n" % (t, n))
    fh.write("\n## Inconsistencias detectadas (%d celdas afectadas)\n\n"
             "| Tipo | Casos |\n|---|---:|\n" % sum(by_type.values()))
    for k, v in by_type.most_common():
        fh.write("| %s | %d |\n" % (k, v))
    fh.write("\n## Conversiones sistematicas (agregadas)\n\n"
             "| Columna | Tipo | Valor original | Accion | Casos |\n|---|---|---|---|---:|\n")
    for (col, kind, val, act), n in AGG.most_common(40):
        fh.write("| %s | %s | `%s` | %s | %d |\n" % (col, kind, val, act, n))
    fh.write("\nDetalle fila por fila en `db/csv/qc_issue.csv` y en la tabla `qc_issue`.\n")

print("   %d celdas afectadas (%d eventos detallados + %d agregados)"
      % (sum(by_type.values()), len(ISSUES), len(AGG)))
for k, v in by_type.most_common(40):
    print("     %-50s %d" % (k, v))
print("\nListo:", dbp)
