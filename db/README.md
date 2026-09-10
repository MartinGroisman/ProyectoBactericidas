# Base de datos normalizada — Proyecto Bactericidas

Documentación del modelo de datos obtenido a partir de la tabla plana
`Full_data_set_en uso.csv` (32.677 filas × 52 columnas).

La base se regenera íntegramente mediante:

```powershell
python scripts\build_db.py
```

El procedimiento es determinístico: ante los mismos datos de entrada produce los
mismos identificadores, de modo que los resultados son reproducibles.

| Archivo | Contenido |
|---|---|
| `bactericidas.sqlite` | Base de datos completa, con claves foráneas, índices y dos vistas |
| `schema.sql` | Definición del esquema (DDL), copia de la utilizada por el script |
| `csv/*.csv` | Una tabla por archivo, para su carga en PostgreSQL, MySQL, R o pandas |
| `reporte_inconsistencias.md` | Síntesis de las correcciones aplicadas |
| `csv/qc_issue.csv` | Registro detallado de cada inconsistencia, con su línea de origen |

## Identificadores creados

| Identificador | Formato | Criterio de asignación |
|---|---|---|
| `rna.rna_id` | `RNA-000001` | **Una molécula de ARN por cepa.** Criterio de identidad: `(cepa, ncbi_id)`; en ausencia del identificador de NCBI, `(cepa, nombre normalizado)`; luego `(cepa, biocyc_id)`; y, como último recurso, `(cepa, secuencia)` |
| `sequence.seq_id` | `SEQ-<sha1 de 12 hex>` | **Una secuencia nucleotídica única.** Dos registros con secuencia idéntica comparten `seq_id`, con independencia de la fila o la columna de la que provengan |
| `strain_id`, `genome_id`, `replicon_id`, `interaction_id`, `evidence_id`, `binding_site_id`, `publication_id`, `study_id`, `technique_id`, `method_id` | Prefijo y numeración correlativa | Claves sustitutas del resto de las entidades |

`rna_id` y `seq_id` se mantienen deliberadamente independientes: una molécula
puede tener varias secuencias registradas (`rna_sequence`, 690 casos) y una misma
secuencia puede corresponder a varias moléculas (209 casos).

## Modelo

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

Dos tablas resultan centrales en el diseño:

- **`rna`** — las moléculas propiamente dichas. Los sRNA y los ARN blanco residen
  en una misma tabla, dado que 130 sRNA aparecen también como blanco de otros
  sRNA; el rol se indica mediante los campos `is_srna` e `is_target`.
- **`publication`** junto con **`genome_publication`** — la información
  bibliográfica, separada de la biológica. `genome_publication` establece qué
  trabajos respaldan cada genoma; los genomas incorporados sin cita conservan
  `publication_id NULL` y `status = 'pendiente_de_curacion'` (actualmente,
  *Klebsiella pneumoniae* SGH10, `NZ_CP025080.1`, con 3.517 interacciones sin
  referencia bibliográfica).

Cabe distinguir `interaction` de `interaction_evidence`: la primera representa el
par biológico (sRNA → blanco en un genoma determinado) y es única; la segunda
corresponde a cada registro experimental que lo respalda. De este modo, las
32.538 filas del archivo original se reducen a 29.656 pares efectivos sin pérdida
de evidencia. El campo `interaction_evidence.source_line` remite a la línea de
origen.

## Descripción de las tablas

El modelo sigue el principio de almacenar cada entidad una sola vez en su propia
tabla, asignándole un identificador. La información se recompone al vincular las
tablas por esos identificadores —operación denominada `JOIN`—, del mismo modo en
que una planilla de laboratorio consigna el código de una cepa en lugar de
repetir su denominación completa en cada registro. Las dos vistas descritas al
final del apartado entregan esa vinculación ya resuelta.

Las 21 tablas se organizan en cinco bloques.

### 1. Origen biológico del dato

| Tabla | Filas | Descripción de cada registro |
|---|---:|---|
| `phylum`, `genus`, `species` | 7 / 34 / 46 | Niveles taxonómicos, con su correspondiente taxid del NCBI. Se mantienen separados para permitir consultas por nivel —por ejemplo, la totalidad de los registros de *Pseudomonadota* o del género *Escherichia*— sin recurrir al nombre completo de cada cepa. |
| `strain` | 72 | **La cepa empleada en el experimento** (*E. coli* O157:H7 Sakai, *Salmonella* SL1344, *Klebsiella* SGH10, entre otras), con su taxid y su tipo de tinción de Gram. |
| `genome` | 74 | Versión del genoma contra la cual se anotó la cepa. El total excede al de cepas porque dos de ellas fueron anotadas contra **dos ensamblados distintos** (`has_multiple_assemblies = 1`). El campo `data_batch` diferencia el lote curado del genoma incorporado recientemente. |
| `replicon` | 99 | **Cada molécula de ADN del genoma considerada por separado**: cromosoma, megaplásmido y plásmidos. En el archivo original figuraban acumuladas en una única celda (`NC_003197.2;NC_003277.2`); en el modelo cada acceso ocupa un registro, con su orden correspondiente. |

### 2. Las moléculas

| Tabla | Filas | Descripción de cada registro |
|---|---:|---|
| `rna` | 14.027 | **Catálogo de moléculas: un registro equivale a un ARN en una cepa.** Es la tabla de consulta para obtener, por ejemplo, el conjunto de sRNA de *Salmonella*. Los campos `is_srna` e `is_target` indican el rol con que la molécula participa —un mismo sRNA puede actuar como regulador en un registro y como blanco en otro—. Incluye asimismo el biotipo (mRNA, sRNA, tRNA, UGR, entre otros), el producto proteico y los identificadores de NCBI y BioCyc. |
| `sequence` | 32.744 | **Una secuencia nucleotídica, almacenada una única vez**, con su longitud y su contenido de GC. Comprende tanto las secuencias completas de sRNA y de mRNA como los fragmentos correspondientes a los sitios de unión. Las secuencias idénticas comparten `seq_id`, lo que permite detectar sRNA conservados entre cepas sin necesidad de alineamiento previo. |
| `rna_sequence` | 11.008 | Tabla de vinculación entre las dos anteriores: **registra qué secuencias fueron atribuidas a cada molécula**. Cuando una molécula presenta más de una —por diferencias de anotación o de ensamblado—, se conservan todas; la marcada con `is_canonical = 1` es la adoptada como principal, por ser la de mayor frecuencia. |
| `rna_synonym` | 9.928 | Denominaciones alternativas de cada molécula (`yhiB`, `ECK3856`, entre otras), una por registro. Permite recuperar un ARN a partir de nomenclaturas en desuso. |
| `rna_locus` | 4.253 | **Ubicación del gen en el genoma**: coordenadas de inicio y fin, hebra, longitud del tramo y genes flanqueantes. Se mantiene separada de `rna` porque una misma molécula puede presentar coordenadas distintas según la fuente de anotación. El campo `coords_were_flipped = 1` señala los registros que en el archivo original consignaban el inicio con posterioridad al fin. |

### 3. La interacción sRNA – blanco

| Tabla | Filas | Descripción de cada registro |
|---|---:|---|
| `interaction` | 29.656 | **El par biológico: un sRNA determinado y su blanco, en un genoma dado.** No admite repeticiones, por lo que constituye la tabla adecuada para cuantificar, por ejemplo, el número de blancos de RyhB. |
| `interaction_evidence` | 32.538 | **Cada registro experimental que respalda ese par**, equivalente a una fila del archivo original. Contiene el ΔG, la técnica empleada, el `pairing_id` de origen y el campo `source_line`, que remite a la línea exacta del CSV y garantiza la trazabilidad. Un mismo par puede contar con varias evidencias, de ahí que su número supere al de interacciones. |
| `binding_site` | 35.813 | **Las dos regiones apareadas**: un registro para el tramo correspondiente al sRNA y otro para el del mRNA, con sus coordenadas, hebra y secuencia del fragmento. El campo `molecule_role` identifica a cuál corresponde cada uno, y `coord_frame` indica si las coordenadas resultan genómicas o relativas al transcripto. |
| `technique` | 8 | Ensayo general del que procede el dato (`RIL-seq with Hfq`, `CLASH with RNase E`, `MS2-affinity purification`, entre otros), desagregado en método base y proteína de unión a ARN utilizada. |
| `experimental_method` | 37 | Método específico informado por cada estudio (CLASH, fusión traduccional, EMSA, entre otros), clasificado por tipo (alto rendimiento o dirigido) y por grupo (directo o indirecto). Es la tabla que permite restringir el análisis a la evidencia directa. |
| `regulation_type` | 2 | Sentido de la regulación informada: represión o activación. |

### 4. Información bibliográfica

| Tabla | Filas | Descripción de cada registro |
|---|---:|---|
| `publication` | 112 | **Una publicación**: PMID, DOI, título, revista, año, primer autor y correo del autor de correspondencia. Se consigna un único registro por trabajo, con independencia del número de interacciones que aporte. |
| `genome_publication` | 126 | **Trabajos que respaldan cada genoma**, con el número de evidencias aportadas por cada uno. Los genomas incorporados sin cita figuran con `status = 'pendiente_de_curacion'` —actualmente, *Klebsiella pneumoniae* SGH10—, de modo que la omisión queda explicitada. |
| `study` | 39.556 | Vínculo entre una evidencia y su respaldo: **publicación, método y tipo de regulación** con que fue informada, además de la condición de cultivo (fase exponencial, `Δhfq`) y la proteína de unión a ARN involucrada. Un mismo par sRNA–blanco puede sustentarse en varios estudios. |

### 5. Control de calidad

| Tabla | Filas | Descripción de cada registro |
|---|---:|---|
| `qc_issue` | 24.490 | **Registro de auditoría del proceso de limpieza.** Cada entrada consigna la anomalía detectada, la línea del archivo original, el valor observado y el criterio aplicado. Las conversiones sistemáticas, repetidas en miles de celdas, se consignan de forma agregada con `source_line = '(agregado)'` y el total en `n_casos`. Ninguna corrección se aplicó sin dejar constancia. |

### Vistas

| Vista | Finalidad |
|---|---|
| `v_interaccion_completa` | Presenta cada interacción con la cepa, la denominación del sRNA y del blanco, la técnica y el ΔG en un único renglón. Es la representación más próxima al archivo original, ya depurada. |
| `v_publicaciones_por_genoma` | Reúne la producción bibliográfica asociada a cada genoma e identifica los que permanecen sin referencia. |

## Consultas de ejemplo

```sql
-- blancos de RyhB con su ΔG y la técnica empleada
SELECT * FROM v_interaccion_completa WHERE srna_name = 'RyhB' ORDER BY delta_g;

-- bibliografía por genoma, incluidos los casos pendientes
SELECT * FROM v_publicaciones_por_genoma WHERE status = 'pendiente_de_curacion';

-- moléculas distintas que comparten una misma secuencia
SELECT seq_id, GROUP_CONCAT(rna_id) FROM rna_sequence
GROUP BY seq_id HAVING COUNT(DISTINCT rna_id) > 1;

-- correcciones aplicadas sobre una fila determinada del archivo original
SELECT * FROM qc_issue WHERE source_line = '24213';
```

## Correcciones aplicadas

El detalle completo consta en `reporte_inconsistencias.md`. Las principales
intervenciones fueron:

- Eliminación de 139 filas duplicadas de forma exacta.
- Conversión de los valores booleanos de Excel en español (`FALSO`/`VERDADERO`)
  a 0/1 (87.476 celdas).
- Normalización de los indicadores de error de Excel (`#N/D`) y de los literales
  `NA`, `None` y `NULL` a valores nulos efectivos (39.869 celdas).
- Depuración de 73 celdas de `DeltaG` que contenían fragmentos del objeto JSON de
  `pairing` (`: None}`).
- La columna `publications_no` combinaba recuentos con citas bibliográficas
  (`Waters 2016`, `Iosub 2020`): el recuento se recalculó a partir de `studies` y
  la cita se trasladó a la tabla `publication`.
- El campo `exp_methods_no` presentaba discrepancias con el valor real en 50
  filas; se conserva el recalculado.
- Las accesiones múltiples consignadas en una única celda
  (`NC_003197.2;NC_003277.2`) se desagregaron en la tabla `replicon`.
- Las coordenadas invertidas (`start > end`) se reordenaron, dejando constancia
  mediante `coords_were_flipped = 1`.
- Un rango consignado en una sola celda (`637111–637250`) se separó en sus
  valores de inicio y fin.
- Los valores de hebra inválidos (numéricos en `mRNA_binding_strand`) se
  anularon (171 casos).
- Las secuencias con espacios o caracteres no válidos se normalizaron o se
  anularon, según el caso.
- Se repararon los artefactos de recodificación de caracteres (`Δhfq`, nombres de
  especie fragmentados).
- Las denominaciones de sRNA con distinta capitalización entre lotes
  (`RyhB` / `ryhB`) se unificaron mediante `rna_name_key`, conservando la
  denominación original.

Dos situaciones se mantuvieron sin corregir de manera deliberada, por no existir
criterio para determinar el valor correcto sin recurrir a la fuente primaria:

1. El campo `small_rna_length` no coincide con la longitud efectiva de la
   secuencia en 1.374 filas, y la extensión derivada de las coordenadas difiere
   de la secuencia en 18.066 sitios de unión. Se conservan ambos valores
   (`sequence.seq_length` frente a `span_length`) y los casos quedan listados en
   `qc_issue`.
2. Las coordenadas de los sitios de unión combinan marcos de referencia
   distintos: algunas son genómicas y otras relativas al transcripto. El campo
   `binding_site.coord_frame` consigna el marco presumible de cada una, obtenido
   por una heurística basada en la magnitud del valor, por lo que se recomienda
   verificarlo antes de emplear esas coordenadas en el cálculo de posiciones.
