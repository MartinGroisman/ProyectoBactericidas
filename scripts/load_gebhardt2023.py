# -*- coding: utf-8 -*-
"""
Incorpora a la base los datos de Gebhardt et al. 2023 (PNAS 120:e2218407120,
PMID 37285605): RIL-seq con Hfq en Pseudomonas aeruginosa PAO1.

  python scripts/build_db.py                       # si se regenera la base
  python scripts/load_gebhardt2023.py

Las fuentes son los CSV de db/fuentes/gebhardt2023/, obtenidos de los
Datasets S1 y S2 del articulo con scripts/xlsx_a_csv.py.

Que se carga
  * Dataset S1 (S-chimeras, fases exponencial y estacionaria): una
    interaction_evidence por fila que involucra al menos un sRNA, con su study
    (RIL-Seq, Hfq, fase) y dos binding_site (region cubierta por las lecturas
    quimericas de cada ARN, coordenadas genomicas).
  * Dataset S2 (pulso de PhrS, RNA-seq): solo los genes que el propio dataset
    marca como blancos directos de PhrS por RIL-seq ('PhrS target' = yes). El
    resto de los genes desregulados son efectos indirectos, no pares sRNA-blanco.
  * Validaciones de bajo rendimiento descritas en el texto (Fig. 2 y 4): PhrS
    reprime hmgA, PA3340 y antR.

Que no se carga
  * Hojas "Self S-Chimeras": fragmentos de un unico transcripto.
  * S-chimeras sin ningun sRNA (mRNA-mRNA, tRNA-mRNA, etc.).
  * Tablas DESeq2 completas: datos de expresion, no de interaccion. Se usan solo
    para el producto genico de los ARN nuevos, el padj del pulso de PhrS y el
    log2FC con PhrS-deltaseed de los 35 blancos. Los p-valores de la tabla de
    PhrS-deltaseed no se usan: repiten los de PhrS (error de la fuente, ver
    qc_issue); la significancia con deltaseed se toma de su hoja "Significant".

Salidas
  * db/bactericidas.sqlite y las tablas afectadas reexportadas a db/csv/.
  * db/cambios_gebhardt2023.md: bitacora legible de todos los cambios.
  * db/cambios_gebhardt2023.csv: una linea por fila insertada o modificada.

No es acumulativo: si la publicacion ya esta cargada, se detiene. build_db.py
reconstruye la base desde cero, por lo que hay que volver a correr este script
despues de el.
"""
from __future__ import annotations
import csv, hashlib, os, re, sqlite3, sys
from collections import Counter, OrderedDict, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "db", "fuentes", "gebhardt2023")
DB = os.path.join(BASE, "db", "bactericidas.sqlite")
CSVDIR = os.path.join(BASE, "db", "csv")
LOG_MD = os.path.join(BASE, "db", "cambios_gebhardt2023.md")
LOG_CSV = os.path.join(BASE, "db", "cambios_gebhardt2023.csv")

STRAIN, GENOME = "STR-0003", "GEN-0003"         # Pseudomonas aeruginosa PAO1, NC_002516.2
PMID = 37285605
PUB = dict(pmid=PMID, doi="10.1073/pnas.2218407120",
           title="Hfq-licensed RNA-RNA interactome in Pseudomonas aeruginosa reveals a "
                 "keystone sRNA",
           journal="Proceedings of the National Academy of Sciences of the United States "
                   "of America",
           year=2023, first_author="Michael J Gebhardt",
           corresponding_author_mail="simon.dove@childrens.harvard.edu; "
                                     "michael-gebhardt@uiowa.edu")
TAG = "Gebhardt2023"
PHASES = {"S1_exp": ("sd01_S_chimeras_in_Exp_Phase.csv", "Exponential phase"),
          "S1_stat": ("sd01_S_chimeras_in_Stat_Phase.csv", "Stationary phase")}
S2_SIG = "sd02_pEV_vs_pPhrS_Significant.csv"
S2_SIG_DSEED = "sd02_pEV_vs_pPhrS_deltaseed_Signficiant.csv"   # [sic] en el original
S2_FULL = {"wt": "sd02_pEV_vs_pPhrS_Full_DESeq2.csv",
           "dseed": "sd02_pEV_vs_pPhrS_deltaseed_Full_DESeq2.csv"}
TABLES = ["phylum", "genus", "species", "strain", "genome", "replicon", "sequence", "rna",
          "rna_sequence", "rna_synonym", "rna_locus", "technique", "experimental_method",
          "regulation_type", "publication", "genome_publication", "interaction",
          "interaction_evidence", "binding_site", "study", "qc_issue"]

LOCUS = re.compile(r"^(PA\d{4}[a-z]?(?:\.\d+)?)(?:_[35]')?$")   # PA3305.1, PA2770_5'
CDS_LOCUS = re.compile(r"^PA\d{4}[a-z]?$")                       # locus de gen codificante
# la clase "mRNA" de RIL-seq no distingue CDS de UTR (hmgA y antR son "mRNA" pero PhrS se
# aparea en su 5'UTR): solo se registra la region cuando la clase la explicita
REGION = {"5-utr": "5'UTR", "3-utr": "3'UTR"}
BIOTYPE = {"mRNA": "mRNA", "5-utr": "mRNA", "3-utr": "mRNA", "tRNA": "tRNA",
           "tmRNA": "tmRNA", "rRNA": "rRNA", "antisense": "antisense", "intergenic": "intergenic"}


def name_key(n):                    # identica a build_db.name_key
    return re.sub(r"[^a-z0-9]", "", n.lower()) if n else None


def match_key(n):
    """Clave de comparacion mas laxa: ademas ignora ceros a la izquierda (Sr063 = Sr63)."""
    k = name_key(n)
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", k) if k else None


READ_ROWS = OrderedDict()           # archivo -> filas leidas (para la bitacora)


def read(fn):
    with open(os.path.join(SRC, fn), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    READ_ROWS[fn] = len(rows)
    return rows


def sha1(fn):
    with open(os.path.join(SRC, fn), "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Ids:
    """Continua la numeracion correlativa de cada prefijo a partir del maximo existente."""

    def __init__(self, con):
        self.con, self.last = con, {}

    def next(self, table, col, prefix, width):
        if prefix not in self.last:
            m = self.con.execute("SELECT MAX(CAST(SUBSTR(%s, %d) AS INTEGER)) FROM %s WHERE %s "
                                 "LIKE '%s-%%'" % (col, len(prefix) + 2, table, col, prefix)
                                 ).fetchone()[0]
            self.last[prefix] = m or 0
        self.last[prefix] += 1
        return "%s-%0*d" % (prefix, width, self.last[prefix])


con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
if con.execute("SELECT 1 FROM publication WHERE pmid = ?", (PMID,)).fetchone():
    sys.exit("La publicacion PMID %d ya esta cargada. Regenerar con build_db.py antes de "
             "volver a correr este script." % PMID)
count_before = OrderedDict((t, con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
                           for t in TABLES)
ids = Ids(con)
qc = []                 # (source_line, column, issue_type, original_value, action)
origin = {}             # id insertado -> fila de la fuente que lo origino
updates = []            # (tabla, id, campo, valor_anterior, valor_nuevo, origen)


def log(src, col, kind, val, action):
    qc.append((src, col, kind, str(val)[:200], action))


def short(src):
    """Origen sin el prefijo de la publicacion: 'S1_exp #13', 'S2 PA0462'."""
    return src[len(TAG) + 1:] if src.startswith(TAG + " ") else src


def method_id(name):
    return con.execute("SELECT method_id FROM experimental_method WHERE method_name = ?",
                       (name,)).fetchone()[0]


METHOD_NAME = dict(con.execute("SELECT method_id, method_name FROM experimental_method"))
TEC_RILSEQ = con.execute("SELECT technique_id FROM technique WHERE technique_name = "
                         "'RIL-seq with Hfq'").fetchone()[0]
REG = dict(con.execute("SELECT regulation_type_name, regulation_type_id FROM regulation_type"))
REG_NAME = {v: k for k, v in REG.items()}

# productos y nombres de gen de PAO1 segun la tabla DESeq2 completa (Dataset S2)
full = {tag: read(fn) for tag, fn in S2_FULL.items()}
gene_info = {}
for r in full["wt"]:
    gene_info.setdefault(r["Locus Tag"], (r["Gene name"], r["Gene Product"]))
full = {tag: {r["Locus Tag"]: r for r in rows} for tag, rows in full.items()}

# --------------------------------------------------------------- 1. publicacion
pub_id = ids.next("publication", "publication_id", "PUB", 4)
con.execute("INSERT INTO publication VALUES (?,?,?,?,?,?,?,?)",
            (pub_id, PUB["pmid"], PUB["doi"], PUB["title"], PUB["journal"], PUB["year"],
             PUB["first_author"], PUB["corresponding_author_mail"]))
origin[pub_id] = "articulo"

# ------------------------------------------------------ 2. catalogo de ARN PAO1
by_ncbi, by_srna_name, by_name = {}, {}, {}
rna_rows = {}
for rid, name, ncbi, is_srna, biotype in con.execute(
        "SELECT rna_id, rna_name, ncbi_id, is_srna, biotype FROM rna WHERE strain_id = ?",
        (STRAIN,)):
    rna_rows[rid] = dict(name=name, ncbi=ncbi)
    if ncbi:
        by_ncbi.setdefault(ncbi.lower(), rid)
    if name:
        mk = match_key(name)
        if is_srna or biotype == "sRNA":
            by_srna_name.setdefault(mk, rid)
        if not ncbi:
            by_name.setdefault(mk, rid)
new_rna, role_flags = [], defaultdict(set)
synonyms = OrderedDict()          # (rna_id, sinonimo) -> origen


def split_aliases(label):
    parts = [p.strip() for p in re.split(r"\s*/\s*", label or "") if p.strip()]
    # 'PrrH/F1/F2': F1/F2 no son nombres autonomos
    return parts[:1] + [p for p in parts[1:] if len(p) > 2]


def clean_target_name(label, locus):
    """'5_utr_mvfR' -> 'mvfR'; "5'-oprD" -> 'oprD'; 'PA3340' -> None."""
    s = re.sub(r"^(?:[35][_-]utr_|5'\s*-?\s*)", "", label or "")
    s = re.sub(r"(?:-[35]'|\s+[35]')$", "", s).split(" / ")[0].strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,11}", s) or s.upper() == (locus or "").upper():
        return None
    return s


def new_rna_row(name, ncbi, biotype, src, product=None, is_antisense=None):
    rid = ids.next("rna", "rna_id", "RNA", 6)
    new_rna.append(dict(rna_id=rid, strain_id=STRAIN, rna_name=name, rna_name_key=name_key(name),
                        ncbi_id=ncbi, biotype=biotype, product=product,
                        is_antisense=is_antisense, annotation_source=str(PMID)))
    origin[rid] = short(src)
    rna_rows[rid] = dict(name=name, ncbi=ncbi)
    if ncbi:
        by_ncbi[ncbi.lower()] = rid
    if name:
        (by_srna_name if biotype == "sRNA" else by_name).setdefault(match_key(name), rid)
        if not ncbi:
            by_name.setdefault(match_key(name), rid)
    return rid


def add_synonym(rid, syn, src):
    known = {name_key(rna_rows[rid]["name"])} | {name_key(x) for r_, x in synonyms if r_ == rid}
    if name_key(syn) not in known:
        synonyms[(rid, syn)] = short(src)


def resolve_srna(label, gene, src, role="srna"):
    aliases = split_aliases(label)
    locus = gene if LOCUS.fullmatch(gene or "") and "_" not in gene else None
    if locus and CDS_LOCUS.fullmatch(locus):
        log(src, "RNA Gene", "srna_con_locus_de_cds", "%s -> %s" % (label, gene),
            "el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre")
        locus = None
    rid = by_ncbi.get(locus.lower()) if locus else None
    if rid is None:
        rid = next((by_srna_name[match_key(a)] for a in aliases if match_key(a) in by_srna_name),
                   None)
        if rid and locus:
            cur = rna_rows[rid]["ncbi"]
            if cur is None and not any(x["rna_id"] == rid for x in new_rna):
                con.execute("UPDATE rna SET ncbi_id = ? WHERE rna_id = ?", (locus, rid))
                updates.append(("rna", rid, "ncbi_id", None, locus, short(src)))
                rna_rows[rid]["ncbi"] = locus
                by_ncbi[locus.lower()] = rid
                log(src, "rna.ncbi_id", "ncbi_id_completado", "%s (%s)" % (rid, label),
                    "NULL -> %s (locus informado en Dataset S1)" % locus)
            elif cur and cur.lower() != locus.lower():
                log(src, "rna.ncbi_id", "locus_distinto_al_registrado",
                    "%s (%s): %s != %s" % (rid, label, cur, locus), "se conserva el registrado")
    if rid is None:
        rid = new_rna_row(aliases[0] if aliases else gene, locus, "sRNA", src)
    extra = [gene] if gene and not locus and gene != label and not CDS_LOCUS.fullmatch(gene) else []
    for a in aliases + extra:
        for p in split_aliases(a):
            add_synonym(rid, p, src)
    role_flags[rid].add(role)
    return rid


def resolve_target(label, gene, cls, src):
    m = LOCUS.fullmatch(gene or "")
    if m and cls not in ("antisense",):
        locus = m.group(1)
        rid = by_ncbi.get(locus.lower())
        if rid is None:
            gname, product = gene_info.get(locus, (None, None))
            name = gname if gname and gname != locus else clean_target_name(label, locus)
            rid = new_rna_row(name, locus, BIOTYPE[cls] if cls in ("tRNA", "tmRNA", "rRNA")
                              else "mRNA", src, product)
    else:
        rid = by_name.get(match_key(label)) or by_srna_name.get(match_key(label))
        if rid is None:
            rid = new_rna_row(label, None, BIOTYPE.get(cls), src,
                              is_antisense=1 if cls == "antisense" else None)
        if gene and gene != label:
            add_synonym(rid, gene, src)
    role_flags[rid].add("target")
    return rid


# ------------------------------------------------------ 3. interacciones
inter_new = []
inter_ids = {(s, t): i for i, s, t in con.execute(
    "SELECT interaction_id, srna_rna_id, target_rna_id FROM interaction WHERE genome_id = ?",
    (GENOME,))}
preexisting_inter = set(inter_ids.values())
ev_rows, bind_rows, study_rows = [], [], []


def interaction(srna, target, src):
    key = (srna, target)
    if key not in inter_ids:
        iid = ids.next("interaction", "interaction_id", "INT", 6)
        inter_ids[key] = iid
        inter_new.append((iid, GENOME, srna, target, 1 if srna == target else 0))
        origin[iid] = src
    return inter_ids[key]


def evidence(iid, technique, region, src):
    eid = ids.next("interaction_evidence", "evidence_id", "EVI", 6)
    ev_rows.append([eid, iid, technique, region, None, None, None, None, 0, 0, "curado", None])
    origin[eid] = src
    return eid


def study(eid, method, reg, rbp, condition, comments, src):
    sid = ids.next("study", "study_id", "STU", 6)
    study_rows.append((sid, eid, pub_id, method_id(method), REG.get(reg) if reg else None,
                       rbp, condition, comments))
    origin[sid] = src


def is_misannotated_srna(label, gene, cls):
    """Genes codificantes (ahpB, hsiB3, PA5446) rotulados 'sRNA' en Dataset S1."""
    return cls == "sRNA" and CDS_LOCUS.fullmatch(gene or "") and not re.match(r"(?i)sr\d", label)


stats = Counter()
excluded = Counter()                          # (hoja, clase RNA1, clase RNA2) sin sRNA
srna_partners = defaultdict(set)              # sRNA -> blancos distintos en RIL-seq
for sheet, (fn, phase) in PHASES.items():
    for r in read(fn):
        src = "%s #%s" % (sheet, r["Number"])
        side = {}
        for k, ccol in (("1", "annotation class RNA1"), ("2", "annotaiton class RNA2")):
            label, gene, cls = r["RNA%s Name" % k], r["RNA%s Gene" % k], r[ccol]
            novel = ("RNA" + k) in r["novel sRNA"]
            if is_misannotated_srna(label, gene, cls) and not novel:
                log(TAG + " " + src, ccol, "clase_srna_en_gen_codificante",
                    "%s (%s)" % (label, gene), "tratado como mRNA")
                cls = "mRNA"
            side[k] = dict(label=label, gene=gene, cls=cls, srna=(cls == "sRNA" or novel),
                           frm=int(r["RNA%s from" % k]), to=int(r["RNA%s to" % k]),
                           strand=r["RNA%s strand" % k])
        if side["2"]["srna"]:
            s, t = side["2"], side["1"]
        elif side["1"]["srna"]:
            s, t = side["1"], side["2"]
        else:
            stats["excluida_sin_srna"] += 1
            excluded[(sheet, side["1"]["cls"], side["2"]["cls"])] += 1
            continue
        if s is side["2"] and t["srna"]:
            stats["srna_srna"] += 1
        srna_id = resolve_srna(s["label"], s["gene"], TAG + " " + src)
        if t["srna"]:
            tgt_id = resolve_srna(t["label"], t["gene"], TAG + " " + src, role="target")
        else:
            tgt_id = resolve_target(t["label"], t["gene"], t["cls"], TAG + " " + src)
        srna_partners[srna_id].add(tgt_id)
        iid = interaction(srna_id, tgt_id, src)
        eid = evidence(iid, TEC_RILSEQ, None if t["srna"] else REGION.get(t["cls"]), src)
        study(eid, "RIL-Seq", None, "Hfq", phase,
              "Dataset S1 (%s) #%s: RNA1=%s, RNA2=%s; chimeric fragments=%s; odds ratio=%s; "
              "Fisher p=%s" % (fn[5:-4], r["Number"], r["RNA1 Name"], r["RNA2 Name"],
                               r["interactions"], r["odds ratio"],
                               r["Fisher's exact test p-value"]), src)
        for role, x, rid in (("sRNA", s, srna_id), ("mRNA", t, tgt_id)):
            lo, hi = sorted((x["frm"], x["to"]))
            bid = ids.next("binding_site", "binding_site_id", "BND", 6)
            bind_rows.append((bid, eid, role, rid, lo, hi,
                              x["strand"] if x["strand"] in ("+", "-") else None,
                              "genomico", 1 if x["frm"] > x["to"] else 0, hi - lo + 1, None))
            origin[bid] = src
        stats["evidencias_rilseq_" + sheet] += 1

log("%s S1" % TAG, "*", "quimeras_sin_srna_excluidas", stats["excluida_sin_srna"],
    "S-chimeras sin sRNA (mRNA-mRNA, tRNA-mRNA, ...) no se cargan")
log("%s S1" % TAG, "RNA1/RNA2", "par_srna_srna", stats["srna_srna"],
    "ambos ARN son sRNA: se toma RNA2 como regulador (convencion RIL-seq) y RNA1 como blanco")

# ------------------------------------------ 4. Dataset S2: pulso de PhrS (RNA-seq)
phrs = by_ncbi["pa3305.1"]
s2_detail = []
sig_dseed = {r["Locus Tag"] for r in read(S2_SIG_DSEED)}
# la tabla DESeq2 de PhrS-deltaseed repite los p-valores de la de PhrS (error de la fuente)
same_p = sum(1 for loc, r in full["wt"].items()
             if full["dseed"].get(loc, {}).get("adjusted p-value") == r["adjusted p-value"])
log("%s S2" % TAG, "adjusted p-value", "pvalores_repetidos_entre_comparaciones",
    "%d de %d genes con padj identico en pPhrS y pPhrS-deltaseed" % (same_p, len(full["wt"])),
    "no se usan los p-valores de deltaseed; la significancia se toma de su hoja Significant")
s2_rows = read(S2_SIG)
for r in s2_rows:
    if r["PhrS target"].strip().lower() != "yes":
        continue
    loc, lfc = r["Locus Tag"], float(r["log-2 fold change (pPhrS / pEV)"])
    src = "S2 %s" % loc
    tgt = resolve_target(r["Gene name"], loc, "mRNA", TAG + " " + src)
    had_rilseq = (phrs, tgt) in inter_ids
    if not had_rilseq:
        log(TAG + " " + src, "PhrS target", "blanco_s2_sin_quimera_en_s1", loc,
            "se crea la interaccion")
    eid = evidence(interaction(phrs, tgt, src), None, None, src)
    wt, ds = full["wt"].get(loc, {}), full["dseed"].get(loc, {})
    padj = num(wt.get("adjusted p-value"))
    ds_lfc, ds_sig = num(ds.get("log-2 fold change (pPhrS / pEV)")), loc in sig_dseed
    seed = ("PhrS-deltaseed: log2FC=%.2f, %s" % (ds_lfc, "significant" if ds_sig
                                                  else "not significant")
            if ds_lfc is not None else "PhrS-deltaseed: no data")
    reg = "Activation" if lfc > 0 else "Repression"
    study(eid, "RNA-Sequencing", reg, None, "Stationary phase",
          "Dataset S2: 20 min pulse of PhrS (0.2%% arabinose) in PAO1 deltaphrS vs empty vector; "
          "log2FC=%.2f, padj=%s; %s" % (lfc, "%.2g" % padj if padj is not None else "NA", seed),
          src)
    s2_detail.append(dict(locus=loc, name=r["Gene name"], rna=tgt, lfc=lfc, padj=padj,
                          ds_lfc=ds_lfc, ds_sig=ds_sig, reg=reg, eid=eid,
                          rilseq=had_rilseq))
    stats["evidencias_s2"] += 1

# ------------------------------- 5. validaciones de bajo rendimiento (texto, Fig. 2 y 4)
VALIDATIONS = {
    "PA2009": [  # hmgA
        ("Translational fusion reporter", "hmgA::lacZ translational fusion: ~3-fold repression "
         "by ectopic PhrS in deltaphrS; lost with PhrS-deltaseed and PhrS-delta1/2seed (Fig. 2C)"),
        ("Site-directed mutagenesis", "PhrS SM171-SM176 dinucleotide substitutions in the "
         "predicted pairing region (171-177) impair repression of hmgA::lacZ (Fig. 2I)"),
        ("Paired compensatory mutations", "PhrS-SM175 represses the compensatory "
         "hmgA-SM175C::lacZ reporter (Fig. 2J)")],
    "PA3340": [
        ("Translational fusion reporter", "PA3340::lacZ translational fusion: ~1.5-fold higher in "
         "deltaphrS; ~4-fold repression by ectopic PhrS; seed-dependent (Fig. 2D)")],
    "PA2511": [  # antR
        ("Real-Time qRT-PCR", "antR ~5-fold, antA ~40-fold, antB ~15-fold higher in deltaphrS; "
         "complemented by PhrS (Fig. 4C)"),
        ("Translational fusion reporter", "antR::lacZ translational fusion: ~3-fold higher in "
         "deltaphrS; ~16-fold repression by ectopic PhrS; seed-dependent (Fig. 4D)"),
        ("Site-directed mutagenesis", "PhrS SM173-SM182 dinucleotide substitutions; SM178-SM181 "
         "reduce repression of antR::lacZ, SM179 strongest (Fig. 4E)"),
        ("Paired compensatory mutations", "chromosomal phrS-SM179 represses antR-M2C::lacZ "
         "(Fig. 4H)"),
        ("Western blot", "AntR-V reduced by PhrS-SM179 in the antR-M2C background (Fig. 4G)")],
}
val_detail = []
for loc, items in VALIDATIONS.items():
    src = "texto %s" % loc
    tgt = resolve_target(gene_info.get(loc, (loc,))[0], loc, "mRNA", TAG + " " + src)
    eid = evidence(interaction(phrs, tgt, src), None, "5'UTR", src)
    for meth, comment in items:
        study(eid, meth, "Repression", None, "Stationary phase", comment, src)
        val_detail.append((loc, rna_rows[tgt]["name"] or "—", eid, meth, comment))
    stats["evidencias_validacion"] += 1

# ----------------------------------------------------------- 6. conteos y escritura
studies_by_ev = defaultdict(set)
for s in study_rows:
    studies_by_ev[s[1]].add(s[3])
for ev in ev_rows:
    ev[8], ev[9] = 1, len(studies_by_ev[ev[0]])

for row in new_rna:
    row.update(is_srna=1 if "srna" in role_flags[row["rna_id"]] else 0,
               is_target=1 if "target" in role_flags[row["rna_id"]] else 0)
con.executemany(
    "INSERT INTO rna (rna_id, strain_id, rna_name, rna_name_key, ncbi_id, biotype, product, "
    "is_srna, is_target, is_antisense, annotation_source) VALUES "
    "(:rna_id, :strain_id, :rna_name, :rna_name_key, :ncbi_id, :biotype, :product, :is_srna, "
    ":is_target, :is_antisense, :annotation_source)", new_rna)
new_ids = {x["rna_id"] for x in new_rna}
for rid, roles in role_flags.items():          # moleculas existentes con un rol nuevo
    if rid in new_ids:
        continue
    for role, col in (("srna", "is_srna"), ("target", "is_target")):
        old = con.execute("SELECT %s FROM rna WHERE rna_id = ?" % col, (rid,)).fetchone()[0]
        if role in roles and old != 1:
            con.execute("UPDATE rna SET %s = 1 WHERE rna_id = ?" % col, (rid,))
            updates.append(("rna", rid, col, old, 1, "rol observado en Dataset S1"))
            log(TAG, "rna." + col, "rol_nuevo_en_molecula_existente",
                "%s (%s)" % (rid, rna_rows[rid]["name"]), "0 -> 1")
syn_rows = [k for k in synonyms if not con.execute(
    "SELECT 1 FROM rna_synonym WHERE rna_id = ? AND synonym = ?", k).fetchone()]
con.executemany("INSERT INTO rna_synonym VALUES (?,?)", syn_rows)
con.executemany("INSERT INTO interaction VALUES (?,?,?,?,?)", inter_new)
con.executemany("INSERT INTO interaction_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ev_rows)
con.executemany("INSERT INTO binding_site VALUES (?,?,?,?,?,?,?,?,?,?,?)", bind_rows)
con.executemany("INSERT INTO study VALUES (?,?,?,?,?,?,?,?)", study_rows)
gpb_id = ids.next("genome_publication", "genome_publication_id", "GPB", 5)
con.execute("INSERT INTO genome_publication VALUES (?,?,?,?,?,?)",
            (gpb_id, GENOME, pub_id, len(study_rows), "derivada_de_studies", "publicada"))
qc_ids = []
for q in qc:
    cur = con.execute("INSERT INTO qc_issue (source_line, column_name, issue_type, "
                      "original_value, action, n_casos) VALUES (?,?,?,?,?,1)", q)
    qc_ids.append(cur.lastrowid)

bad = con.execute("PRAGMA foreign_key_check").fetchall()
if bad:
    con.rollback()
    sys.exit("foreign_key_check fallo, no se guardo nada: %s" % bad[:5])
# la transaccion sigue abierta: si la bitacora falla, la base queda como estaba
count_after = OrderedDict((t, con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
                          for t in TABLES)

# ------------------------------------------------ 7. bitacora fila por fila (CSV)
rname = lambda rid: rna_rows[rid]["name"] or rna_rows[rid]["ncbi"] or rid  # noqa: E731
change_rows = [("publication", pub_id, "INSERT", "", "", "PMID %d | %s | %s %d" % (
    PMID, PUB["first_author"], "PNAS", PUB["year"]), origin[pub_id]),
    ("genome_publication", gpb_id, "INSERT", "", "",
     "%s | %s | n_evidences=%d" % (GENOME, pub_id, len(study_rows)), "articulo")]
for x in new_rna:
    change_rows.append(("rna", x["rna_id"], "INSERT", "", "",
                        "%s | ncbi_id=%s | %s | is_srna=%d is_target=%d" % (
                            x["rna_name"] or "", x["ncbi_id"] or "", x["biotype"] or "",
                            x["is_srna"], x["is_target"]), origin[x["rna_id"]]))
for tbl, rid, fld, old, new, src in updates:
    change_rows.append((tbl, rid, "UPDATE", fld, "" if old is None else old, new, src))
for rid, syn in syn_rows:
    change_rows.append(("rna_synonym", rid, "INSERT", "synonym", "", syn, synonyms[(rid, syn)]))
for iid, _, s, t, _self in inter_new:
    change_rows.append(("interaction", iid, "INSERT", "", "", "%s (%s) -> %s (%s)" % (
        s, rname(s), t, rname(t)), origin[iid]))
for ev in ev_rows:
    change_rows.append(("interaction_evidence", ev[0], "INSERT", "", "",
                        "%s | technique=%s | region=%s" % (ev[1], ev[2] or "", ev[3] or ""),
                        origin[ev[0]]))
for b in bind_rows:
    change_rows.append(("binding_site", b[0], "INSERT", "", "", "%s | %s %s %d-%d (%s)" % (
        b[1], b[2], b[3], b[4], b[5], b[6] or ""), origin[b[0]]))
for s in study_rows:
    change_rows.append(("study", s[0], "INSERT", "", "", "%s | %s | %s | %s" % (
        s[1], METHOD_NAME[s[3]], REG_NAME.get(s[4], ""), s[6] or ""), origin[s[0]]))
for qid, q in zip(qc_ids, qc):
    change_rows.append(("qc_issue", qid, "INSERT", "", "", "%s: %s" % (q[2], q[3]), q[0]))
with open(LOG_CSV, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["tabla", "id", "operacion", "campo", "valor_anterior", "valor_nuevo", "origen"])
    w.writerows(change_rows)

# ------------------------------------------------ 8. bitacora legible (Markdown)


def rng(prefix_rows):
    return "%s … %s" % (prefix_rows[0], prefix_rows[-1]) if prefix_rows else "—"


NUMERIC = {"n", "n blancos", "Antes", "Después", "Insertadas", "Modificadas", "Filas leídas",
           "Cargadas", "Excluidas (sin sRNA)", "log2FC", "padj", "Δseed log2FC", "issue_id"}


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---:" if h in NUMERIC else "---" for h in header) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


upd_by_table = Counter(u[0] for u in updates)
ins_by_table = Counter({t: count_after[t] - count_before[t] for t in TABLES})
L = []
L.append("# Bitácora de cambios: Gebhardt et al. 2023\n")
L.append("Registro de todas las modificaciones que `scripts/load_gebhardt2023.py` "
         "aplica sobre `db/bactericidas.sqlite` al incorporar el artículo. El archivo se "
         "regenera en cada carga, y el detalle fila por fila está en "
         "`db/cambios_gebhardt2023.csv`, con %d líneas.\n" % len(change_rows))
L.append("## Publicación\n")
L.append(md_table(["Campo", "Valor"], [
    ("publication_id", pub_id), ("PMID", PMID), ("DOI", PUB["doi"]), ("Título", PUB["title"]),
    ("Revista", PUB["journal"]), ("Año", PUB["year"]), ("Primer autor", PUB["first_author"]),
    ("Correspondencia", PUB["corresponding_author_mail"]),
    ("Cepa / genoma", "Pseudomonas aeruginosa PAO1 (%s) / %s" % (STRAIN, GENOME))]) + "\n")

L.append("## Archivos de origen\n")
L.append("Todos provienen de `db/fuentes/gebhardt2023/` y se obtuvieron de los Datasets "
         "suplementarios S1 y S2 con `scripts/xlsx_a_csv.py`. El SHA-1 permite verificar que "
         "la fuente no cambió entre una carga y otra.\n")
L.append(md_table(["Archivo", "Filas leídas", "Uso", "SHA-1"], [
    (fn, n, {"sd01_S_chimeras_in_Exp_Phase.csv": "interacciones RIL-seq, fase exponencial",
             "sd01_S_chimeras_in_Stat_Phase.csv": "interacciones RIL-seq, fase estacionaria",
             S2_SIG: "blancos de PhrS con cambio de expresión tras el pulso",
             S2_FULL["wt"]: "producto génico de ARN nuevos; padj del pulso de PhrS",
             S2_SIG_DSEED: "significancia con PhrS-Δseed (según los autores)",
             S2_FULL["dseed"]: "log2FC con PhrS-Δseed para los blancos del pulso"}[fn],
     "`%s`" % sha1(fn)[:12]) for fn, n in sorted(READ_ROWS.items())]) + "\n")
L.append("También se conservan `sd01_Legend.csv` y `sd02_Description.csv`, que describen las "
         "columnas de cada dataset; el cargador no las lee.\n")

L.append("## Resumen por tabla\n")
L.append(md_table(["Tabla", "Antes", "Insertadas", "Modificadas", "Después"], [
    (t, count_before[t], ins_by_table[t] or "", upd_by_table.get(t, "") or "", count_after[t])
    for t in TABLES if ins_by_table[t] or upd_by_table.get(t)]) + "\n")
L.append("El resto de las tablas (taxonomía, genomas, replicones, secuencias, locus, técnicas, "
         "métodos y tipos de regulación) no cambia. Se reutilizaron las técnicas y los métodos "
         "que ya existían: `%s` (RIL-seq with Hfq) y los métodos %s.\n" % (
             TEC_RILSEQ, ", ".join("`%s` (%s)" % (m, METHOD_NAME[m]) for m in
                                   sorted({s[3] for s in study_rows}))))
L.append("Rangos de identificadores asignados:\n")
for label, lst in (("rna", [x["rna_id"] for x in new_rna]),
                   ("interaction", [i[0] for i in inter_new]),
                   ("interaction_evidence", [e[0] for e in ev_rows]),
                   ("binding_site", [b[0] for b in bind_rows]),
                   ("study", [s[0] for s in study_rows]),
                   ("qc_issue", ["%d" % q for q in qc_ids])):
    L.append("- `%s`: %s (%d)" % (label, rng(lst), len(lst)))
L.append("")

L.append("## Registros existentes modificados\n")
L.append("La carga modifica %d registros que ya estaban en la base; todos se listan a "
         "continuación. En ningún caso se sobrescribe un valor que no fuera nulo o cero.\n"
         % len(updates))
L.append(md_table(["Tabla", "ID", "Molécula", "Campo", "Antes", "Después", "Motivo / origen"], [
    (u[0], u[1], rname(u[1]), u[2], "NULL" if u[3] is None else u[3], u[4], u[5])
    for u in updates]) + "\n")
old_syn = [(r, s) for r, s in syn_rows if r not in new_ids]
if old_syn:
    L.append("Sinónimos agregados a moléculas que ya existían:\n")
    L.append(md_table(["rna_id", "Molécula", "Sinónimo", "Origen"],
                      [(r, rname(r), s, synonyms[(r, s)]) for r, s in old_syn]) + "\n")

L.append("## Dataset S1: interacciones RIL-seq\n")
L.append(md_table(["Hoja", "Filas leídas", "Cargadas", "Excluidas (sin sRNA)"], [
    (fn, READ_ROWS[fn], stats["evidencias_rilseq_" + sh],
     sum(v for (s_, a, b), v in excluded.items() if s_ == sh))
    for sh, (fn, _) in PHASES.items()]) + "\n")
L.append("Cada fila cargada genera una `interaction_evidence` con técnica `%s`, un `study` "
         "con método RIL-Seq, `rbp = Hfq` y la fase en `microbe_condition`, y dos "
         "`binding_site`. El campo `comments` del `study` guarda el número de fila de la "
         "hoja, los fragmentos quiméricos, el *odds ratio* y el p de Fisher. En %d filas "
         "ambos ARN son sRNA; en ese caso se tomó RNA2 como regulador.\n"
         % (TEC_RILSEQ, stats["srna_srna"]))
L.append("Filas excluidas, por combinación de clases (RNA1 / RNA2):\n")
exc = Counter()
for (sh, a, b), v in excluded.items():
    exc[(a, b)] += v
L.append(md_table(["RNA1", "RNA2", "n"], [(a, b, v) for (a, b), v in exc.most_common()]) + "\n")
L.append("Además quedaron sin cargar las hojas *Self S-Chimeras* (fragmentos de un mismo "
         "transcripto) y las filas de encabezado repetidas de cada hoja.\n")

n_new_pairs = sum(1 for i in inter_new)
reused = sorted({iid for iid in inter_ids.values() if iid in preexisting_inter} &
                {e[1] for e in ev_rows})
L.append("### Interacciones\n")
L.append("Se crearon %d interacciones (pares sRNA → blanco) y %d pares que ya existían "
         "recibieron evidencia nueva. Estos últimos son coincidencias con estudios previos:\n"
         % (n_new_pairs, len(reused)))
prev = []
for iid in reused:
    s_, t_ = con.execute("SELECT srna_rna_id, target_rna_id FROM interaction WHERE "
                         "interaction_id = ?", (iid,)).fetchone()
    pubs = [r[0] for r in con.execute(
        "SELECT DISTINCT p.first_author || ' ' || p.year FROM study st JOIN interaction_evidence "
        "e USING(evidence_id) JOIN publication p USING(publication_id) WHERE e.interaction_id = ? "
        "AND st.publication_id <> ? ORDER BY 1", (iid, pub_id))]
    prev.append((iid, rname(s_), rname(t_), "; ".join(pubs)))
L.append(md_table(["interaction_id", "sRNA", "Blanco", "Publicaciones previas"], prev) + "\n")

L.append("### sRNA\n")
new_srna = [x for x in new_rna if x["biotype"] == "sRNA"]
ROLE = {(1, 0): "regulador", (0, 1): "blanco", (1, 1): "regulador y blanco"}
L.append("Se incorporaron %d sRNA nuevos (`biotype = sRNA`). De ellos, %d actúan como "
         "reguladores y %d aparecen sólo como blanco de otro sRNA. La tabla indica el rol "
         "de cada uno, que determina `is_srna` / `is_target`, y la cantidad de blancos "
         "distintos que tiene como regulador en este trabajo:\n"
         % (len(new_srna), sum(x["is_srna"] for x in new_srna),
            sum(1 for x in new_srna if not x["is_srna"])))
L.append(md_table(["rna_id", "Nombre", "ncbi_id", "Sinónimos", "Rol", "n blancos", "Origen"], [
    (x["rna_id"], x["rna_name"], x["ncbi_id"] or "",
     ", ".join(s for r, s in synonyms if r == x["rna_id"]),
     ROLE[(x["is_srna"], x["is_target"])],
     len(srna_partners.get(x["rna_id"], ())), origin[x["rna_id"]]) for x in new_srna]) + "\n")
old_srna = sorted((r for r in srna_partners if r not in new_ids),
                  key=lambda r: -len(srna_partners[r]))
L.append("sRNA que ya estaban en la base y reciben interacciones de este trabajo:\n")
L.append(md_table(["rna_id", "Nombre", "ncbi_id", "n blancos"], [
    (r, rname(r), rna_rows[r]["ncbi"] or "", len(srna_partners[r])) for r in old_srna]) + "\n")

L.append("### Blancos nuevos\n")
bt = Counter((x["biotype"], x["is_srna"]) for x in new_rna if x["biotype"] != "sRNA")
L.append("Se agregaron %d moléculas que actúan sólo como blanco. Los mRNA se identifican "
         "por locus y toman nombre y producto de la tabla DESeq2. Los transcriptos "
         "antisentido e intergénicos se identifican por el nombre que figura en el "
         "dataset. El detalle de cada uno está en el CSV de cambios.\n"
         % sum(bt.values()))
L.append(md_table(["biotype", "n"], [(b, v) for (b, _), v in bt.most_common()]) + "\n")

L.append("## Dataset S2: pulso de PhrS (RNA-seq)\n")
L.append("De los %d genes con |log2FC| > 1 y padj ≤ 0,05 tras 20 min de expresión de PhrS "
         "en fase estacionaria, se cargan sólo los %d que el dataset marca como blanco "
         "directo de PhrS por RIL-seq. Cada uno genera una `interaction_evidence` sin "
         "técnica y un `study` con método RNA-Sequencing. La regulación se asigna según el "
         "signo del log2FC.\n" % (READ_ROWS[S2_SIG], len(s2_detail)))
L.append("**Error en la fuente.** En la tabla DESeq2 completa de PhrS-Δseed, el p-valor y el "
         "padj son idénticos a los de PhrS en %d de %d genes, aunque los log2FC difieren. "
         "Es un error de copia del archivo suplementario, así que esos p-valores no se "
         "usan. La columna *Δseed signif.* indica si el gen figura en la hoja de "
         "significativos de PhrS-Δseed publicada por los autores. Un blanco que responde a "
         "PhrS pero no a PhrS-Δseed depende de la región semilla (170–181).\n"
         % (same_p, len(full["wt"])))
L.append(md_table(["Locus", "Gen", "rna_id", "log2FC", "padj", "Regulación", "Δseed log2FC",
                   "Δseed signif.", "Quimera en S1", "evidence_id"], [
    (d["locus"], d["name"], d["rna"], "%.2f" % d["lfc"],
     "%.2g" % d["padj"] if d["padj"] is not None else "NA", d["reg"],
     "%.2f" % d["ds_lfc"] if d["ds_lfc"] is not None else "NA",
     "sí" if d["ds_sig"] else "no",
     "sí" if d["rilseq"] else "no", d["eid"]) for d in s2_detail]) + "\n")
L.append("Resumen: %d de los %d blancos siguen alterados con PhrS-Δseed y %d dejan de "
         "estarlo (efecto dependiente de la semilla).\n"
         % (sum(d["ds_sig"] for d in s2_detail), len(s2_detail),
            sum(not d["ds_sig"] for d in s2_detail)))

L.append("## Validaciones de bajo rendimiento (texto del artículo)\n")
L.append("Las tres validaciones son de represión en el 5'UTR del blanco, en fase "
         "estacionaria. Cada blanco tiene una `interaction_evidence` propia, sin técnica, "
         "con un `study` por método.\n")
L.append(md_table(["Locus", "Gen", "evidence_id", "Método", "Resultado"],
                  [(a, b, c, d, e) for a, b, c, d, e in val_detail]) + "\n")

L.append("## Registros en qc_issue\n")
L.append(md_table(["issue_id", "Origen", "Columna", "Tipo", "Valor", "Acción"], [
    (qid, q[0], q[1], q[2], q[3], q[4]) for qid, q in zip(qc_ids, qc)]) + "\n")
with open(LOG_MD, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
con.commit()

# reexporta las tablas modificadas para que db/csv siga en sincronia con la base
for t in ("publication", "genome_publication", "rna", "rna_synonym", "interaction",
          "interaction_evidence", "binding_site", "study", "qc_issue"):
    cur = con.execute("SELECT * FROM %s" % t)   # qc_issue: issue_id es el rowid
    cols = [d[0] for d in cur.description]
    with open(os.path.join(CSVDIR, t + ".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows([["" if v is None else v for v in row] for row in cur])
con.close()

print("Gebhardt 2023 (%s) cargado en %s" % (pub_id, os.path.relpath(DB, BASE)))
for k, v in [("rna nuevas", len(new_rna)), ("sinonimos", len(syn_rows)),
             ("interacciones nuevas", len(inter_new)), ("evidencias", len(ev_rows)),
             ("binding_site", len(bind_rows)), ("study", len(study_rows)),
             ("registros modificados", len(updates)), ("qc_issue", len(qc))] + sorted(stats.items()):
    print("  %-34s %6d" % (k, v))
print("Bitacora: %s, %s" % (os.path.relpath(LOG_MD, BASE), os.path.relpath(LOG_CSV, BASE)))
