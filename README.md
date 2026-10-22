# ProyectoBactericidas

Normalización de una base de interacciones sRNA–mRNA bacterianas: se parte de una
tabla plana de 32.677 filas × 52 columnas y se obtiene un modelo relacional de 21
tablas y 2 vistas, con las inconsistencias del archivo original corregidas y
documentadas.

## Contenido del repositorio

| Ruta | Contenido |
|---|---|
| `scripts/build_db.py` | Proceso de extracción, depuración y carga (ETL) |
| `scripts/schema.sql` | Definición del esquema relacional (DDL) |
| `scripts/xlsx_a_csv.py` | Conversión de planillas suplementarias (.xlsx) a CSV |
| `scripts/load_gebhardt2023.py` | Incorporación de Gebhardt et al. 2023 (RIL-seq, *P. aeruginosa* PAO1) |
| `scripts/load_csvs_nuevos.py` | Incorporación de 16 trabajos de un compendio externo (`db/fuentes/csvs_nuevos/`) |
| `scripts/completar_csvs_nuevos.py` | Metadatos de PubMed y NCBI que ese compendio no trae |
| `scripts/exportar_exclusion.py` | Lista de exclusión: publicaciones, pares y alias ya cargados, para buscar fuentes nuevas |
| `scripts/buscar_candidatos.py` | Búsqueda en PubMed y Europe PMC de trabajos candidatos (`db/candidatos/`) |
| `docs/hoja_de_ruta_nuevas_interacciones.md` | Plan para incorporar interacciones publicadas desde 2022 |
| `tests/` | Pruebas: cadena completa de punta a punta y reintentos de red |
| `db/csv/` | Las 24 tablas de la base, una por archivo, con los mismos nombres y columnas |
| `db/README.md` | **Documentación completa del modelo de datos** |
| `db/reporte_inconsistencias.md` | Síntesis de las correcciones aplicadas |

## Reproducción

El único requisito es Python 3.10 o superior: el proceso emplea exclusivamente la
biblioteca estándar (`csv`, `sqlite3`, `hashlib`, `ast`, `re`), sin dependencias
externas.

```powershell
python scripts\build_db.py
```

La ejecución genera `db/bactericidas.sqlite`, las tablas exportadas en `db/csv/`,
una copia del esquema y el reporte de inconsistencias. El procedimiento es
determinístico: ante los mismos datos de entrada produce los mismos
identificadores.

### Fuentes incorporadas después de la normalización

```powershell
python scripts\load_gebhardt2023.py            # agrega Gebhardt et al. 2023 a la base
python scripts\load_csvs_nuevos.py             # agrega los estudios de db/fuentes/csvs_nuevos/
python scripts\exportar_exclusion.py           # regenera db/exclusion/ tras cada carga
python scripts\buscar_candidatos.py            # agrega candidatos nuevos a db/candidatos/
```

Los cargadores se corren en ese orden después de `build_db.py`, que reconstruye
la base desde cero. `completar_csvs_nuevos.py` solo hace falta si cambian los
CSV de `db/fuentes/csvs_nuevos/`: consulta PubMed y NCBI y deja el resultado en
`complementos/`, así que la carga no necesita red.

Cada cargador lee fuentes versionadas en `db/fuentes/`. Las de Gebhardt son los
Datasets S1 y S2 del artículo convertidos a CSV con `scripts\xlsx_a_csv.py`; las
de `csvs_nuevos/` son la exportación del compendio tal como llegó (≈80 MB). Cada
carga deja una bitácora de cambios: la de Gebhardt en `db/cambios_gebhardt2023.md` y
`db/cambios_gebhardt2023.csv`, y la de los CSV nuevos en
`db/cambios_csvs_nuevos.md` y `.csv`. El criterio de cada carga se describe en
[`db/README.md`](db/README.md#fuentes-incorporadas).

La base (≈190 MB) no se versiona; sus tablas sí, en `db/csv/` (≈90 MB): cada archivo lleva el
nombre de su tabla y las columnas en el orden del esquema, de modo que la base se
puede consultar o cargar en otro motor sin correr los scripts. Los scripts de
carga los reescriben, así que cualquier cambio en los datos aparece en el diff.

> **Datos de origen.** El archivo `Full_data_set_en uso.csv` (≈82 MB) no se
> encuentra versionado, por exceder el tamaño recomendado para un repositorio
> público. Debe situarse en la raíz del proyecto antes de ejecutar el script.

### Pruebas

```powershell
python tests\test_e2e_ciclo.py      # cadena completa en una copia limpia (~10 min, requiere red)
python tests\test_reintento.py      # reintentos ante respuestas truncadas (servidor local)
```

`test_e2e_ciclo.py` copia el repositorio a un directorio temporal, sin tocar la
base ni los CSV del árbol de trabajo. Ahí corre la cadena completa, comprueba
que los archivos versionados se regeneren idénticos y recorre un ciclo real de
búsqueda, cribado manual, carga y nueva búsqueda. Necesita el CSV de origen en
la raíz. Ambas pruebas usan sólo la biblioteca estándar y también corren con
`pytest`.

## El modelo en síntesis

```
phylum → genus → species → strain → genome → replicon
                              │        │
                              │        └── genome_publication → publication
                              │
                              ├── rna ──┬── rna_sequence → sequence
                              │         ├── rna_synonym
                              │         └── rna_locus
                              │
                        interaction (sRNA → blanco, único por genoma)
                              │
                     interaction_evidence (una fila del CSV original)
                              ├── binding_site → sequence
                              ├── study → publication / experimental_method / regulation_type
                              ├── evidence_stats (lecturas, p, odds ratio de la fuente)
                              └── duplex_prediction (dúplex predicho, no experimental)

                        srna_seed_region (región consenso de apareamiento de un sRNA)
```

Dos identificadores se crean en el proceso: `rna.rna_id`, que designa una
molécula de ARN por cepa, y `sequence.seq_id`, que designa una secuencia
nucleotídica única —de modo que las secuencias idénticas quedan reunidas bajo un
mismo identificador, con independencia de su procedencia—. Ambos se mantienen
separados: una molécula puede tener varias secuencias registradas (690 casos) y
una misma secuencia puede corresponder a varias moléculas (209 casos).

La información bibliográfica (`publication`, `genome_publication`) se aísla de la
biológica, lo que permite explicitar qué trabajos respaldan cada genoma y cuáles
permanecen sin referencia.

La descripción pormenorizada de cada tabla, junto con consultas de ejemplo,
consta en **[`db/README.md`](db/README.md)**.

## Resultado

| Magnitud | Valor |
|---|---:|
| Filas del archivo original | 32.677 |
| Filas duplicadas exactas eliminadas | 139 |
| Interacciones únicas (sRNA → blanco) | 29.656 |
| Registros de evidencia experimental | 32.538 |
| Moléculas de ARN catalogadas | 14.027 |
| Secuencias nucleotídicas únicas | 32.744 |
| Publicaciones | 112 |
| Cepas / genomas | 72 / 74 |

Son las cifras de `build_db.py`. Con las dos fuentes incorporadas después
(Gebhardt 2023 y los CSV nuevos) la base llega a 63.979 interacciones, 100.839
evidencias, 29.634 moléculas, 129 publicaciones y 79 cepas en 49 especies.

Todas las inconsistencias detectadas se registran en la tabla `qc_issue`, con la
línea del archivo original, el valor observado y el criterio aplicado; ninguna
corrección se realizó sin dejar constancia.
