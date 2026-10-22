-- =====================================================================
-- Proyecto Bactericidas - esquema relacional normalizado
-- Generado a partir de "Full_data_set_en uso.csv" por scripts/build_db.py
--
-- Identificadores nuevos:
--   rna.rna_id      'RNA-000001'      -> una molecula de ARN (la sustancia) por cepa
--   sequence.seq_id 'SEQ-<sha1x12>'   -> una secuencia nucleotidica unica
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_publicaciones_por_genoma;
DROP VIEW  IF EXISTS v_interaccion_completa;
DROP TABLE IF EXISTS qc_issue;
DROP TABLE IF EXISTS srna_seed_region;
DROP TABLE IF EXISTS duplex_prediction;
DROP TABLE IF EXISTS evidence_stats;
DROP TABLE IF EXISTS study;
DROP TABLE IF EXISTS binding_site;
DROP TABLE IF EXISTS interaction_evidence;
DROP TABLE IF EXISTS interaction;
DROP TABLE IF EXISTS genome_publication;
DROP TABLE IF EXISTS publication;
DROP TABLE IF EXISTS regulation_type;
DROP TABLE IF EXISTS experimental_method;
DROP TABLE IF EXISTS technique;
DROP TABLE IF EXISTS rna_locus;
DROP TABLE IF EXISTS rna_synonym;
DROP TABLE IF EXISTS rna_sequence;
DROP TABLE IF EXISTS rna;
DROP TABLE IF EXISTS sequence;
DROP TABLE IF EXISTS replicon;
DROP TABLE IF EXISTS genome;
DROP TABLE IF EXISTS strain;
DROP TABLE IF EXISTS species;
DROP TABLE IF EXISTS genus;
DROP TABLE IF EXISTS phylum;

-- ------------------------------------------------------------ taxonomia
CREATE TABLE phylum (
  phylum_taxid INTEGER PRIMARY KEY,
  phylum_name  TEXT NOT NULL UNIQUE
);

CREATE TABLE genus (
  genus_taxid  INTEGER PRIMARY KEY,
  genus_name   TEXT NOT NULL UNIQUE,
  phylum_taxid INTEGER NOT NULL REFERENCES phylum(phylum_taxid)
);

CREATE TABLE species (
  species_taxid INTEGER PRIMARY KEY,
  species_name  TEXT NOT NULL UNIQUE,
  genus_taxid   INTEGER NOT NULL REFERENCES genus(genus_taxid)
);

CREATE TABLE strain (
  strain_id     TEXT PRIMARY KEY,
  strain_name   TEXT NOT NULL UNIQUE,
  strain_taxid  INTEGER,
  species_taxid INTEGER REFERENCES species(species_taxid),
  gram_type     TEXT CHECK (gram_type IN ('Gram-negative','Gram-positive'))
);

-- ------------------------------------------------------------ genomas
-- accession_raw conserva el valor original (podia traer varios accesos
-- separados por ';' dentro de una sola celda); cada acceso queda ademas
-- desglosado en replicon.
CREATE TABLE genome (
  genome_id     TEXT PRIMARY KEY,
  strain_id     TEXT NOT NULL REFERENCES strain(strain_id),
  accession_raw TEXT,
  n_replicons   INTEGER NOT NULL DEFAULT 0,
  has_multiple_assemblies INTEGER NOT NULL DEFAULT 0,
  data_batch    TEXT CHECK (data_batch IN ('curado','genoma_nuevo')),
  UNIQUE (strain_id, accession_raw)
);

CREATE TABLE replicon (
  replicon_id    TEXT PRIMARY KEY,
  genome_id      TEXT NOT NULL REFERENCES genome(genome_id),
  accession      TEXT NOT NULL,
  replicon_order INTEGER NOT NULL,
  replicon_role  TEXT,
  UNIQUE (genome_id, accession)
);

-- --------------------------------------------- secuencias (id por secuencia)
-- Secuencias identicas comparten seq_id, sin importar en que fila o en que
-- columna del CSV original aparecieran.
CREATE TABLE sequence (
  seq_id        TEXT PRIMARY KEY,
  seq_length    INTEGER NOT NULL,
  gc_content    REAL,
  molecule_type TEXT,
  sequence      TEXT NOT NULL UNIQUE
);

-- ------------------------------------------------- ARN (id por molecula)
-- Una fila por molecula de ARN por cepa: sRNA y ARN blanco viven en la misma
-- tabla porque 130 sRNAs aparecen tambien como blanco de otros sRNAs.
-- Identidad: (strain_id, ncbi_id); si falta, (strain_id, rna_name_key); si falta,
-- (strain_id, biocyc_id); y como ultimo recurso (strain_id, seq_id).
CREATE TABLE rna (
  rna_id        TEXT PRIMARY KEY,
  strain_id     TEXT NOT NULL REFERENCES strain(strain_id),
  rna_name      TEXT,
  rna_name_key  TEXT,                  -- nombre normalizado: une RyhB / ryhB / ryhB-1
  ncbi_id       TEXT,
  biocyc_id     TEXT,
  biotype       TEXT,
  product       TEXT,
  protein_id    TEXT,
  is_srna       INTEGER NOT NULL DEFAULT 0,
  is_target     INTEGER NOT NULL DEFAULT 0,
  is_antisense  INTEGER,
  is_plasmid_derived INTEGER,
  plasmid_ncbi_id    TEXT,
  is_est_utr    INTEGER,
  annotation_source  TEXT,
  seq_id        TEXT REFERENCES sequence(seq_id),  -- secuencia canonica
  hfq_class     TEXT,                  -- 'Clase I' / 'Clase II' (sRNA de union a Hfq)
  hfq_class_evidence TEXT              -- cita o criterio de la clasificacion
);

-- Una molecula puede tener mas de una secuencia registrada (distintas
-- versiones de ensamblado): todas quedan aca, la canonica marcada con 1.
CREATE TABLE rna_sequence (
  rna_id       TEXT NOT NULL REFERENCES rna(rna_id),
  seq_id       TEXT NOT NULL REFERENCES sequence(seq_id),
  is_canonical INTEGER NOT NULL DEFAULT 0,
  n_records    INTEGER,
  PRIMARY KEY (rna_id, seq_id)
);

CREATE TABLE rna_synonym (
  rna_id  TEXT NOT NULL REFERENCES rna(rna_id),
  synonym TEXT NOT NULL,
  PRIMARY KEY (rna_id, synonym)
);

CREATE TABLE rna_locus (
  locus_id    TEXT PRIMARY KEY,
  rna_id      TEXT NOT NULL REFERENCES rna(rna_id),
  genome_id   TEXT REFERENCES genome(genome_id),
  start_coord INTEGER,
  end_coord   INTEGER,
  strand      TEXT CHECK (strand IN ('+','-')),
  span_length INTEGER,
  coords_were_flipped INTEGER NOT NULL DEFAULT 0,  -- venia start > end
  left_gene   TEXT,
  right_gene  TEXT,
  annotation_source TEXT,
  seq_id      TEXT REFERENCES sequence(seq_id)
);

-- ------------------------------------------------------------ metodologia
CREATE TABLE technique (
  technique_id   TEXT PRIMARY KEY,
  technique_name TEXT NOT NULL UNIQUE,   -- 'RIL-seq with Hfq'
  base_method    TEXT,                   -- 'RIL-seq'
  rbp            TEXT                    -- 'Hfq'
);

CREATE TABLE experimental_method (
  method_id    TEXT PRIMARY KEY,
  method_name  TEXT NOT NULL UNIQUE,
  method_type  TEXT,
  method_group TEXT
);

CREATE TABLE regulation_type (
  regulation_type_id   TEXT PRIMARY KEY,
  regulation_type_name TEXT NOT NULL UNIQUE
);

-- ---------------------------------------------------------- publicaciones
CREATE TABLE publication (
  publication_id TEXT PRIMARY KEY,
  pmid           INTEGER UNIQUE,
  doi            TEXT,
  title          TEXT,
  journal        TEXT,
  year           INTEGER,
  first_author   TEXT,
  corresponding_author_mail TEXT
);

-- Publicaciones asociadas a cada genoma. Los genomas incorporados sin cita
-- bibliografica quedan con publication_id NULL y status
-- 'pendiente_de_curacion', para poder cargarles la referencia despues.
CREATE TABLE genome_publication (
  genome_publication_id TEXT PRIMARY KEY,
  genome_id      TEXT NOT NULL REFERENCES genome(genome_id),
  publication_id TEXT REFERENCES publication(publication_id),
  n_evidences    INTEGER NOT NULL DEFAULT 0,
  link_source    TEXT,
  status         TEXT CHECK (status IN ('publicada','pendiente_de_curacion')),
  UNIQUE (genome_id, publication_id)
);

-- ---------------------------------------------------------- interacciones
-- interaction  = el par biologico (sRNA -> blanco) en un genoma: unico.
-- interaction_evidence = cada registro experimental que lo respalda
--                        (una fila del CSV original).
CREATE TABLE interaction (
  interaction_id TEXT PRIMARY KEY,
  genome_id      TEXT NOT NULL REFERENCES genome(genome_id),
  srna_rna_id    TEXT NOT NULL REFERENCES rna(rna_id),
  target_rna_id  TEXT NOT NULL REFERENCES rna(rna_id),
  is_self_interaction INTEGER NOT NULL DEFAULT 0,
  UNIQUE (genome_id, srna_rna_id, target_rna_id)
);

CREATE TABLE interaction_evidence (
  evidence_id          TEXT PRIMARY KEY,
  interaction_id       TEXT NOT NULL REFERENCES interaction(interaction_id),
  technique_id         TEXT REFERENCES technique(technique_id),
  region_involved_mrna TEXT,
  source_pairing_id    INTEGER,   -- pairing_id que traia el JSON original
  pairing_energy       REAL,
  mre_binding_area     TEXT,
  delta_g              REAL,
  n_publications       INTEGER NOT NULL DEFAULT 0,  -- recalculado desde studies
  n_exp_methods        INTEGER NOT NULL DEFAULT 0,  -- recalculado desde studies
  data_batch           TEXT CHECK (data_batch IN ('curado','genoma_nuevo')),
  source_line          INTEGER    -- linea del CSV original, para trazabilidad
);

CREATE TABLE binding_site (
  binding_site_id TEXT PRIMARY KEY,
  evidence_id     TEXT NOT NULL REFERENCES interaction_evidence(evidence_id),
  molecule_role   TEXT NOT NULL CHECK (molecule_role IN ('sRNA','mRNA')),
  rna_id          TEXT REFERENCES rna(rna_id),
  start_coord     INTEGER,
  end_coord       INTEGER,
  strand          TEXT CHECK (strand IN ('+','-')),
  coord_frame     TEXT CHECK (coord_frame IN ('genomico','relativo')),
  coords_were_flipped INTEGER NOT NULL DEFAULT 0,
  span_length     INTEGER,
  seq_id          TEXT REFERENCES sequence(seq_id)
);

CREATE TABLE study (
  study_id       TEXT PRIMARY KEY,
  evidence_id    TEXT NOT NULL REFERENCES interaction_evidence(evidence_id),
  publication_id TEXT REFERENCES publication(publication_id),
  method_id      TEXT REFERENCES experimental_method(method_id),
  regulation_type_id TEXT REFERENCES regulation_type(regulation_type_id),
  rbp            TEXT,
  microbe_condition TEXT,
  comments       TEXT
);

-- Estadisticos que la fuente informa para cada evidencia de alto rendimiento
-- (quimeras de RIL-seq/CLASH, enriquecimiento de MAPS). Una fila por evidencia,
-- solo para las que los traen. p_value_kind y score_kind dicen que es cada
-- valor, porque cada trabajo informa un estadistico distinto.
CREATE TABLE evidence_stats (
  evidence_id    TEXT PRIMARY KEY REFERENCES interaction_evidence(evidence_id),
  source_ref     TEXT,       -- registro de la fuente ('S1_exp #13', 'INT043074')
  hybrid_reads   INTEGER,    -- lecturas o fragmentos quimericos
  p_value        REAL,
  p_value_kind   TEXT CHECK (p_value_kind IN ('fisher','bonferroni','fdr','fdr_bh',
                                              'sin_especificar')),
  score          REAL,
  score_kind     TEXT CHECK (score_kind IN ('odds_ratio','connection_score',
                                            'log2_fold_change')),
  n_libraries    INTEGER,    -- replicas o librerias en que aparece el par
  chimera_order  TEXT,       -- de que lado de la quimera esta el sRNA
  srna_binding_verified   INTEGER,   -- la ventana se verifico contra el genoma
  target_binding_verified INTEGER,
  confidence_level TEXT CHECK (confidence_level IN ('alto','medio','bajo')),
  confidence_n_measurements   INTEGER,
  confidence_reads_percentile REAL
);

-- Prediccion computacional del duplex sRNA-blanco a partir de las ventanas de
-- binding: no es un dato experimental. Las posiciones son relativas a la
-- ventana (base 1); *_rel_pos es la posicion normalizada (0-1). Los *_null_*
-- son la media de modelos nulos con secuencias barajadas (mononucleotido y
-- dinucleotido preservado).
CREATE TABLE duplex_prediction (
  evidence_id          TEXT PRIMARY KEY REFERENCES interaction_evidence(evidence_id),
  source_ref           TEXT,
  srna_window_length   INTEGER,
  target_window_length INTEGER,
  delta_g              REAL,
  n_base_pairs         INTEGER,
  srna_core_start      INTEGER,
  srna_core_end        INTEGER,
  target_core_start    INTEGER,
  target_core_end      INTEGER,
  srna_core_rel_pos    REAL,
  target_core_rel_pos  REAL,
  srna_core_sequence   TEXT,
  target_core_sequence TEXT,
  structure            TEXT,       -- notacion de puntos y parentesis, '&' separa los ARN
  n_helices            INTEGER,
  helix_length         INTEGER,    -- helice mas larga
  helix_srna_start     INTEGER,
  helix_srna_end       INTEGER,
  helix_target_start   INTEGER,
  helix_target_end     INTEGER,
  helix_srna_rel_pos   REAL,
  helix_target_rel_pos REAL,
  helix_srna_sequence  TEXT,
  helix_target_sequence TEXT,
  helix_gc             REAL,
  delta_g_null_shuffled     REAL,
  delta_g_null_dinucleotide REAL,
  helix_null_shuffled       REAL,
  helix_null_dinucleotide   REAL
);

-- Region del sRNA que concentra el apareamiento con sus blancos (posible
-- semilla), calculada sobre todos los blancos del sRNA en la especie. rna_id
-- queda nulo cuando el sRNA corresponde a mas de una molecula (varias cepas).
CREATE TABLE srna_seed_region (
  seed_region_id TEXT PRIMARY KEY,
  species_taxid  INTEGER REFERENCES species(species_taxid),
  srna_name      TEXT NOT NULL,
  rna_id         TEXT REFERENCES rna(rna_id),
  source_ref     TEXT,
  n_partners     INTEGER,
  n_studies      INTEGER,
  srna_length    INTEGER,
  peak_fraction  REAL,      -- fraccion de blancos que cubre la posicion pico
  peak_position  INTEGER,
  null_fraction  REAL,      -- la misma fraccion esperada al azar
  enrichment_ratio REAL,    -- peak_fraction / null_fraction
  p_value        REAL,
  q_value        REAL,
  region_start   INTEGER,
  region_end     INTEGER,
  region_length  INTEGER,
  region_coverage REAL      -- fraccion de blancos cuyo apareamiento cae en la region
);

-- ------------------------------------------------------- control de calidad
CREATE TABLE qc_issue (
  issue_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  n_casos        INTEGER NOT NULL DEFAULT 1,
  source_line    TEXT,
  column_name    TEXT,
  issue_type     TEXT,
  original_value TEXT,
  action         TEXT
);

-- ------------------------------------------------------------------ indices
CREATE INDEX idx_rna_strain   ON rna(strain_id);
CREATE INDEX idx_rna_namekey  ON rna(strain_id, rna_name_key);
CREATE INDEX idx_rna_ncbi     ON rna(strain_id, ncbi_id);
CREATE INDEX idx_rna_seq      ON rna(seq_id);
CREATE INDEX idx_locus_rna    ON rna_locus(rna_id);
CREATE INDEX idx_inter_srna   ON interaction(srna_rna_id);
CREATE INDEX idx_inter_target ON interaction(target_rna_id);
CREATE INDEX idx_evi_inter    ON interaction_evidence(interaction_id);
CREATE INDEX idx_bind_evi     ON binding_site(evidence_id);
CREATE INDEX idx_study_evi    ON study(evidence_id);
CREATE INDEX idx_study_pub    ON study(publication_id);
CREATE INDEX idx_gpub_genome  ON genome_publication(genome_id);
CREATE INDEX idx_seed_rna     ON srna_seed_region(rna_id);

-- ------------------------------------------------------------------- vistas
CREATE VIEW v_interaccion_completa AS
SELECT i.interaction_id,
       st.strain_name,
       g.accession_raw AS genoma,
       s.rna_id   AS srna_id,   s.rna_name AS srna_name,   s.seq_id AS srna_seq_id,
       t.rna_id   AS blanco_id, t.rna_name AS blanco_name, t.biotype AS blanco_biotype,
       t.seq_id   AS blanco_seq_id,
       e.evidence_id, tec.technique_name, e.delta_g, e.data_batch
FROM interaction i
JOIN rna    s   ON s.rna_id    = i.srna_rna_id
JOIN rna    t   ON t.rna_id    = i.target_rna_id
JOIN genome g   ON g.genome_id = i.genome_id
JOIN strain st  ON st.strain_id = g.strain_id
LEFT JOIN interaction_evidence e ON e.interaction_id = i.interaction_id
LEFT JOIN technique tec          ON tec.technique_id = e.technique_id;

CREATE VIEW v_publicaciones_por_genoma AS
SELECT g.genome_id, s.strain_name, g.accession_raw, gp.status,
       p.publication_id, p.pmid, p.year, p.first_author, p.title, gp.n_evidences
FROM genome g
JOIN strain s ON s.strain_id = g.strain_id
LEFT JOIN genome_publication gp ON gp.genome_id = g.genome_id
LEFT JOIN publication p         ON p.publication_id = gp.publication_id;
