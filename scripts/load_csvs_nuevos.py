# -*- coding: utf-8 -*-
"""
Incorpora a la base los estudios nuevos de db/fuentes/csvs_nuevos/: un
compendio externo de interacciones sRNA-ARN (estudios, entidades,
interacciones, duplex predichos y regiones consenso) exportado en otro esquema.

  python scripts/build_db.py                 # si se regenera la base
  python scripts/load_gebhardt2023.py
  python scripts/completar_csvs_nuevos.py    # solo si cambian las fuentes (usa red)
  python scripts/load_csvs_nuevos.py

Que se carga
  * Los estudios de las ingestas posteriores a la migracion (fuente_ingesta
    distinta de 'migracion_v1') cuya publicacion no esta todavia en la base.
    Cada fila de interacciones.csv da una interaction_evidence con su study,
    hasta dos binding_site y, si los trae, una fila de evidence_stats (lecturas,
    p, odds ratio o enriquecimiento, nivel de confianza).
  * duplex.csv: la prediccion del duplex de cada evidencia cargada y, cuando
    la fila de la fuente coincide sin ambiguedad con una evidencia que ya
    estaba (mismas ventanas de binding y mismo pairing_id), tambien la de esa.
  * regiones_consenso.csv: en srna_seed_region.
  * clase_hfq de entidades_rna.csv: en rna.hfq_class de cada molecula a la
    que corresponde la entidad (sin sobrescribir un valor existente).

Que no se carga
  * Las filas 'migracion_v1': son la propia base migrada al otro esquema.
  * Los estudios de publicaciones que ya estan en la base (Melamed 2016 y
    2020, Gebhardt 2023): son reingestas del mismo experimento, que la fuente
    marca como duplicado ("no sumar").
  * Estudios sin interacciones (CLIP-seq de Bergman 2024).
  * Filas con una molecula de otro organismo que el del estudio (fago lambda
    en Silverman 2025).

Los datos que la fuente no trae (titulo, revista, cepa, taxonomia) salen de
db/fuentes/csvs_nuevos/complementos/, generados por completar_csvs_nuevos.py.

Salidas
  * db/bactericidas.sqlite y todas sus tablas reexportadas a db/csv/.
  * db/cambios_csvs_nuevos.md: bitacora legible.
  * db/cambios_csvs_nuevos.csv: una linea por registro de catalogo insertado o
    modificado (publicaciones, taxonomia, genomas, tecnicas, metodos, ARN,
    sinonimos, regiones consenso, qc). Las evidencias y sus tablas hijas se
    resumen por estudio en la bitacora legible; cada una remite a su fila de
    la fuente por evidence_stats.source_ref o study.comments.

No es acumulativo: si ya se cargo, se detiene. Hay que volver a correrlo
despues de build_db.py y load_gebhardt2023.py.
"""
from __future__ import annotations
import csv, hashlib, os, re, sqlite3, sys
from collections import Counter, OrderedDict, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "db", "fuentes", "csvs_nuevos")
COMP = os.path.join(SRC, "complementos")
DB = os.path.join(BASE, "db", "bactericidas.sqlite")
CSVDIR = os.path.join(BASE, "db", "csv")
LOG_MD = os.path.join(BASE, "db", "cambios_csvs_nuevos.md")
LOG_CSV = os.path.join(BASE, "db", "cambios_csvs_nuevos.csv")
TAG = "CsvsNuevos"
csv.field_size_limit(10 ** 8)

TABLES = ["phylum", "genus", "species", "strain", "genome", "replicon", "sequence", "rna",
          "rna_sequence", "rna_synonym", "rna_locus", "technique", "experimental_method",
          "regulation_type", "publication", "genome_publication", "interaction",
          "interaction_evidence", "binding_site", "study", "evidence_stats",
          "duplex_prediction", "srna_seed_region", "qc_issue"]

# tecnica = metodo base + proteina; MAPS es la tecnica ya existente sin proteina
TECH_BASE = {"RIL-Seq": "RIL-seq", "iRIL-Seq": "iRIL-seq", "Hi-GRIL": "Hi-GRIL-seq",
             "CLASH": "CLASH", "MAP-Seq": "MS2-affinity purification"}
BIOTYPE = {"mRNA": "mRNA", "IGR": "intergenic", "asRNA": "antisense", "sRNA": "sRNA",
           "tRNA": "tRNA", "rRNA": "rRNA", "tmRNA": "tmRNA", "ncRNA": "ncRNA",
           "otro_ncRNA": "ncRNA", "misc_RNA": "misc_RNA", "Pseudogene": "Pseudogene",
           "UGR": "UGR", "riboswitch": "riboswitch", "CRISPR": "CRISPR"}
# region_blanco tambien trae la clase del blanco (IGR, AS, sRNA...): solo las
# regiones de un mRNA van a region_involved_mrna
REGION = {"CDS": "CDS", "5UTR": "5'UTR", "3UTR": "3'UTR"}
FRAME = {"genomica": "genomico", "relativa_al_transcripto": "relativo"}
BOOL = {"1": 1, "TRUE": 1, "0": 0, "FALSE": 0}
# la fuente registra la UTR de un gen como entidad propia ('thrL.5UTR'); en la base
# la UTR es parte del mRNA del gen, como en load_gebhardt2023.py
UTR = re.compile(r"^(.+)\.(?:EST)?[35]UTR$")
SEQ_OK = re.compile(r"^[ACGTUN]+$")


def name_key(n):                    # identica a build_db.name_key
    return re.sub(r"[^a-z0-9]", "", n.lower()) if n else None


def match_key(n):                   # identica a load_gebhardt2023.match_key
    k = name_key(n)
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", k) if k else None


def read(fn, folder=SRC, delim=";"):
    with open(os.path.join(folder, fn), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delim))


def sha1(fn):
    with open(os.path.join(SRC, fn), "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def accs_of(raw):                   # 'NC_1; NC_2' -> ['NC_1', 'NC_2']
    return [a.strip() for a in (raw or "").split(";") if a.strip()]


def unversioned(a):
    return a.split(".")[0].upper()


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


# ------------------------------------------------------------------ lectura
for fn in ("publicaciones.csv", "genomas.csv"):
    if not os.path.exists(os.path.join(COMP, fn)):
        sys.exit("Falta %s: correr antes scripts/completar_csvs_nuevos.py" % fn)
con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
if con.execute("SELECT 1 FROM qc_issue WHERE source_line LIKE ?", (TAG + "%",)).fetchone():
    sys.exit("Los CSV nuevos ya estan cargados. Regenerar con build_db.py y "
             "load_gebhardt2023.py antes de volver a correr este script.")
if not con.execute("SELECT 1 FROM publication WHERE pmid = 37285605").fetchone():
    sys.exit("Falta Gebhardt 2023: correr antes scripts/load_gebhardt2023.py")

READ_ROWS = OrderedDict()
SOURCES = OrderedDict()
for fn in ("estudios.csv", "entidades_rna.csv", "interacciones.csv", "duplex.csv",
           "regiones_consenso.csv"):
    SOURCES[fn] = read(fn)
    READ_ROWS[fn] = len(SOURCES[fn])
estudios = SOURCES["estudios.csv"]
entidades = {r["entidad_id"]: r for r in SOURCES["entidades_rna.csv"]}
filas = SOURCES["interacciones.csv"]
duplex = {r["interaccion_id"]: r for r in SOURCES["duplex.csv"]}
regiones = SOURCES["regiones_consenso.csv"]
comp_pub = {r["doi_fuente"].lower(): r for r in read("publicaciones.csv", COMP, ",")}
comp_gen = {r["accesiones"]: r for r in read("genomas.csv", COMP, ",")}

count_before = OrderedDict((t, con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
                           for t in TABLES)
ids = Ids(con)
qc = []                     # (source_line, column, issue_type, original_value, action, n)
QC_AGG = Counter()          # (source_line, column, issue_type, value, action) -> n
updates = []                # (tabla, id, campo, valor_anterior, valor_nuevo, origen)
change_rows = []            # bitacora CSV de catalogos
stats = Counter()


def log(src, col, kind, val, action):
    qc.append((src, col, kind, str(val)[:200], action, 1))


def log_agg(src, col, kind, val, action):
    QC_AGG[(src, col, kind, str(val)[:200], action)] += 1


def insert(table, row, src, summary):
    con.execute("INSERT INTO %s VALUES (%s)" % (table, ",".join("?" * len(row))), row)
    change_rows.append((table, row[0], "INSERT", "", "", summary, src))


# ---------------------------------------------------------- parseo de valores
MILES = re.compile(r"-?\d{1,3}(?:\.\d{3}){2,}")
# columnas que en un estudio vienen mayormente con el separador de miles corrompido:
# ahi tampoco son confiables los valores que si se pueden leer ('2341432108')
corrupt_cols = set()
for col in ("odds_ratio",):
    tot, bad = Counter(), Counter()
    for r in filas:
        if r[col].strip():
            tot[r["estudio_id"]] += 1
            bad[r["estudio_id"]] += bool(MILES.fullmatch(r[col].strip()))
    corrupt_cols |= {(est, col) for est in tot if bad[est] > tot[est] / 2}


def num(v, est, col, kind="real"):
    """Numero de la fuente o None, dejando constancia de cada valor descartado."""
    v = (v or "").strip()
    if not v:
        return None
    src = "%s %s" % (TAG, est)
    if v.lower() in ("nan", "inf", "-inf", "#num!"):
        log_agg(src, col, "valor_no_finito", v, "-> NULL")
        return None
    if (est, col) in corrupt_cols and not MILES.fullmatch(v):
        log_agg(src, col, "columna_corrompida_en_el_estudio", "",
                "-> NULL (la mayoria de los valores del estudio tienen el separador de miles "
                "corrompido)")
        return None
    if MILES.fullmatch(v):
        log_agg(src, col, "separador_de_miles_corrompido", "",
                "-> NULL (la coma decimal se perdio; el valor no es recuperable)")
        return None
    if kind == "log2" and re.fullmatch(r"-?[1-9]\d*\.\d{3}", v):
        log_agg(src, col, "ambiguo_separador_de_miles", "",
                "-> NULL (tres decimales: puede ser un separador de miles)")
        return None
    if re.fullmatch(r"-?\d+,\d+(?:[eE][-+]?\d+)?", v):
        log_agg(src, col, "coma_decimal", "", "convertida a punto")
        v = v.replace(",", ".")
    try:
        x = float(v)
    except ValueError:
        log_agg(src, col, "valor_no_numerico", v, "-> NULL")
        return None
    if kind == "int":
        if x != int(x):
            log_agg(src, col, "entero_con_decimales", v, "-> NULL")
            return None
        return int(x)
    return x


def seq(v):
    s = re.sub(r"\s", "", v or "").upper()
    return s if s and SEQ_OK.fullmatch(s) else None


def seq_id(s, src):
    """Como build_db.seq_id: una fila por secuencia distinta, id por sha1."""
    if not s:
        return None
    sid = "SEQ-" + hashlib.sha1(s.encode()).hexdigest()[:12].upper()
    if sid not in known_seq:
        known_seq.add(sid)
        gc = sum(s.count(b) for b in "GC") / float(len(s))
        con.execute("INSERT INTO sequence VALUES (?,?,?,?,?)",
                    (sid, len(s), round(gc, 4), "RNA" if ("U" in s and "T" not in s) else "DNA",
                     s))
        stats["secuencias_nuevas"] += 1
    return sid


known_seq = {r[0] for r in con.execute("SELECT seq_id FROM sequence")}

# --------------------------------------------------------- 1. que se carga
base_pmids = {str(r[0]) for r in con.execute("SELECT pmid FROM publication WHERE pmid IS NOT NULL")}
base_dois = {(r[0] or "").lower() for r in con.execute("SELECT doi FROM publication")}
rows_by_est = Counter(r["estudio_id"] for r in filas)
cargar, no_cargados = OrderedDict(), []
for e in estudios:
    eid_ = e["estudio_id"]
    if e["fuente_ingesta"] == "migracion_v1":
        stats["estudios_migracion_v1"] += 1
        continue
    pub = comp_pub.get(e["publication_doi"].strip().lower())
    if not rows_by_est[eid_]:
        no_cargados.append((e, pub, "sin filas en interacciones.csv"))
        log("%s %s" % (TAG, eid_), "*", "estudio_sin_interacciones", e["metodo_nombre"],
            "no se carga")
        continue
    if pub is None:
        sys.exit("%s: falta su publicacion en complementos/publicaciones.csv" % eid_)
    if pub["pmid"] in base_pmids or pub["doi"].lower() in base_dois:
        no_cargados.append((e, pub, "publicacion ya en la base"))
        log("%s %s" % (TAG, eid_), "*", "publicacion_ya_en_la_base",
            "PMID %s, %d filas" % (pub["pmid"], rows_by_est[eid_]),
            "no se carga: reingesta del mismo experimento")
        continue
    cargar[eid_] = dict(e=e, pub=pub)

# ---------------------------------------------------------- 2. publicaciones
pub_ids = OrderedDict()                       # doi_fuente -> publication_id
for x in cargar.values():
    p = x["pub"]
    if p["doi_fuente"] in pub_ids:
        continue
    pid = ids.next("publication", "publication_id", "PUB", 4)
    pub_ids[p["doi_fuente"]] = pid
    insert("publication", (pid, int(p["pmid"]) if p["pmid"] else None, p["doi"] or None,
                           p["title"] or None, p["journal"] or None,
                           int(p["year"]) if p["year"] else None, p["first_author"] or None,
                           p["corresponding_author_mail"] or None), "complementos",
           "PMID %s | %s %s | %s" % (p["pmid"], p["first_author"], p["year"], p["journal"]))
    if p["nota"]:
        log("%s %s" % (TAG, p["doi_fuente"]), "publication_doi", "metadato_corregido",
            p["doi_fuente"], p["nota"])

# ---------------------------------------------------- 3. taxonomia y genomas
replicon_owner = defaultdict(list)            # accesion sin version -> [genome_id]
genome_accs = defaultdict(set)
for gid, acc in con.execute("SELECT genome_id, accession FROM replicon ORDER BY genome_id"):
    replicon_owner[unversioned(acc)].append(gid)
    genome_accs[gid].add(unversioned(acc))
strain_of_genome = dict(con.execute("SELECT genome_id, strain_id FROM genome"))
species_of_strain = dict(con.execute("SELECT strain_id, species_taxid FROM strain"))
species_name = dict(con.execute("SELECT species_taxid, species_name FROM species"))
strain_taxid = dict(con.execute("SELECT strain_id, strain_taxid FROM strain"))
strain_by_name = {n: s for s, n in con.execute("SELECT strain_id, strain_name FROM strain")}
genome_cache, new_genomes = {}, []


def ensure_taxonomy(g, src):
    for table, key, row, summary in (
            ("phylum", int(g["phylum_taxid"]), (int(g["phylum_taxid"]), g["phylum_name"]),
             g["phylum_name"]),
            ("genus", int(g["genus_taxid"]), (int(g["genus_taxid"]), g["genus_name"],
                                              int(g["phylum_taxid"])), g["genus_name"]),
            ("species", int(g["species_taxid"]), (int(g["species_taxid"]), g["species_name"],
                                                  int(g["genus_taxid"])), g["species_name"])):
        col = table + "_taxid"
        if not con.execute("SELECT 1 FROM %s WHERE %s = ?" % (table, col), (key,)).fetchone():
            insert(table, row, src, summary)
            if table == "species":
                species_name[key] = g["species_name"]


def genome_for(e, create=True):
    """Genoma del estudio: el que ya tiene alguna de sus accesiones o, si ninguno, uno
    nuevo a partir de complementos/genomas.csv."""
    accs = accs_of(e["ensamblado_accession"])
    key = ";".join(accs)
    if key in genome_cache:
        return genome_cache[key]
    gid = None
    src = "%s %s" % (TAG, e["estudio_id"])
    for a in accs:
        owners = replicon_owner.get(unversioned(a))
        if owners:
            gid = owners[0]
            if create and len(owners) > 1:
                log(src, "ensamblado_accession", "accesion_en_varios_genomas",
                    "%s: %s" % (a, ", ".join(owners)),
                    "se usa %s (%s), el primero cargado" % (gid, strain_of_genome[gid]))
            break
    if gid is None and not create:
        return None
    if gid is None:
        g = comp_gen[key]
        ensure_taxonomy(g, "complementos")
        sid = strain_by_name.get(g["strain_name"])
        if sid is None:
            sid = ids.next("strain", "strain_id", "STR", 4)
            insert("strain", (sid, g["strain_name"],
                              int(g["strain_taxid"]) if g["strain_taxid"] else None,
                              int(g["species_taxid"]), g["gram_type"] or None), "complementos",
                   "%s | taxid %s | %s" % (g["strain_name"], g["strain_taxid"] or "-",
                                           g["gram_type"]))
            strain_by_name[g["strain_name"]] = sid
            species_of_strain[sid] = int(g["species_taxid"])
            strain_taxid[sid] = int(g["strain_taxid"]) if g["strain_taxid"] else None
            if g["nota"]:
                log(src, "strain_name", "cepa_distinta_del_ensamblado", g["strain_name"],
                    g["nota"])
        gid = ids.next("genome", "genome_id", "GEN", 4)
        insert("genome", (gid, sid, key, len(accs), 0, "curado"), src,
               "%s | %s" % (g["strain_name"], key))
        strain_of_genome[gid] = sid
        new_genomes.append(gid)
        for k, a in enumerate(accs):
            rid = ids.next("replicon", "replicon_id", "REP", 4)
            insert("replicon", (rid, gid, a, k + 1,
                                "cromosoma" if k == 0 else "replicon_secundario"), src,
                   "%s | %s" % (gid, a))
            replicon_owner[unversioned(a)].append(gid)
            genome_accs[gid].add(unversioned(a))
    elif create:
        extra = [a for a in accs if unversioned(a) not in genome_accs[gid]]
        if extra:
            log(src, "ensamblado_accession", "replicon_no_registrado_en_el_genoma",
                "%s: %s" % (gid, ", ".join(extra)),
                "se usa el genoma existente; el replicon no se agrega")
    genome_cache[key] = gid
    return gid


# ------------------------------------------------- 4. tecnicas y metodos
tech_by_name = dict(con.execute("SELECT technique_name, technique_id FROM technique"))
method_by_name = dict(con.execute("SELECT method_name, method_id FROM experimental_method"))
REG = dict(con.execute("SELECT regulation_type_name, regulation_type_id FROM regulation_type"))


def technique_for(e):
    base = TECH_BASE[e["metodo_nombre"]]
    rbp = e["rbp"].strip() or None
    name = base if base == "MS2-affinity purification" or not rbp else "%s with %s" % (base, rbp)
    if name not in tech_by_name:
        tid = ids.next("technique", "technique_id", "TEC", 3)
        insert("technique", (tid, name, base, rbp), "%s %s" % (TAG, e["estudio_id"]), name)
        tech_by_name[name] = tid
    return tech_by_name[name]


def method_for(e):
    name = e["metodo_nombre"]
    if name not in method_by_name:
        mid = ids.next("experimental_method", "method_id", "MET", 3)
        insert("experimental_method", (mid, name, e["metodo_tipo"] or None,
                                       e["metodo_grupo"] or None),
               "%s %s" % (TAG, e["estudio_id"]),
               "%s | %s | %s" % (name, e["metodo_tipo"], e["metodo_grupo"]))
        method_by_name[name] = mid
    return method_by_name[name]


# --------------------------------------------------------------- 5. moleculas
class Catalog:
    """Moleculas de una cepa indexadas por locus, BioCyc, nombre y sinonimo."""

    def __init__(self, strain):
        self.ncbi, self.biocyc, self.name, self.srna, self.syn = {}, {}, {}, {}, {}
        for rid, name, ncbi, biocyc, is_srna, biotype in con.execute(
                "SELECT rna_id, rna_name, ncbi_id, biocyc_id, is_srna, biotype FROM rna "
                "WHERE strain_id = ? ORDER BY rna_id", (strain,)):
            self.add(rid, name, ncbi, biocyc, bool(is_srna) or biotype == "sRNA")
        for rid, syn in con.execute(
                "SELECT s.rna_id, s.synonym FROM rna_synonym s JOIN rna r USING(rna_id) "
                "WHERE r.strain_id = ? ORDER BY s.rna_id, s.synonym", (strain,)):
            self.syn.setdefault(match_key(syn), rid)

    def add(self, rid, name, ncbi, biocyc, is_srna):
        if ncbi:
            self.ncbi.setdefault(ncbi.lower(), rid)
        if biocyc:
            self.biocyc.setdefault(biocyc.lower(), rid)
        if name:
            self.name.setdefault(match_key(name), rid)
            if is_srna:
                self.srna.setdefault(match_key(name), rid)

    def find(self, ent, name, srna_role):
        ncbi, biocyc = ent["ncbi_id"].strip().lower(), ent["biocyc_id"].strip().lower()
        syns = [s for s in ent["sinonimos"].split("|") if s.strip()]
        for k in [ncbi, biocyc, (name or "").lower()] + [s.lower() for s in syns]:
            if k and (k in self.ncbi or k in self.biocyc):
                return self.ncbi.get(k) or self.biocyc[k]
        names = [match_key(n) for n in [name] + syns if match_key(n)]
        for table in ((self.srna, self.name, self.syn) if srna_role else
                      (self.name, self.srna, self.syn)):
            for k in names:
                if k in table:
                    return table[k]
        return None


catalogs = {}
rna_names = dict(con.execute("SELECT rna_id, COALESCE(rna_name, ncbi_id, rna_id) FROM rna"))
existing_rna = set(rna_names)
new_rna, new_syn, new_loci = [], [], []
role_flags = defaultdict(set)
resolved = {}                                  # (entidad_id, strain) -> rna_id
entity_rnas = defaultdict(set)                 # entidad_id -> {rna_id}


def same_organism(ent, strain):
    sp = species_of_strain[strain]
    taxid = ent["organismo_taxid"].strip()
    return ent["organismo_especie"].strip() == species_name.get(sp) or \
        (taxid.isdigit() and int(taxid) in (sp, strain_taxid.get(strain)))


def resolve(ent_id, gid, role, est, create=True):
    """rna_id de la entidad en la cepa del genoma; la crea si no existe."""
    strain = strain_of_genome[gid]
    key = (ent_id, strain)
    if key in resolved:
        rid = resolved[key]
    else:
        ent = entidades[ent_id]
        if not same_organism(ent, strain):
            if create:
                log_agg("%s %s" % (TAG, est), "organismo_especie",
                        "molecula_de_otro_organismo", ent["organismo_especie"],
                        "fila descartada")
            return None
        cat = catalogs.get(strain) or catalogs.setdefault(strain, Catalog(strain))
        name = ent["nombre_canonico"].split("@")[0].strip() or None
        utr = UTR.match(name or "")
        if utr:
            name = utr.group(1)
            stats["entidades_utr_al_gen"] += 1
        srna_role = role == "srna" or ent["biotipo"] == "sRNA"
        rid = cat.find(ent, name, srna_role)
        if rid is None and not create:
            return None
        if rid is None:
            rid = new_molecule(ent, name, gid, strain, srna_role, utr is not None)
            cat.add(rid, name, ent["ncbi_id"].strip() or None, ent["biocyc_id"].strip() or None,
                    srna_role)
        resolved[key] = rid
        entity_rnas[ent_id].add(rid)
    if role:
        role_flags[rid].add(role)
    return rid


def new_molecule(ent, name, gid, strain, srna_role, utr=False):
    """Molecula nueva a partir de la entidad. Una UTR crea el mRNA de su gen, sin la
    secuencia ni las coordenadas de la UTR."""
    rid = ids.next("rna", "rna_id", "RNA", 6)
    bt = "mRNA" if utr else BIOTYPE.get(ent["biotipo"]) or ("sRNA" if srna_role else None)
    biocyc = ent["biocyc_id"].strip()
    row = dict(rna_id=rid, strain_id=strain, rna_name=name, rna_name_key=name_key(name),
               ncbi_id=ent["ncbi_id"].strip() or None,
               biocyc_id=None if utr and UTR.match(biocyc) else biocyc or None,
               biotype=bt, product=ent["producto"].strip() or None,
               is_antisense=1 if bt == "antisense" else None,
               annotation_source="%s %s" % (TAG, ent["entidad_id"]), seq_id=None)
    # secuencia y locus solo si la entidad esta anotada sobre este mismo genoma
    acc = accs_of(ent["ensamblado_accession"])
    same_genome = not utr and len(acc) == 1 and unversioned(acc[0]) in genome_accs[gid]
    s = seq(ent["secuencia_referencia"])
    if s and same_genome:
        row["seq_id"] = seq_id(s, ent["entidad_id"])
    elif s:
        stats["secuencia_de_otro_ensamblado"] += 1
    if same_genome and ent["coord_inicio"].strip() and ent["coord_fin"].strip():
        a, b = int(ent["coord_inicio"]), int(ent["coord_fin"])
        lo, hi = min(a, b), max(a, b)
        new_loci.append((ids.next("rna_locus", "locus_id", "LOC", 6), rid, gid, lo, hi,
                         ent["hebra"] if ent["hebra"] in ("+", "-") else None, hi - lo + 1,
                         1 if a > b else 0, None, None, ent["criterio_referencia"] or None,
                         row["seq_id"]))
    new_rna.append(row)
    rna_names[rid] = name or row["ncbi_id"] or rid
    seen = {name_key(name)}
    for syn in [s.strip() for s in ent["sinonimos"].split("|")] + \
            ([ent["nombre_canonico"]] if "@" in ent["nombre_canonico"] or utr else []):
        if syn and name_key(syn) not in seen:
            seen.add(name_key(syn))
            new_syn.append((rid, syn, ent["entidad_id"]))
    return rid


# ------------------------------------------------------ 6. interacciones
inter_ids = {(g, s, t): i for i, g, s, t in con.execute(
    "SELECT interaction_id, genome_id, srna_rna_id, target_rna_id FROM interaction")}
pubs_of_inter = defaultdict(set)
for iid, pid in con.execute("SELECT e.interaction_id, s.publication_id FROM study s "
                            "JOIN interaction_evidence e USING(evidence_id)"):
    pubs_of_inter[iid].add(pid)
preexisting_inter = set(inter_ids.values())
inter_new, ev_rows, bind_rows, study_rows, stats_rows, duplex_rows = [], [], [], [], [], []
ev_of_row = {}                                 # interaccion_id -> evidence_id
per_est = defaultdict(Counter)
ev_range = defaultdict(list)
gp_count = Counter()                           # (genome_id, publication_id) -> evidencias
DUPLEX_INT = ("largo_ventana_srna", "largo_ventana_blanco", None, "n_pares",
              "srna_nucleo_inicio", "srna_nucleo_fin", "blanco_nucleo_inicio",
              "blanco_nucleo_fin")
P_KIND = [("bonferroni", "bonferroni"), ("benjamini", "fdr_bh"),
          ("fdr guarda el p de la fuente", "sin_especificar"), ("p de fisher", "fisher"),
          ("p del test exacto de fisher", "fisher"), ("fdr", "fdr")]


def p_kind(e):
    c = e["comentarios"].lower()
    return next((k for pat, k in P_KIND if pat in c), "sin_especificar")


def duplex_row(eid, d, est):
    f = lambda col: num(d[col], est, "duplex." + col)                 # noqa: E731
    i = lambda col: num(d[col], est, "duplex." + col, "int")          # noqa: E731
    core = (i("largo_nucleo_srna"), i("largo_nucleo_blanco"))
    calc = (i("srna_nucleo_fin") - i("srna_nucleo_inicio") + 1
            if d["srna_nucleo_fin"] and d["srna_nucleo_inicio"] else None,
            i("blanco_nucleo_fin") - i("blanco_nucleo_inicio") + 1
            if d["blanco_nucleo_fin"] and d["blanco_nucleo_inicio"] else None)
    if core != calc:
        log_agg("%s %s" % (TAG, est), "duplex.largo_nucleo_*", "largo_no_coincide_con_extremos",
                "", "se guardan los extremos; el largo se deriva de ellos")
    return (eid, d["interaccion_id"], i("largo_ventana_srna"), i("largo_ventana_blanco"),
            f("dg"), i("n_pares"), i("srna_nucleo_inicio"), i("srna_nucleo_fin"),
            i("blanco_nucleo_inicio"), i("blanco_nucleo_fin"), f("srna_nucleo_pos_rel"),
            f("blanco_nucleo_pos_rel"), d["srna_nucleo_secuencia"] or None,
            d["blanco_nucleo_secuencia"] or None, d["estructura"] or None, i("n_helices"),
            i("helice_largo"), i("helice_srna_inicio"), i("helice_srna_fin"),
            i("helice_blanco_inicio"), i("helice_blanco_fin"), f("helice_srna_pos_rel"),
            f("helice_blanco_pos_rel"), d["helice_srna_secuencia"] or None,
            d["helice_blanco_secuencia"] or None, f("helice_gc"), f("dg_nulo_barajado"),
            f("dg_nulo_dinucleotido"), f("helice_nulo_barajado"), f("helice_nulo_dinucleotido"))


for r in filas:
    est = r["estudio_id"]
    if est not in cargar:
        continue
    x = cargar[est]
    e = x["e"]
    src = "%s %s" % (TAG, est)
    pc = per_est[est]
    pc["filas"] += 1
    if not r["entidad_srna_id"] or not r["entidad_blanco_id"]:
        log_agg(src, "entidad_*_id", "fila_sin_molecula", "", "fila descartada")
        pc["descartadas"] += 1
        continue
    gid = genome_for(e)
    s_id = resolve(r["entidad_srna_id"], gid, "srna", est)
    t_id = resolve(r["entidad_blanco_id"], gid, "target", est)
    if s_id is None or t_id is None:
        pc["descartadas"] += 1
        continue
    key = (gid, s_id, t_id)
    if key not in inter_ids:
        iid = ids.next("interaction", "interaction_id", "INT", 6)
        inter_ids[key] = iid
        inter_new.append((iid, gid, s_id, t_id, 1 if s_id == t_id else 0))
        pc["pares_nuevos"] += 1
    iid = inter_ids[key]
    if iid in preexisting_inter:
        pc["pares_existentes"] += 1
        if pubs_of_inter[iid]:
            pc["pares_con_publicacion_previa"] += 1
    eid = ids.next("interaction_evidence", "evidence_id", "EVI", 6)
    ev_of_row[r["interaccion_id"]] = eid
    ev_range[est].append(eid)
    region = r["region_blanco"].strip()
    if region and region not in REGION:
        log_agg(src, "region_blanco", "region_no_es_de_mrna", region,
                "region_involved_mrna = NULL")
    pairing = r["pairing_id_original"].strip()
    ev_rows.append((eid, iid, technique_for(e), REGION.get(region),
                    int(pairing) if re.fullmatch(r"-?\d+", pairing) else None, None, None,
                    num(r["delta_g"], est, "delta_g"), 1, 1, "curado", None))
    pid = pub_ids[x["pub"]["doi_fuente"]]
    gp_count[(gid, pid)] += 1
    reg = e["tipo_regulacion"].strip()
    study_rows.append((ids.next("study", "study_id", "STU", 6), eid, pid, method_for(e),
                       REG.get(reg), e["rbp"].strip() or None, e["condicion"].strip() or None,
                       "%s %s %s%s" % (TAG, est, r["interaccion_id"],
                                       "; pairing %s" % pairing
                                       if pairing and not re.fullmatch(r"-?\d+", pairing)
                                       else "")))
    for role, pre, rid in (("sRNA", "srna", s_id), ("mRNA", "blanco", t_id)):
        a = num(r[pre + "_binding_inicio"], est, pre + "_binding_inicio", "int")
        b = num(r[pre + "_binding_fin"], est, pre + "_binding_fin", "int")
        sq = seq(r[pre + "_binding_secuencia"])
        if r[pre + "_binding_secuencia"].strip() and sq is None:
            log_agg(src, pre + "_binding_secuencia", "secuencia_invalida", "", "-> NULL")
        if a is None and b is None and sq is None:
            continue
        lo, hi = (min(a, b), max(a, b)) if a is not None and b is not None else (a, b)
        strand = r[pre + "_binding_hebra"].strip()
        bind_rows.append((ids.next("binding_site", "binding_site_id", "BND", 6), eid, role, rid,
                          lo, hi, strand if strand in ("+", "-") else None,
                          FRAME.get(e["coord_binding_sistema"]) if lo is not None else None,
                          1 if a is not None and b is not None and a > b else 0,
                          hi - lo + 1 if lo is not None and hi is not None else None,
                          seq_id(sq, est)))
    nlib = r["n_librerias"].strip()
    if nlib in ("U", "u"):
        log_agg(src, "n_librerias", "valor_no_numerico", nlib, "-> NULL")
        nlib = ""
    enr = num(r["enriquecimiento_log2"], est, "enriquecimiento_log2", "log2")
    odds = num(r["odds_ratio"], est, "odds_ratio")
    pval = num(r["fdr"], est, "fdr")
    score, kind = (enr, "log2_fold_change") if r["enriquecimiento_log2"].strip() else \
        (odds, "connection_score" if "connection score" in e["comentarios"].lower()
         else "odds_ratio")
    reads = num(r["reads_hibridos"], est, "reads_hibridos", "int")
    conf = r["confianza_nivel"].strip() or None
    stats_rows.append((eid, r["interaccion_id"], reads, pval, p_kind(e) if pval is not None
                       else None, score, kind if score is not None else None,
                       num(nlib, est, "n_librerias", "int"), r["orden_quimera"].strip() or None,
                       BOOL.get(r["srna_binding_verificado"].strip()),
                       BOOL.get(r["blanco_binding_verificado"].strip()), conf,
                       num(r["confianza_n_mediciones"], est, "confianza_n_mediciones", "int"),
                       num(r["confianza_reads_percentil"], est, "confianza_reads_percentil")))
    if r["interaccion_id"] in duplex:
        duplex_rows.append(duplex_row(eid, duplex[r["interaccion_id"]], est))
    pc["cargadas"] += 1

# -------------------------- 7. duplex de evidencias que ya estaban en la base
# la fila de la fuente se reconoce por las dos ventanas de binding y el pairing_id
by_window = defaultdict(set)
sites = defaultdict(dict)
for eid, role, lo, hi, pid in con.execute(
        "SELECT b.evidence_id, b.molecule_role, b.start_coord, b.end_coord, e.source_pairing_id "
        "FROM binding_site b JOIN interaction_evidence e USING(evidence_id) "
        "WHERE b.start_coord IS NOT NULL AND b.end_coord IS NOT NULL"):
    sites[eid][role] = (lo, hi)
    sites[eid]["pid"] = pid
for eid, d in sites.items():
    if "sRNA" in d and "mRNA" in d:
        by_window[(d["sRNA"], d["mRNA"], d["pid"])].add(eid)
filas_by_id = {r["interaccion_id"]: r for r in filas}
dup_old, dup_stats = {}, Counter()
for d in SOURCES["duplex.csv"]:
    r = filas_by_id[d["interaccion_id"]]
    if r["estudio_id"] in cargar:
        continue
    try:
        k = tuple(tuple(sorted((int(r[p + "_binding_inicio"]), int(r[p + "_binding_fin"]))))
                  for p in ("srna", "blanco"))
    except ValueError:
        dup_stats["sin_ventanas"] += 1
        continue
    pairing = r["pairing_id_original"].strip()
    m = by_window.get(k + (int(pairing) if re.fullmatch(r"-?\d+", pairing) else None,), set())
    if len(m) != 1:
        dup_stats["sin_evidencia" if not m else "ambigua"] += 1
        continue
    eid = next(iter(m))
    if eid in dup_old:
        prev = dup_old[eid]
        same = (prev["dg"], prev["estructura"]) == (d["dg"], d["estructura"])
        dup_stats["repetida_igual" if same else "repetida_distinta"] += 1
        if not same:
            log_agg(TAG + " duplex.csv", "dg/estructura", "duplex_distintos_para_una_evidencia",
                    "", "se conserva el primero")
        continue
    dup_old[eid] = d
    dup_stats["asociada"] += 1
for eid in sorted(dup_old):
    duplex_rows.append(duplex_row(eid, dup_old[eid], filas_by_id[dup_old[eid]["interaccion_id"]]
                                  ["estudio_id"]))
for k_, v in dup_stats.items():
    if k_ in ("sin_ventanas", "sin_evidencia", "ambigua"):
        log(TAG + " duplex.csv", "interaccion_id", "duplex_sin_evidencia_asociada",
            "%s: %d filas" % (k_, v), "no se carga")

# ------------------------------- 8. clase Hfq y moleculas de las regiones consenso
# se resuelve cada entidad en todos los genomas en que aparece, sin crear moleculas
genome_of_est = {}
for e in estudios:
    if e["estudio_id"] in cargar:
        genome_of_est[e["estudio_id"]] = genome_for(e)
    elif e["ensamblado_accession"].strip():
        genome_of_est[e["estudio_id"]] = genome_for(e, create=False)
need = {r["entidad_id"] for r in regiones} | \
    {k for k, v in entidades.items() if v["clase_hfq"].strip()}
for r in filas:
    gid = genome_of_est.get(r["estudio_id"])
    if gid is None:
        continue
    for col, role in (("entidad_srna_id", "srna"), ("entidad_blanco_id", "target")):
        if r[col] in need:
            resolve(r[col], gid, None, r["estudio_id"], create=False)

new_ids = {x["rna_id"] for x in new_rna}
hfq_set = []
for ent_id in sorted(k for k, v in entidades.items() if v["clase_hfq"].strip()):
    ent = entidades[ent_id]
    for rid in sorted(entity_rnas.get(ent_id, ())):
        if rid in new_ids:
            row = next(x for x in new_rna if x["rna_id"] == rid)
            if row.get("hfq_class") is None:
                row.update(hfq_class=ent["clase_hfq"], hfq_class_evidence=ent["clase_hfq_evidencia"])
                hfq_set.append((rid, ent_id, "nueva"))
            continue
        old = con.execute("SELECT hfq_class FROM rna WHERE rna_id = ?", (rid,)).fetchone()[0]
        if old is None:
            con.execute("UPDATE rna SET hfq_class = ?, hfq_class_evidence = ? WHERE rna_id = ?",
                        (ent["clase_hfq"], ent["clase_hfq_evidencia"], rid))
            updates.append(("rna", rid, "hfq_class", None, ent["clase_hfq"], ent_id))
            hfq_set.append((rid, ent_id, "existente"))

# -------------------------------------------------------- 9. regiones consenso
species_by_name = {v: k for k, v in species_name.items()}
seed_rows = []
for r in regiones:
    ent = entidades[r["entidad_id"]]
    sp = species_by_name.get(r["organismo"])
    rids = sorted(entity_rnas.get(r["entidad_id"], ()))
    rid = rids[0] if len(rids) == 1 else None
    src = "%s regiones_consenso %s" % (TAG, r["entidad_id"])
    if len(rids) > 1:
        log(src, "entidad_id", "region_de_varias_moleculas",
            "%s: %s" % (r["sRNA"], ", ".join(rids)), "rna_id = NULL; se usa especie y nombre")
    elif not rids:
        log(src, "entidad_id", "region_sin_molecula", r["sRNA"], "rna_id = NULL")
    f = lambda col: num(r[col], "regiones_consenso", col)              # noqa: E731
    i = lambda col: num(r[col], "regiones_consenso", col, "int")       # noqa: E731
    sid = ids.next("srna_seed_region", "seed_region_id", "SSR", 4)
    row = (sid, sp, r["sRNA"].split("@")[0], rid, r["entidad_id"], i("n_socios"),
           i("n_estudios"), i("largo_srna"), f("pico_fraccion"), i("pico_posicion"),
           f("nulo_fraccion"), f("razon"), f("p"), f("q"), i("region_inicio"), i("region_fin"),
           i("region_largo"), f("region_cubre"))
    seed_rows.append(row)

# ----------------------------------------------------------- 10. escritura
for row in new_rna:
    row.setdefault("hfq_class", None)
    row.setdefault("hfq_class_evidence", None)
    row.update(is_srna=1 if "srna" in role_flags[row["rna_id"]] else 0,
               is_target=1 if "target" in role_flags[row["rna_id"]] else 0)
con.executemany(
    "INSERT INTO rna (rna_id, strain_id, rna_name, rna_name_key, ncbi_id, biocyc_id, biotype, "
    "product, is_srna, is_target, is_antisense, annotation_source, seq_id, hfq_class, "
    "hfq_class_evidence) VALUES (:rna_id, :strain_id, :rna_name, :rna_name_key, :ncbi_id, "
    ":biocyc_id, :biotype, :product, :is_srna, :is_target, :is_antisense, :annotation_source, "
    ":seq_id, :hfq_class, :hfq_class_evidence)", new_rna)
for x in new_rna:
    change_rows.append(("rna", x["rna_id"], "INSERT", "", "",
                        "%s | %s | ncbi_id=%s | %s | is_srna=%d is_target=%d" % (
                            x["strain_id"], x["rna_name"] or "", x["ncbi_id"] or "",
                            x["biotype"] or "", x["is_srna"], x["is_target"]),
                        x["annotation_source"]))
con.executemany("INSERT INTO rna_sequence VALUES (?,?,1,1)",
                [(x["rna_id"], x["seq_id"]) for x in new_rna if x["seq_id"]])
for rid, roles in sorted(role_flags.items()):         # moleculas existentes con un rol nuevo
    if rid in new_ids:
        continue
    for role, col in (("srna", "is_srna"), ("target", "is_target")):
        old = con.execute("SELECT %s FROM rna WHERE rna_id = ?" % col, (rid,)).fetchone()[0]
        if role in roles and old != 1:
            con.execute("UPDATE rna SET %s = 1 WHERE rna_id = ?" % col, (rid,))
            updates.append(("rna", rid, col, old, 1, "rol observado en los estudios nuevos"))
con.executemany("INSERT INTO rna_synonym VALUES (?,?)", [(r_, s) for r_, s, _ in new_syn])
for r_, s, ent in new_syn:
    change_rows.append(("rna_synonym", r_, "INSERT", "synonym", "", s, ent))
con.executemany("INSERT INTO rna_locus VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", new_loci)
con.executemany("INSERT INTO interaction VALUES (?,?,?,?,?)", inter_new)
con.executemany("INSERT INTO interaction_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ev_rows)
con.executemany("INSERT INTO binding_site VALUES (?,?,?,?,?,?,?,?,?,?,?)", bind_rows)
con.executemany("INSERT INTO study VALUES (?,?,?,?,?,?,?,?)", study_rows)
con.executemany("INSERT INTO evidence_stats VALUES (%s)" % ",".join("?" * 14), stats_rows)
con.executemany("INSERT INTO duplex_prediction VALUES (%s)" % ",".join("?" * 30), duplex_rows)
for row in seed_rows:
    insert("srna_seed_region", row, "regiones_consenso.csv %s" % row[4],
           "%s | species %s | rna_id=%s | region %s-%s | q=%s" % (
               row[2], row[1], row[3] or "", row[14], row[15], row[13]))
gpb_new = []
for (gid, pid), n in sorted(gp_count.items()):
    gpb = ids.next("genome_publication", "genome_publication_id", "GPB", 5)
    insert("genome_publication", (gpb, gid, pid, n, "derivada_de_studies", "publicada"),
           "studies", "%s | %s | n_evidences=%d" % (gid, pid, n))
    gpb_new.append((gpb, gid, pid, n))
for tbl, rid, fld, old, new, src in updates:
    change_rows.append((tbl, rid, "UPDATE", fld, "" if old is None else old, new, src))
for (src, col, kind, val, action), n in sorted(QC_AGG.items()):
    qc.append((src, col, kind, val, action, n))
qc_ids = []
for q in qc:
    cur = con.execute("INSERT INTO qc_issue (source_line, column_name, issue_type, "
                      "original_value, action, n_casos) VALUES (?,?,?,?,?,?)", q)
    qc_ids.append(cur.lastrowid)
    change_rows.append(("qc_issue", cur.lastrowid, "INSERT", "", "",
                        "%s: %s (n=%d)" % (q[2], q[3], q[5]), q[0]))

bad = con.execute("PRAGMA foreign_key_check").fetchall()
if bad:
    con.rollback()
    sys.exit("foreign_key_check fallo, no se guardo nada: %s" % bad[:5])
count_after = OrderedDict((t, con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
                          for t in TABLES)

with open(LOG_CSV, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["tabla", "id", "operacion", "campo", "valor_anterior", "valor_nuevo", "origen"])
    w.writerows(change_rows)

# ------------------------------------------------------ 11. bitacora legible
NUMERIC = {"n", "Filas", "Cargadas", "Descartadas", "Pares nuevos", "Pares previos",
           "Con publicación previa", "Antes", "Insertadas", "Modificadas", "Después",
           "Filas leídas", "issue_id", "n_casos", "Evidencias"}


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---:" if h in NUMERIC else "---" for h in header) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c).replace("|", "/") for c in r) + " |"
            for r in rows]
    return "\n".join(out)


def rng(lst):
    return "%s … %s" % (lst[0], lst[-1]) if lst else "—"


pub_by_id = {pid: next(x["pub"] for x in cargar.values() if x["pub"]["doi_fuente"] == d)
             for d, pid in pub_ids.items()}
upd_by_table = Counter(u[0] for u in updates)
ins_by_table = Counter({t: count_after[t] - count_before[t] for t in TABLES})
L = ["# Bitácora de cambios: CSV nuevos\n",
     "Registro de las modificaciones que `scripts/load_csvs_nuevos.py` aplica sobre "
     "`db/bactericidas.sqlite` al incorporar los estudios nuevos de "
     "`db/fuentes/csvs_nuevos/`. El archivo se regenera en cada carga. El detalle de los "
     "registros de catálogo (publicaciones, taxonomía, genomas, técnicas, métodos, ARN, "
     "sinónimos, regiones consenso y `qc_issue`) está en `db/cambios_csvs_nuevos.csv`, con "
     "%d líneas. Las evidencias y sus tablas hijas se resumen por estudio; cada una remite a "
     "su fila de origen por `evidence_stats.source_ref` y por `study.comments`.\n"
     % len(change_rows)]

L.append("## Archivos de origen\n")
L.append("El SHA-1 permite verificar que la fuente no cambió entre una carga y otra.\n")
L.append(md_table(["Archivo", "Filas leídas", "Contenido", "SHA-1"], [
    (fn, n, {"estudios.csv": "un estudio = publicación, método, condición y ensamblado",
             "entidades_rna.csv": "moléculas por especie, con secuencia y coordenadas",
             "interacciones.csv": "una evidencia de un par en un estudio",
             "duplex.csv": "dúplex predicho para cada interacción con ventanas de binding",
             "regiones_consenso.csv": "región del sRNA que concentra el apareamiento"}[fn],
     "`%s`" % sha1(fn)[:12]) for fn, n in READ_ROWS.items()]) + "\n")
L.append("Complementos, generados por `scripts/completar_csvs_nuevos.py` y corregibles a mano: "
         "`complementos/publicaciones.csv` (%d) y `complementos/genomas.csv` (%d).\n"
         % (len(comp_pub), len(comp_gen)))

L.append("## Qué se cargó\n")
L.append("De los %d estudios de la fuente, %d son la base migrada (`migracion_v1`) y no se "
         "leen. De los %d restantes se cargan %d; los demás se detallan más abajo.\n"
         % (len(estudios), stats["estudios_migracion_v1"],
            len(estudios) - stats["estudios_migracion_v1"], len(cargar)))
rows = []
for est, x in cargar.items():
    e, pc = x["e"], per_est[est]
    pid = pub_ids[x["pub"]["doi_fuente"]]
    rows.append((est, "%s %s" % (x["pub"]["first_author"], x["pub"]["year"]), pid,
                 "%s%s" % (e["metodo_nombre"], " / " + e["rbp"] if e["rbp"] else ""),
                 genome_cache[";".join(accs_of(e["ensamblado_accession"]))],
                 e["condicion"][:70], pc["filas"], pc["cargadas"], pc["descartadas"],
                 pc["pares_nuevos"], pc["pares_existentes"], pc["pares_con_publicacion_previa"],
                 rng(ev_range[est])))
L.append(md_table(["Estudio", "Trabajo", "publication_id", "Método", "Genoma", "Condición",
                   "Filas", "Cargadas", "Descartadas", "Pares nuevos", "Pares previos",
                   "Con publicación previa", "evidence_id"], rows) + "\n")
L.append("*Pares previos* son evidencias que se suman a un par sRNA → blanco que ya existía "
         "(de este mismo lote o de antes); *con publicación previa*, las que caen sobre un par "
         "que ya tenía respaldo bibliográfico antes de esta carga.\n")
L.append("Qué guarda `evidence_stats` en cada estudio, según su descripción en la fuente:\n")
kinds = defaultdict(set)
est_of_ev = {eid: est for est, lst in ev_range.items() for eid in lst}
for s in stats_rows:
    if s[6]:
        kinds[est_of_ev[s[0]]].add(s[6])
L.append(md_table(["Estudio", "p_value_kind", "score_kind"], [
    (est, p_kind(x["e"]), ", ".join(sorted(kinds[est])) or "—")
    for est, x in cargar.items()]) + "\n")

L.append("### Estudios no cargados\n")
L.append(md_table(["Estudio", "Trabajo", "Método", "Filas", "Motivo"], [
    (e["estudio_id"], "%s %s" % (p["first_author"], p["year"]) if p else
     e["publication_first_author"], e["metodo_nombre"], rows_by_est[e["estudio_id"]], why)
    for e, p, why in no_cargados]) + "\n")
L.append("Las reingestas de Melamed 2016 y 2020 y de Gebhardt 2023 traen además lecturas y "
         "p-valores por quimera que la base no tiene para esas evidencias; quedan sin cargar "
         "porque no hay una correspondencia fila a fila con las evidencias existentes.\n")

L.append("## Publicaciones\n")
L.append("Los datos salen de PubMed; la fuente traía errores que se corrigieron en el "
         "complemento y constan en `qc_issue`:\n")
L.append(md_table(["publication_id", "PMID", "DOI", "Primer autor", "Año", "Revista", "Nota"], [
    (pid, p["pmid"], p["doi"], p["first_author"], p["year"], p["journal"], p["nota"])
    for pid, p in pub_by_id.items()]) + "\n")

L.append("## Taxonomía, cepas y genomas\n")
new_gen_rows = [r for r in change_rows if r[0] in ("phylum", "genus", "species", "strain",
                                                   "genome")]
L.append(md_table(["Tabla", "ID", "Valor"], [(r[0], r[1], r[5]) for r in new_gen_rows]) + "\n")
L.append("Los estudios cuyo ensamblado ya estaba en la base usan ese genoma. Cuando una "
         "accesión aparece en varios genomas (NC_000913.3: MG1655, MC4100, GS162) se usa el "
         "primero cargado, y los replicones que el estudio nombra pero el genoma no tiene "
         "(plásmidos, el fago lambda) quedan anotados en `qc_issue`.\n")

L.append("## Resumen por tabla\n")
L.append(md_table(["Tabla", "Antes", "Insertadas", "Modificadas", "Después"], [
    (t, count_before[t], ins_by_table[t] or "", upd_by_table.get(t, "") or "", count_after[t])
    for t in TABLES if ins_by_table[t] or upd_by_table.get(t)]) + "\n")
L.append("Rangos de identificadores asignados:\n")
for label, lst in (("rna", [x["rna_id"] for x in new_rna]),
                   ("interaction", [i[0] for i in inter_new]),
                   ("interaction_evidence", [e[0] for e in ev_rows]),
                   ("binding_site", [b[0] for b in bind_rows]),
                   ("study", [s[0] for s in study_rows]),
                   ("rna_locus", [x[0] for x in new_loci]),
                   ("srna_seed_region", [x[0] for x in seed_rows]),
                   ("qc_issue", ["%d" % q for q in qc_ids])):
    L.append("- `%s`: %s (%d)" % (label, rng(lst), len(lst)))
L.append("")

L.append("## Moléculas\n")
matched = {rid for (ent, strain), rid in resolved.items() if rid in existing_rna}
L.append("Cada entidad de la fuente es una molécula por especie; la base guarda una por cepa. "
         "Se busca en la cepa del estudio por locus (`ncbi_id`), BioCyc, sinónimos con forma "
         "de locus, nombre y sinónimos, con la misma comparación de nombres que "
         "`load_gebhardt2023.py`. Se reutilizaron %d moléculas existentes y se crearon %d. "
         "Una molécula nueva toma secuencia y locus de la entidad solo si la entidad está "
         "anotada sobre el mismo ensamblado del estudio; %d secuencias de otro ensamblado "
         "no se usaron.\n" % (len(matched), len(new_rna), stats["secuencia_de_otro_ensamblado"]))
bt = Counter((x["biotype"] or "—") for x in new_rna)
L.append(md_table(["biotype", "n"], bt.most_common()) + "\n")
L.append("Se agregaron %d sinónimos, %d locus y %d secuencias nuevas.\n"
         % (len(new_syn), len(new_loci), stats["secuencias_nuevas"]))

L.append("## Registros existentes modificados\n")
L.append("La carga modifica %d registros que ya estaban en la base. En ningún caso se "
         "sobrescribe un valor que no fuera nulo o cero.\n" % len(updates))
L.append(md_table(["Campo", "n"], Counter("rna." + u[2] for u in updates).most_common()) + "\n")
L.append("El detalle de cada uno está en el CSV de cambios (operación `UPDATE`).\n")

L.append("## Klebsiella pneumoniae SGH10\n")
gen_sgh = genome_cache.get("NZ_CP025080.1;NZ_CP025081.1")
if gen_sgh:
    sin_cita = {i for (i,) in con.execute(
        "SELECT i.interaction_id FROM interaction i WHERE i.genome_id = ? AND NOT EXISTS "
        "(SELECT 1 FROM interaction_evidence e JOIN study s USING(evidence_id) "
        "WHERE e.interaction_id = i.interaction_id AND s.publication_id IS NOT NULL "
        "AND s.publication_id NOT IN (%s))" % ",".join("?" * len(pub_ids)),
        (gen_sgh,) + tuple(pub_ids.values()))} & preexisting_inter
    goh = {e_[1] for e_ in ev_rows if e_[1] in sin_cita}
    L.append("El genoma `%s` figuraba en `genome_publication` como `pendiente_de_curacion`: "
             "%d de sus pares no tenían ninguna publicación. Goh et al. 2024 (RIL-seq en "
             "SGH10) aporta evidencia a %d de esos pares (%.0f %%). La fila pendiente se "
             "conserva; si se confirma que el lote sin cita es este trabajo, se puede "
             "reemplazar por la publicación.\n"
             % (gen_sgh, len(sin_cita), len(goh), 100.0 * len(goh) / max(len(sin_cita), 1)))

L.append("## Dúplex predichos\n")
L.append("`duplex_prediction` guarda la predicción de la fuente, que no es un dato "
         "experimental. Se cargaron %d: %d de evidencias de esta carga y %d de evidencias que "
         "ya estaban, reconocidas por sus dos ventanas de binding y su `pairing_id`.\n"
         % (len(duplex_rows), len(duplex_rows) - len(dup_old), len(dup_old)))
L.append(md_table(["Filas de duplex.csv fuera de esta carga", "n"],
                  sorted(dup_stats.items())) + "\n")

L.append("## Regiones consenso y clase Hfq\n")
L.append("Se cargaron %d regiones en `srna_seed_region` (%d con q < 0,05). %d quedaron con "
         "`rna_id` porque la entidad corresponde a una sola molécula; las demás se consultan "
         "por especie y nombre del sRNA.\n" % (
             len(seed_rows), sum(1 for x in seed_rows if x[13] is not None and x[13] < 0.05),
             sum(1 for x in seed_rows if x[3])))
L.append("`rna.hfq_class` se completó en %d moléculas (%d nuevas y %d existentes), a partir de "
         "%d entidades clasificadas.\n" % (
             len(hfq_set), sum(1 for x in hfq_set if x[2] == "nueva"),
             sum(1 for x in hfq_set if x[2] == "existente"),
             sum(1 for v in entidades.values() if v["clase_hfq"].strip())))

L.append("## Registros en qc_issue\n")
by_kind = Counter()
for q in qc:
    by_kind[q[2]] += q[5]
L.append(md_table(["Tipo", "n_casos"], by_kind.most_common()) + "\n")
L.append(md_table(["issue_id", "Origen", "Columna", "Tipo", "Valor", "Acción", "n_casos"], [
    (qid, q[0], q[1], q[2], q[3], q[4], q[5]) for qid, q in zip(qc_ids, qc)]) + "\n")
with open(LOG_MD, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
con.commit()

# reexporta todas las tablas para que db/csv siga en sincronia con la base
for t in TABLES:
    cur = con.execute("SELECT * FROM %s" % t)
    cols = [d[0] for d in cur.description]
    with open(os.path.join(CSVDIR, t + ".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows([["" if v is None else v for v in row] for row in cur])
con.close()

print("CSV nuevos cargados en %s" % os.path.relpath(DB, BASE))
print("  %-34s %6d" % ("estudios cargados", len(cargar)))
for t in TABLES:
    if ins_by_table[t] or upd_by_table.get(t):
        print("  %-34s %6d%s" % (t, ins_by_table[t], " (+%d modificados)" % upd_by_table[t]
                                 if upd_by_table.get(t) else ""))
print("Bitacora: %s, %s" % (os.path.relpath(LOG_MD, BASE), os.path.relpath(LOG_CSV, BASE)))
