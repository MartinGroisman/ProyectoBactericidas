# -*- coding: utf-8 -*-
"""
Completa con PubMed, Crossref y NCBI los datos que db/fuentes/csvs_nuevos/ no
trae y que load_csvs_nuevos.py necesita: titulo, revista y correo de cada
publicacion, y cepa y taxonomia de cada genoma.

  python scripts/completar_csvs_nuevos.py     # requiere red; se corre una vez
  python scripts/load_csvs_nuevos.py          # no usa red

Salidas (versionadas, se pueden corregir a mano antes de cargar):
  db/fuentes/csvs_nuevos/complementos/publicaciones.csv
      una fila por publicacion de los estudios ingestados (no los de
      migracion_v1), clave doi. Si la fuente no trae PMID se busca por DOI en
      PubMed; si PubMed no tiene el trabajo, los datos salen de Crossref.
  db/fuentes/csvs_nuevos/complementos/genomas.csv
      una fila por conjunto de accesiones de esos estudios, con la cepa, su
      taxid y el linaje (especie, genero, filo) del primer replicon segun NCBI.

Es incremental: las filas que ya estan en los archivos se conservan tal cual,
asi que una correccion manual no se pierde al volver a correr el script.

Variables de entorno opcionales: NCBI_API_KEY y NCBI_EMAIL, como en
buscar_candidatos.py.
"""
from __future__ import annotations
import csv, http.client, json, os, re, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "db", "fuentes", "csvs_nuevos")
OUT = os.path.join(SRC, "complementos")
PUBS = os.path.join(OUT, "publicaciones.csv")
GENS = os.path.join(OUT, "genomas.csv")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works/"
NCBI_EXTRA = {"tool": "ProyectoBactericidas"}
if os.environ.get("NCBI_EMAIL"):
    NCBI_EXTRA["email"] = os.environ["NCBI_EMAIL"]
if os.environ.get("NCBI_API_KEY"):
    NCBI_EXTRA["api_key"] = os.environ["NCBI_API_KEY"]
NCBI_PAUSA = 0.12 if "api_key" in NCBI_EXTRA else 0.4

PUB_CAMPOS = ["doi_fuente", "pmid", "doi", "title", "journal", "year", "first_author",
              "corresponding_author_mail", "fuente_metadatos", "nota"]
# DOI de estudios.csv que apuntan a otro trabajo: el PMID correcto sale de la cita
# de la serie de GEO que el propio estudio nombra en sus comentarios
CORRECCIONES = {
    "10.1038/s41467-022-34073-3": dict(pmid="35732654", nota="el DOI de la fuente es de "
                                       "otro trabajo; PMID segun GEO GSE166151"),
    "10.1128/spectrum.00552-24": dict(pmid="38534138", nota="el DOI de la fuente no existe; "
                                      "PMID segun GEO GSE254532"),
    "10.1128/jb.00145-25": dict(pmid="41042061", nota="el DOI de la fuente es de otro "
                                "trabajo; PMID segun GEO GSE296222"),
    # PubMed consigna 2021 en PubDate; la publicacion electronica es de 2022
    "10.1128/mbio.03576-21": dict(year="2022", nota="anio de la publicacion electronica "
                                  "(PubMed registra 2021)"),
}
GEN_CAMPOS = ["accesiones", "strain_name", "strain_taxid", "species_taxid", "species_name",
              "genus_taxid", "genus_name", "phylum_taxid", "phylum_name", "gram_type",
              "fuente_metadatos", "nota"]
# Wu et al. 2024 midio en la cepa hipervirulenta VK055 pero anoto contra el genoma
# de KPPR1 (ATCC 43816), segun el comentario de su estudio
CEPA_EXPERIMENTAL = {"NZ_CP009208.1": "Klebsiella pneumoniae VK055"}
# Gram por filo; los estudios ingestados son todos de estos dos filos
GRAM = {"Pseudomonadota": "Gram-negative", "Bacillota": "Gram-positive"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


# ---------------------------------------------------------------- red
def pedir(url, params=None, intentos=5):     # como buscar_candidatos.pedir
    if params is not None:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    espera = 2
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ProyectoBactericidas/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504) or i == intentos - 1:
                raise
        except (OSError, http.client.HTTPException):
            if i == intentos - 1:
                raise
        time.sleep(espera)
        espera *= 2


def eutils(fn, params):
    time.sleep(NCBI_PAUSA)
    return pedir(EUTILS + fn, dict(params, **NCBI_EXTRA))


def texto(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


# -------------------------------------------------------- publicaciones
def pmid_por_doi(doi):
    r = json.loads(eutils("esearch.fcgi", dict(db="pubmed", term="%s[doi]" % doi,
                                               retmode="json")))["esearchresult"]
    return r["idlist"][0] if r["idlist"] else None


def pubmed(pmid):
    art = ET.fromstring(eutils("efetch.fcgi", dict(db="pubmed", id=pmid, retmode="xml"))
                        ).find("PubmedArticle")
    a = art.find("MedlineCitation/Article")
    anio = a.findtext("Journal/JournalIssue/PubDate/Year") or \
        (a.findtext("Journal/JournalIssue/PubDate/MedlineDate") or "")[:4] or \
        a.findtext("ArticleDate/Year") or ""
    autores = a.findall("AuthorList/Author")
    primero = autores[0] if autores else None
    nombre = " ".join(x for x in (primero.findtext("ForeName"), primero.findtext("LastName"))
                      if x) if primero is not None else ""
    correos = []
    for au in autores:
        for af in au.iterfind("AffiliationInfo/Affiliation"):
            for m in EMAIL.findall(af.text or ""):
                m = m.rstrip(".")
                if m.lower() not in [c.lower() for c in correos]:
                    correos.append(m)
    doi = next((x.text.strip() for x in art.iterfind("PubmedData/ArticleIdList/ArticleId")
                if x.get("IdType") == "doi" and x.text), "")
    return dict(pmid=pmid, doi=doi, title=texto(a.find("ArticleTitle")).rstrip("."),
                journal=a.findtext("Journal/Title") or "", year=anio, first_author=nombre,
                corresponding_author_mail="; ".join(correos), fuente_metadatos="pubmed")


def crossref(doi):
    raw = pedir(CROSSREF + urllib.parse.quote(doi))
    if raw is None:
        return None
    m = json.loads(raw)["message"]
    au = (m.get("author") or [{}])[0]
    fecha = (m.get("published") or m.get("issued") or {}).get("date-parts", [[""]])[0]
    return dict(pmid="", doi=doi, title=re.sub(r"\s+", " ", (m.get("title") or [""])[0]).strip(),
                journal=(m.get("container-title") or [""])[0],
                year=str(fecha[0]) if fecha and fecha[0] else "",
                first_author=" ".join(x for x in (au.get("given"), au.get("family")) if x),
                corresponding_author_mail="", fuente_metadatos="crossref")


# ------------------------------------------------------------- genomas
def nuccore(acc):
    """(organismo, taxid, cepa) del replicon segun esummary de nuccore."""
    r = json.loads(eutils("esummary.fcgi", dict(db="nuccore", id=acc, retmode="json")))
    res = r["result"]
    doc = res[res["uids"][0]]
    sub = dict(zip(doc["subtype"].split("|"), doc["subname"].split("|")))
    return doc["organism"], int(doc["taxid"]), sub.get("strain", "")


def linaje(taxid):
    """{rango: (taxid, nombre)} del linaje de un taxid, incluido el propio."""
    tx = ET.fromstring(eutils("efetch.fcgi", dict(db="taxonomy", id=taxid))).find("Taxon")
    out = {tx.findtext("Rank"): (int(tx.findtext("TaxId")), tx.findtext("ScientificName"))}
    for t in tx.iterfind("LineageEx/Taxon"):
        out.setdefault(t.findtext("Rank"), (int(t.findtext("TaxId")), t.findtext("ScientificName")))
    return out


# ---------------------------------------------------------------- main
def leer(fn, delim=","):
    if not os.path.exists(fn):
        return []
    with open(fn, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delim))


def escribir(fn, campos, filas):
    with open(fn, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def accesiones(raw):                            # 'NC_1; NC_2' -> 'NC_1;NC_2'
    return ";".join(a.strip() for a in raw.split(";") if a.strip())


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(SRC, "interacciones.csv"), encoding="utf-8", newline="") as fh:
        con_filas = {r["estudio_id"] for r in csv.DictReader(fh, delimiter=";")}
    estudios = [e for e in leer(os.path.join(SRC, "estudios.csv"), ";")
                if e["fuente_ingesta"] != "migracion_v1" and e["estudio_id"] in con_filas]

    pubs = {r["doi_fuente"].lower(): r for r in leer(PUBS)}
    for e in estudios:
        doi = e["publication_doi"].strip()
        if not doi or doi.lower() in pubs:
            continue
        fix = CORRECCIONES.get(doi, {})
        pmid = fix.get("pmid") or e["publication_pmid"].strip() or pmid_por_doi(doi)
        reg = pubmed(pmid) if pmid else crossref(doi)
        if reg is None:
            reg = dict(pmid="", doi=doi, title="", journal=e["publication_journal"],
                       year=e["publication_year"], first_author=e["publication_first_author"],
                       corresponding_author_mail="", fuente_metadatos="estudios.csv")
        notas = [fix["nota"]] if fix.get("nota") else []
        if fix.get("year"):
            reg["year"] = fix["year"]
        if reg["first_author"] != e["publication_first_author"]:
            notas.append("primer autor en estudios.csv: %s" % e["publication_first_author"])
        reg.update(doi_fuente=doi, nota="; ".join(notas))
        pubs[doi.lower()] = reg
        print("  %-34s PMID %-9s %s %s (%s)" % (doi, reg["pmid"] or "-", reg["first_author"],
                                               reg["year"], reg["fuente_metadatos"]))
    escribir(PUBS, PUB_CAMPOS, sorted(pubs.values(), key=lambda r: r["doi_fuente"].lower()))

    gens = {r["accesiones"]: r for r in leer(GENS)}
    for e in estudios:
        accs = accesiones(e["ensamblado_accession"])
        if not accs or accs in gens:
            continue
        org, taxid, cepa = nuccore(accs.split(";")[0])
        lin = linaje(taxid)
        sp, ge, ph = lin["species"], lin["genus"], lin["phylum"]
        nombre = org if not cepa or any(c.strip() in org for c in cepa.split(";")) \
            else "%s %s" % (org, cepa)
        nota = ""
        if accs in CEPA_EXPERIMENTAL:
            nombre, nota = CEPA_EXPERIMENTAL[accs], "cepa del experimento; el ensamblado es " \
                "de %s %s" % (org, cepa)
            taxid = sp[0]
        gens[accs] = dict(accesiones=accs, strain_name=nombre,
                          strain_taxid=taxid if taxid != sp[0] else "",
                          species_taxid=sp[0], species_name=sp[1], genus_taxid=ge[0],
                          genus_name=ge[1], phylum_taxid=ph[0], phylum_name=ph[1],
                          gram_type=GRAM.get(ph[1], ""), fuente_metadatos="ncbi", nota=nota)
        print("  %-40s %s (%s)" % (accs[:40], nombre, gens[accs]["strain_taxid"] or "-"))
    escribir(GENS, GEN_CAMPOS, sorted(gens.values(), key=lambda r: r["accesiones"]))
    print("Complementos: %s, %s" % (os.path.relpath(PUBS, BASE), os.path.relpath(GENS, BASE)))


if __name__ == "__main__":
    main()
