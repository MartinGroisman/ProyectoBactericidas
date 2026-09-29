# -*- coding: utf-8 -*-
"""
Busca publicaciones con interacciones sRNA-mRNA que no estan en la base
(paso 2 de docs/hoja_de_ruta_nuevas_interacciones.md).

  python scripts/exportar_exclusion.py     # lista de exclusion al dia
  python scripts/buscar_candidatos.py      # agrega candidatos nuevos

Fuentes
  2a. PubMed (E-utilities): consulta general, por metodo y por organismo
      prioritario. Europe PMC (REST): las consultas por metodo en texto
      completo y la general restringida a preprints (bioRxiv y otros).
  2c. Rastreo de citas: trabajos que citan a las publicaciones de alto
      rendimiento que ya estan en la base (elink pubmed_pubmed_citedin), con
      al menos un termino de sRNA en titulo o resumen.
  2b (bases de interacciones: RNAInter, NPInter, RegulonDB...) es manual: las
  filas se agregan a mano a candidatos.csv con fuente_busqueda
  "manual:<base>" y el script las conserva.

Todo se une en db/candidatos/candidatos.csv (clave: PMID, si no DOI, si no el
id de Europe PMC). Se descarta lo que ya esta en db/exclusion/publicaciones.csv
por PMID o DOI. Es incremental: las filas existentes conservan las columnas de
cribado (decision, motivo_exclusion, notas) y fecha_alta; solo se agregan
filas nuevas y se actualiza fuente_busqueda. Un candidato de una corrida
anterior que despues se cargo a la base queda con en_base = si. Cada corrida se registra en
db/candidatos/busquedas.csv con la cantidad de resultados por consulta.

metodos_detectados, organismos_detectados y prioridad_sugerida salen de
expresiones regulares sobre titulo y resumen: ayudan a ordenar el cribado,
no lo reemplazan.

Variables de entorno opcionales: NCBI_API_KEY (sube el limite de 3 a 10
consultas por segundo) y NCBI_EMAIL (recomendado por NCBI).
"""
from __future__ import annotations
import csv, datetime, http.client, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCL = os.path.join(BASE, "db", "exclusion", "publicaciones.csv")
OUT = os.path.join(BASE, "db", "candidatos")
CAND = os.path.join(OUT, "candidatos.csv")
LOG = os.path.join(OUT, "busquedas.csv")

DESDE = 2022                                   # ver hoja de ruta, seccion 0
HOY = datetime.date.today()
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
NCBI_EXTRA = {"tool": "ProyectoBactericidas"}
if os.environ.get("NCBI_EMAIL"):
    NCBI_EXTRA["email"] = os.environ["NCBI_EMAIL"]
if os.environ.get("NCBI_API_KEY"):
    NCBI_EXTRA["api_key"] = os.environ["NCBI_API_KEY"]
NCBI_PAUSA = 0.12 if "api_key" in NCBI_EXTRA else 0.4

# ------------------------------------------------------------------ consultas
SRNA = ('("small RNA"[tiab] OR sRNA*[tiab] OR "regulatory RNA"[tiab] '
        'OR "noncoding RNA"[tiab] OR "non-coding RNA"[tiab])')
BACT = '(bacteri*[tiab] OR Bacteria[MeSH])'
BLANCO = ('(target*[tiab] OR "base pairing"[tiab] OR "base-pairing"[tiab] '
          'OR "RNA-RNA interaction*"[tiab] OR interactome[tiab] OR Hfq[tiab] OR ProQ[tiab])')
NO_REV = 'NOT (review[pt] OR "systematic review"[pt])'
METODOS_Q = ('("RIL-seq"[tiab] OR "iRIL-seq"[tiab] OR CLASH[tiab] OR "GRIL-seq"[tiab] '
             'OR "Hi-GRIL-seq"[tiab] OR "LIGR-seq"[tiab] OR "MAPS"[tiab] '
             'OR "MS2 affinity purification"[tiab] OR "RNA interactome"[tiab] '
             'OR "RNA-RNA interactome"[tiab] OR "proximity ligation"[tiab])')
# "MAPS" o "proximity ligation" solos traen cientos de resultados ajenos: se
# exige contexto de sRNA o de chaperona de ARN
CONTEXTO = ('("small RNA"[tiab] OR sRNA*[tiab] OR "regulatory RNA"[tiab] '
            'OR "noncoding RNA"[tiab] OR Hfq[tiab] OR ProQ[tiab])')
ORGANISMOS_Q = ["Acinetobacter baumannii", "Enterococcus faecium", "Enterobacter",
                "Staphylococcus aureus", "Klebsiella pneumoniae", "Pseudomonas aeruginosa",
                "Mycobacterium tuberculosis"]

PUBMED_Q = OrderedDict([
    ("pm_general", "%s AND %s AND %s %s" % (SRNA, BACT, BLANCO, NO_REV)),
    ("pm_metodo", "%s AND %s AND (%s OR CsrA[tiab] OR \"RNase E\"[tiab])"
     % (METODOS_Q, CONTEXTO, BACT)),
])
for org in ORGANISMOS_Q:
    PUBMED_Q["pm_org_" + org.split()[-1].lower()] = (
        '"%s"[tiab] AND %s AND (%s OR regulat*[tiab]) %s' % (org, SRNA, BLANCO, NO_REV))

EPMC_ANIOS = "PUB_YEAR:[%d TO %d]" % (DESDE, HOY.year)
EPMC_Q = OrderedDict([
    # texto completo: metodos que muchas veces solo aparecen en Metodos o figuras
    ("epmc_metodo_texto", '("RIL-seq" OR "iRIL-seq" OR "GRIL-seq" OR "Hi-GRIL-seq" OR "LIGR-seq" '
     'OR "Hfq CLASH" OR "RNase E CLASH" OR "MS2 affinity purification") '
     'AND ("small RNA" OR sRNA) AND (Hfq OR ProQ OR bacteria OR bacterial) AND ' + EPMC_ANIOS),
    ("epmc_preprints", '(ABSTRACT:"small RNA" OR ABSTRACT:sRNA OR ABSTRACT:"regulatory RNA") '
     'AND (ABSTRACT:bacteria OR ABSTRACT:bacterial OR ABSTRACT:Hfq OR ABSTRACT:ProQ) '
     'AND (ABSTRACT:target OR ABSTRACT:targets OR ABSTRACT:"base pairing" OR ABSTRACT:interactome) '
     'AND SRC:PPR AND ' + EPMC_ANIOS),
])

# metodos de alto rendimiento cuyos trabajos se rastrean por citas (2c)
ALTO_RENDIMIENTO = {"CLASH", "RIL-Seq", "GRIL", "rGRIL", "Hi-GRIL", "LIGR", "MAP-Seq"}

# ------------------------------------------------------ preclasificacion
METODOS_RE = [  # (nombre, regex, clase)
    ("RIL-seq", r"\bi?RIL-?seq\b", "alto_directo"),
    ("CLASH", r"\bCLASH\b", "alto_directo"),
    ("GRIL-seq", r"\b(?:Hi-|r)?GRIL-?seq\b", "alto_directo"),
    ("LIGR-seq", r"\bLIGR-?seq\b", "alto_directo"),
    ("MAPS", r"\bMAPS\b|MS2[- ]affinity purification", "alto_indirecto"),
    ("RNA-seq", r"\bRNA-?seq\b|transcriptom", "alto_indirecto"),
    ("EMSA", r"\bEMSA\b|gel[- ](?:mobility[- ])?shift|electrophoretic mobility", "bajo_directo"),
    ("mutaciones compensatorias", r"compensatory mutation", "bajo_directo"),
    ("footprinting/probing", r"footprint|structure probing|toeprint|in-line probing", "bajo_directo"),
    ("fusion reportera", r"(?:translational|transcriptional|gfp|lacZ|reporter)[- ]fusion"
                         r"|reporter assay", "bajo_indirecto"),
    ("Northern/Western", r"northern blot|western blot|immunoblot", "bajo_indirecto"),
    ("qRT-PCR", r"qRT-PCR|RT-qPCR|quantitative (?:real-time )?PCR", "bajo_indirecto"),
    ("prediccion", r"IntaRNA|CopraRNA|TargetRNA|sRNATarget|in silico|computational predict",
     "prediccion"),
]
METODOS_RE = [(n, re.compile(r, re.I), c) for n, r, c in METODOS_RE]
# ESKAPE ausentes o casi ausentes de la base (hoja de ruta, seccion 0)
HUECO = {"Acinetobacter baumannii", "Enterococcus faecium", "Enterobacter",
         "Staphylococcus aureus"}
SRNA_RE = re.compile(r"small RNA|\bsRNAs?\b|regulatory RNA|non-?coding RNA|\bHfq\b|\bProQ\b",
                     re.I)
# tipos de publicacion que no son trabajos primarios (prioridad 9, como las revisiones)
NO_PRIMARIO = re.compile(r"review|editorial|comment|news|biography|erratum|retraction"
                         r"|interview|introductory journal article", re.I)
# ARN del hospedador: trabajos sobre miRNA o lncRNA que nombran a la bacteria
# como patogeno y entran por "small RNA" o "non-coding RNA" (prioridad 7)
EUCARIOTA = re.compile(r"\bmiR-?\d|\bmiRNAs?\b|microRNA|\blncRNAs?\b|\bcircRNAs?\b|\bpiRNAs?\b",
                       re.I)

CAMPOS = ["clave", "pmid", "doi", "epmc_id", "anio", "primer_autor", "titulo", "revista",
          "tipo_publicacion", "es_preprint", "metodos_detectados", "clase_metodo",
          "organismos_detectados", "organismo_en_base", "prioridad_sugerida",
          "fuente_busqueda", "cita_a", "version_de", "en_base", "fecha_alta", "decision",
          "motivo_exclusion", "notas", "resumen"]
MANUALES = ("decision", "motivo_exclusion", "notas", "fecha_alta")


# ---------------------------------------------------------------- red
def pedir(url, params=None, post=False, intentos=5):
    data = None
    if params is not None:
        enc = urllib.parse.urlencode(params, doseq=True)
        if post:
            data = enc.encode()
        else:
            url += "?" + enc
    espera = 2
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": "ProyectoBactericidas/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == intentos - 1:
                raise
        # URLError, timeouts y conexiones cortadas son OSError; una respuesta
        # truncada a mitad de lectura es IncompleteRead (HTTPException)
        except (OSError, http.client.HTTPException):
            if i == intentos - 1:
                raise
        time.sleep(espera)
        espera *= 2


def eutils(fn, params, post=False):
    time.sleep(NCBI_PAUSA)
    return pedir(EUTILS + fn, dict(params, **NCBI_EXTRA), post=post)


def pubmed_buscar(q):
    p = dict(db="pubmed", term=q, retmode="json", retmax=10000, datetype="pdat",
             mindate="%d/01/01" % DESDE, maxdate="3000")
    r = json.loads(eutils("esearch.fcgi", p))["esearchresult"]
    return r["idlist"], int(r["count"])


def texto(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def pubmed_registros(pmids):
    """efetch en lotes de 200; devuelve {pmid: registro}."""
    out = {}
    pmids = sorted(set(pmids), key=int)
    for i in range(0, len(pmids), 200):
        xml = eutils("efetch.fcgi", dict(db="pubmed", id=",".join(pmids[i:i + 200]),
                                         retmode="xml"), post=True)
        for art in ET.fromstring(xml).iter("PubmedArticle"):
            mc = art.find("MedlineCitation")
            pmid = mc.findtext("PMID")
            a = mc.find("Article")
            anio = a.findtext("Journal/JournalIssue/PubDate/Year") or \
                (a.findtext("Journal/JournalIssue/PubDate/MedlineDate") or "")[:4] or \
                a.findtext("ArticleDate/Year") or ""
            autor = ""
            au = a.find("AuthorList/Author")
            if au is not None:
                autor = au.findtext("CollectiveName") or " ".join(
                    x for x in (au.findtext("ForeName"), au.findtext("LastName")) if x)
            doi = ""
            for aid in art.iterfind("PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = (aid.text or "").strip()
            if not doi:
                for e in a.iterfind("ELocationID"):
                    if e.get("EIdType") == "doi":
                        doi = (e.text or "").strip()
            partes = []
            for ab in a.iterfind("Abstract/AbstractText"):
                t = texto(ab)
                partes.append("%s: %s" % (ab.get("Label"), t) if ab.get("Label") else t)
            tipos = [texto(t) for t in a.iterfind("PublicationTypeList/PublicationType")]
            out[pmid] = dict(pmid=pmid, doi=norm_doi(doi), epmc_id="", anio=anio,
                             primer_autor=autor, titulo=texto(a.find("ArticleTitle")),
                             revista=a.findtext("Journal/Title") or "",
                             tipo_publicacion="|".join(tipos), es_preprint=int(
                                 "Preprint" in tipos), resumen=" ".join(partes))
    return out


def pubmed_citas(pmids):
    """{pmid_citante: {pmid_citado, ...}} via elink pubmed_pubmed_citedin."""
    citas = defaultdict(set)
    pmids = sorted(pmids, key=int)
    for i in range(0, len(pmids), 50):
        r = json.loads(eutils("elink.fcgi", dict(dbfrom="pubmed", db="pubmed",
                                                  linkname="pubmed_pubmed_citedin",
                                                  retmode="json", id=pmids[i:i + 50]),
                              post=True))
        for ls in r.get("linksets", []):
            citado = ls["ids"][0]
            for db in ls.get("linksetdbs", []):
                for c in db.get("links", []):
                    citas[str(c)].add(str(citado))
    return citas


def epmc_buscar(q):
    regs, cursor, total = [], "*", 0
    while True:
        r = json.loads(pedir(EPMC, dict(query=q, format="json", resultType="core",
                                        pageSize=1000, cursorMark=cursor)))
        total = r.get("hitCount", 0)
        for x in r.get("resultList", {}).get("result", []):
            ji = x.get("journalInfo") or {}
            revista = (ji.get("journal") or {}).get("title") or \
                (x.get("bookOrReportDetails") or {}).get("publisher", "")
            tipos = (x.get("pubTypeList") or {}).get("pubType", [])
            autores = (x.get("authorList") or {}).get("author", [])
            autor = ""
            if autores:
                autor = autores[0].get("fullName") or autores[0].get("collectiveName", "")
            regs.append(dict(pmid=x.get("pmid", ""), doi=norm_doi(x.get("doi")),
                             epmc_id="%s:%s" % (x.get("source"), x.get("id")),
                             anio=x.get("pubYear", ""), primer_autor=autor,
                             titulo=re.sub(r"<[^>]+>", "", x.get("title", "")).strip(),
                             revista=revista, tipo_publicacion="|".join(tipos),
                             es_preprint=int(x.get("source") == "PPR"),
                             resumen=re.sub(r"<[^>]+>", " ", x.get("abstractText", "")).strip()))
        nxt = r.get("nextCursorMark")
        if not nxt or nxt == cursor or not r.get("resultList", {}).get("result"):
            break
        cursor = nxt
    return regs, total


# ------------------------------------------------------------ utilidades
def norm_doi(d):                    # identica a exportar_exclusion.norm_doi
    if not d:
        return ""
    d = d.strip().lower()
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d)


def organismo_re(nombre):
    partes = nombre.split()
    if len(partes) == 1:
        return re.compile(r"\b%s\b" % re.escape(nombre))
    g, sp = partes[0], " ".join(partes[1:])
    return re.compile(r"\b(?:%s|%s\.)\s*%s\b" % (re.escape(g), re.escape(g[0]), re.escape(sp)),
                      re.I)


def clasificar(reg, organismos, en_base):
    txt = reg["titulo"] + " " + reg["resumen"]
    mets = [(n, c) for n, r, c in METODOS_RE if r.search(txt)]
    orgs = [o for o, r in organismos if r.search(txt)]
    clases = {c for _, c in mets}
    es_rev = NO_PRIMARIO.search(reg["tipo_publicacion"]) or \
        re.match(r"\s*(a\s+)?review\b", reg["titulo"], re.I)
    if es_rev:
        prio = 9
    elif EUCARIOTA.search(txt) and not SRNA_RE.search(reg["titulo"]):
        prio = 7
    elif "alto_directo" in clases:
        prio = 1
    elif HUECO & set(orgs) and SRNA_RE.search(txt) and clases != {"prediccion"}:
        prio = 2
    elif clases - {"prediccion"}:
        prio = 3
    elif clases == {"prediccion"}:
        prio = 8
    else:
        prio = 4
    reg["metodos_detectados"] = "|".join(n for n, _ in mets)
    reg["clase_metodo"] = "|".join(sorted(clases))
    reg["organismos_detectados"] = "|".join(orgs)
    reg["organismo_en_base"] = "|".join("si" if o in en_base else "no" for o in orgs)
    reg["prioridad_sugerida"] = prio


def clave(reg):
    if reg.get("pmid"):
        return "PMID:" + reg["pmid"]
    if reg.get("doi"):
        return "DOI:" + reg["doi"]
    return reg["epmc_id"]


# ================================================================== corrida
if not os.path.exists(EXCL):
    sys.exit("No existe %s: correr antes scripts/exportar_exclusion.py" % EXCL)
os.makedirs(OUT, exist_ok=True)

with open(EXCL, encoding="utf-8", newline="") as fh:
    base_pubs = list(csv.DictReader(fh))
pmid_base = {r["pmid"] for r in base_pubs if r["pmid"]}
doi_base = {r["doi"] for r in base_pubs if r["doi"]}
especies_base = {e for r in base_pubs for e in r["especies"].split("|") if e}
organismos = [(o, organismo_re(o)) for o in sorted(especies_base | HUECO)]

log, fuentes, regs = [], defaultdict(set), {}
cita_a = defaultdict(set)


def registrar(fuente, qid, q, n, estado):
    log.append([HOY.isoformat(), fuente, qid, n, estado, q])
    print("  %-22s %6s  %s" % (qid, n, estado))


print("PubMed")
pm_ids = set()
for qid, q in PUBMED_Q.items():
    try:
        ids, n = pubmed_buscar(q)
    except Exception as e:                       # noqa: BLE001 - se registra y sigue
        registrar("pubmed", qid, q, "", "error: %s" % e)
        continue
    registrar("pubmed", qid, q, n, "ok")
    for i in ids:
        fuentes["PMID:" + i].add(qid)
    pm_ids.update(ids)

print("Rastreo de citas (elink)")
semillas = [r["pmid"] for r in base_pubs
            if r["pmid"] and ALTO_RENDIMIENTO & set(r["metodos"].split("|"))]
try:
    citas = pubmed_citas(semillas)
    registrar("pubmed_citedin", "citas_alto_rend", "citan a %d trabajos de alto rendimiento "
              "de la base" % len(semillas), len(citas), "ok")
except Exception as e:                           # noqa: BLE001
    citas = {}
    registrar("pubmed_citedin", "citas_alto_rend", "", "", "error: %s" % e)

print("Descarga de registros PubMed")
todos_pm = pm_ids | set(citas)
pm_regs = pubmed_registros(todos_pm)
print("  %d registros" % len(pm_regs))
n_citas = 0
for pmid, cit in citas.items():
    r = pm_regs.get(pmid)
    if not r or not r["anio"].isdigit() or int(r["anio"]) < DESDE:
        continue
    if not SRNA_RE.search(r["titulo"] + " " + r["resumen"]):
        continue
    fuentes["PMID:" + pmid].add("citas_alto_rend")
    cita_a["PMID:" + pmid] |= cit
    n_citas += 1
print("  citas desde %d con terminos de sRNA: %d" % (DESDE, n_citas))
for pmid in pm_ids | {k[5:] for k in cita_a}:
    if pmid in pm_regs:
        regs["PMID:" + pmid] = pm_regs[pmid]

print("Europe PMC")
for qid, q in EPMC_Q.items():
    try:
        lista, n = epmc_buscar(q)
    except Exception as e:                       # noqa: BLE001
        registrar("europepmc", qid, q, "", "error: %s" % e)
        continue
    registrar("europepmc", qid, q, n, "ok")
    for r in lista:
        k = clave(r)
        fuentes[k].add(qid)
        if k in regs:                            # ya venia de PubMed: completar id
            regs[k]["epmc_id"] = regs[k]["epmc_id"] or r["epmc_id"]
        else:
            regs[k] = r

# ------------------------------------------------ exclusion y preclasificacion
descartados = 0
nuevos = {}
for k, r in regs.items():
    if (r["pmid"] and r["pmid"] in pmid_base) or (r["doi"] and r["doi"] in doi_base):
        descartados += 1
        continue
    if r["anio"].isdigit() and int(r["anio"]) < DESDE:
        continue
    clasificar(r, organismos, especies_base)
    r["clave"] = k
    r["fuente_busqueda"] = "|".join(sorted(fuentes[k]))
    r["cita_a"] = "|".join(sorted(cita_a.get(k, ()), key=int))
    r["version_de"] = ""
    nuevos[k] = r

# preprint y version publicada del mismo trabajo: mismo titulo normalizado. Se
# conservan ambas filas; la secundaria apunta a la preferida en version_de
# (articulo de revista antes que preprint; con PMID antes que sin; el mas nuevo).
por_titulo = defaultdict(list)
for k, r in nuevos.items():
    por_titulo[re.sub(r"[^a-z0-9]", "", r["titulo"].lower())].append(k)
for t, ks in por_titulo.items():
    if len(ks) < 2 or len(t) < 30:
        continue
    ks.sort(key=lambda k: (not nuevos[k]["es_preprint"] and "preprint" not in
                           nuevos[k]["revista"].lower() and "biorxiv" not in
                           nuevos[k]["revista"].lower(), bool(nuevos[k]["pmid"]),
                           nuevos[k]["anio"], nuevos[k]["pmid"]), reverse=True)
    for k in ks[1:]:
        nuevos[k]["version_de"] = ks[0]

# ---------------------------------------------------- fusion con lo existente
previos = OrderedDict()
if os.path.exists(CAND):
    with open(CAND, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            previos[r["clave"]] = r
filas, agregados = [], 0
for k in set(previos) | set(nuevos):
    if k in nuevos:
        r = {c: nuevos[k].get(c, "") for c in CAMPOS}
        if k in previos:
            p = previos[k]
            for c in MANUALES:
                r[c] = p.get(c, "")
            r["fuente_busqueda"] = "|".join(sorted(
                set(p["fuente_busqueda"].split("|")) | set(r["fuente_busqueda"].split("|"))
                - {""}))
        else:
            r["fecha_alta"] = HOY.isoformat()
            agregados += 1
    else:                          # fila manual (2b) o que ya no aparece: se conserva
        r = {c: previos[k].get(c, "") for c in CAMPOS}
    # un candidato que ya se cargo sigue en la planilla (conserva su cribado),
    # marcado para que no se vuelva a procesar
    r["en_base"] = "si" if ((r["pmid"] and r["pmid"] in pmid_base)
                            or (r["doi"] and r["doi"] in doi_base)) else ""
    filas.append(r)
filas.sort(key=lambda r: (int(r["prioridad_sugerida"] or 99), -int(r["anio"] or 0),
                          r["clave"]))

with open(CAND, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(filas)
nuevo_log = not os.path.exists(LOG)
with open(LOG, "a", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    if nuevo_log:
        w.writerow(["fecha", "fuente", "consulta_id", "n_resultados", "estado", "consulta"])
    w.writerows(log)

# ----------------------------------------------------------------- resumen
print()
print("Ya en la base (descartados por PMID o DOI): %d" % descartados)
cargados = sum(1 for r in filas if r["en_base"])
if cargados:
    print("Candidatos de corridas anteriores ya cargados (en_base = si): %d" % cargados)
pendientes = [r for r in filas if not r["en_base"]]
print("Candidatos pendientes: %d (%d nuevos en esta corrida) -> %s"
      % (len(pendientes), agregados, os.path.relpath(CAND, BASE)))
# las filas nuevas traen la prioridad como int y las leidas del CSV como str
cuenta = defaultdict(int)
for r in pendientes:
    cuenta[str(r["prioridad_sugerida"])] += 1
etiquetas = {"1": "alto rendimiento directo", "2": "organismo sin cobertura",
             "3": "otro metodo experimental", "4": "sin metodo detectado",
             "7": "probable ARN eucariota", "8": "solo prediccion",
             "9": "revision u otro no primario"}
for p in sorted(cuenta, key=lambda x: int(x or 99)):
    print("  prioridad %s (%s): %d" % (p or "-", etiquetas.get(p, "sin prioridad, fila manual"),
                                       cuenta[p]))
errores = [l for l in log if l[4] != "ok"]
if errores:
    print("Consultas con error (reintentar mas tarde): %s" % ", ".join(l[2] for l in errores))
