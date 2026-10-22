# CSV nuevos: compendio externo de interacciones

Exportación de un compendio de interacciones sRNA–ARN armado fuera de este
repositorio, en un esquema propio (en castellano y menos normalizado). Se
recibió el 21-10-2026. **Origen y autoría: pendiente de documentar.**

| Archivo | Filas | Contenido |
|---|---:|---|
| `estudios.csv` | 485 | Un estudio = publicación + método + proteína + condición + ensamblado |
| `entidades_rna.csv` | 29.907 | Una molécula por especie, con sinónimos, biotipo, IDs, coordenadas y secuencia de referencia |
| `interacciones.csv` | 128.599 | Una evidencia de un par sRNA–blanco en un estudio, con sus ventanas de binding y estadísticos |
| `duplex.csv` | 72.847 | Dúplex predicho (ΔG, estructura, hélice principal, modelos nulos) para cada interacción con ventanas |
| `regiones_consenso.csv` | 84 | Región del sRNA que concentra el apareamiento con sus blancos |

`fuente_ingesta` separa la base de este repositorio migrada al otro esquema
(`migracion_v1`) de las ingestas posteriores (`ingesta_2026-09-08` a
`ingesta_2026-10-05`), que son las que carga `scripts/load_csvs_nuevos.py`.

Los archivos se conservan tal como llegaron (`;` como separador, CRLF, UTF-8 sin
BOM); `.gitattributes` evita que Git les cambie los finales de línea, para que
el SHA-1 de la bitácora siga valiendo.

## Complementos

`complementos/` tiene lo que la fuente no trae y la carga necesita. Lo genera
`scripts/completar_csvs_nuevos.py` con PubMed, Crossref y NCBI, y se puede
corregir a mano: el script conserva las filas existentes.

- `publicaciones.csv`: título, revista, año, primer autor y correo de cada
  publicación, por el DOI que figura en `estudios.csv` (`doi_fuente`). La
  columna `nota` registra las correcciones: tres DOI de la fuente apuntan a
  otro trabajo o no existen (el PMID correcto sale de la serie de GEO que cita
  el estudio) y cinco primeros autores están mal escritos.
- `genomas.csv`: cepa, taxid y linaje de cada conjunto de accesiones. Wu et al.
  2024 midió en *K. pneumoniae* VK055 pero anotó contra el genoma de KPPR1;
  la cepa se registra como VK055.

## Problemas conocidos de la fuente

Constan en `qc_issue` (`source_line LIKE 'CsvsNuevos%'`) y en
`db/cambios_csvs_nuevos.md`:

- `odds_ratio` perdió la coma decimal en casi todos los estudios de RIL-seq
  (`144.852.081.396.333`): no es recuperable y queda nulo.
- `enriquecimiento_log2` (MAPS) tiene el mismo problema en los valores ≥ 1.
- `fdr` usa coma decimal en parte de las filas (`6,98E-15`); se convierte.
- `n_librerias` trae `U`/`u` sin explicación.
- `fdr` guarda según el estudio el p de Fisher, el p ajustado por Bonferroni o
  por Benjamini-Hochberg; `evidence_stats.p_value_kind` lo indica.
