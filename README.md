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
```

El cargador lee las fuentes versionadas en `db/fuentes/gebhardt2023/`, que son los
Datasets S1 y S2 del artículo convertidos a CSV con `scripts\xlsx_a_csv.py`. Cada
carga deja una bitácora de cambios en `db/cambios_gebhardt2023.md` y
`db/cambios_gebhardt2023.csv`. `build_db.py` reconstruye la base desde cero, así que
el cargador se debe volver a correr después de él. El criterio de carga se
describe en [`db/README.md`](db/README.md#gebhardt-et-al-2023).

> **Datos de origen.** El archivo `Full_data_set_en uso.csv` (≈82 MB) no se
> encuentra versionado, por exceder el tamaño recomendado para un repositorio
> público. Debe situarse en la raíz del proyecto antes de ejecutar el script.

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
                              └── study → publication / experimental_method / regulation_type
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

Todas las inconsistencias detectadas se registran en la tabla `qc_issue`, con la
línea del archivo original, el valor observado y el criterio aplicado; ninguna
corrección se realizó sin dejar constancia.
