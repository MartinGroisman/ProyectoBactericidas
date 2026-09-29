# Hoja de ruta: búsqueda de interacciones sRNA–mRNA no registradas

Objetivo: identificar interacciones sRNA–mRNA con respaldo experimental, publicadas
recientemente, que todavía no figuran en `db/bactericidas.sqlite`, y dejarlas
listas para cargar con el mismo criterio que se usó en Gebhardt et al. 2023.

## 0. Punto de partida

Estado de la base al 2026-09-29, consultado sobre `publication` e `interaction`:

| Año | Publicaciones |
|---|---:|
| ≤ 2020 | 96 |
| 2021 | 12 |
| 2022 | 4 |
| 2023 | 1 (Gebhardt, `PUB-0113`) |
| 2024 – 2026 | 0 |

- **Hueco temporal.** La cobertura es buena hasta 2021, escasa en 2022 y
  prácticamente nula desde 2023. Por eso la ventana de búsqueda arranca el
  **2022-01-01**: 2022 está claramente incompleto.
- **Sesgo taxonómico.** El 90 % de las 30.814 interacciones corresponde a
  *E. coli*, *Salmonella*, *Klebsiella*, *V. cholerae* y *P. aeruginosa*. Entre
  los patógenos ESKAPE no hay datos de ***Acinetobacter baumannii***,
  ***Enterococcus faecium*** ni ***Enterobacter*** spp., y *S. aureus* tiene
  apenas 135 interacciones. Para un proyecto sobre bactericidas, esos son los
  huecos que más importa cubrir.
- **Métodos.** Ya están catalogados CLASH, RIL-seq, GRIL, rGRIL, Hi-GRIL, LIGR y
  MAPS (`experimental_method`). Si aparece una técnica nueva, hay que darla de
  alta antes de cargar sus datos.

## 1. Lista de exclusión (qué ya tenemos)

**Hecho.** `python scripts\exportar_exclusion.py` exporta lo que ya está
cargado a `db/exclusion/`, y hay que volver a correrlo después de cada carga:

| Archivo | Filas | Para qué sirve |
|---|---:|---|
| `publicaciones.csv` | 113 | Descartar trabajos conocidos por PMID o DOI. El DOI está normalizado (minúsculas, sin `https://doi.org/`). Incluye especies, métodos y cantidad de interacciones de cada trabajo. |
| `pares.csv` | 30.814 | Una fila por interacción, con especie, cepa, genoma, sRNA, blanco, claves normalizadas, y los PMID y métodos que la respaldan. |
| `alias.csv` | 58.663 | Todas las formas conocidas de cada ARN (nombre, sinónimos, locus tag de NCBI y de BioCyc, proteína) y su clave de comparación. Resuelve los nombres de un trabajo nuevo a un `rna_id`. |

La clave de comparación es la `match_key` de `load_gebhardt2023.py`: minúsculas,
sólo letras y dígitos, sin ceros a la izquierda. Sólo se versiona
`publicaciones.csv`; los otros dos archivos (≈14 MB) se regeneran.

**Claves ambiguas.** 1.325 claves apuntan a más de un ARN dentro de la misma
cepa, sobre todo en *E. coli* MG1655, y se marcan con `clave_ambigua = 1`. La
mayoría es esperable. Hay variantes del mismo gen que se guardan como moléculas
separadas (`phoP` como `mRNA`, b1130, y como `UGR`, b1130_AS). Hay sinónimos
históricos compartidos por un operón (`rff`, `hrbB`) y copias de elementos IS
con el mismo número ECK. En el paso 4, una clave ambigua cuenta como "ya existe"
si **cualquiera** de sus `rna_id` forma el par; lo que hay que decidir a mano es
sólo a cuál asignar una evidencia nueva.

## 2. Búsqueda sistemática

**Hecho.** `python scripts\buscar_candidatos.py` hace la búsqueda y deja los
resultados en `db/candidatos/candidatos.csv`. Antes hay que correr
`exportar_exclusion.py`, porque los trabajos que ya están en la base se
descartan por PMID o DOI. Ventana: 2022-01-01 a la fecha. Las consultas
exactas están al principio del script. Cada corrida queda registrada en
`db/candidatos/busquedas.csv`, con la fecha, la consulta y la cantidad de
resultados.

### 2a. Bases bibliográficas

| Consulta | Fuente | Resultados (2026-09-29) |
|---|---|---:|
| General: sRNA + bacteria + (blanco, apareamiento, interactoma, Hfq, ProQ), sin revisiones | PubMed | 603 |
| Por método: RIL-seq, CLASH, GRIL-seq, LIGR-seq, MAPS, interactoma de ARN, con contexto sRNA/Hfq/ProQ | PubMed | 54 |
| Por organismo: *A. baumannii* 16, *E. faecium* 3, *Enterobacter* 2, *S. aureus* 63, *K. pneumoniae* 15, *P. aeruginosa* 69, *M. tuberculosis* 49 | PubMed | 217 |
| Por método, en texto completo | Europe PMC | 154 |
| General, sólo preprints (`SRC:PPR`) | Europe PMC | 85 |

La consulta por método exige contexto de sRNA porque "MAPS" y "proximity
ligation" solos traen más de 600 resultados que no tienen que ver. Europe PMC
estuvo intermitente (HTTP 503): el script reintenta, registra el error y sigue,
así que basta con volver a correrlo más tarde.

### 2b. Bases de datos de interacciones (manual)

Hay que cotejar lo publicado en estas bases desde 2022, porque pueden haber
curado trabajos que no aparecieron en la búsqueda:

- **RNAInter** y **NPInter**: interacciones ARN–ARN con referencia.
- **RegulonDB** y **EcoCyc** (*E. coli*), **SubtiWiki** (*B. subtilis*) y
  **AureoWiki** (*S. aureus*): regulación por sRNA curada por especie.
- Datos crudos de RIL-seq y CLASH en **GEO/SRA**: se buscan por palabras clave y
  sirven sólo cuando el artículo no publicó la tabla de quimeras.

Lo que se encuentre se agrega a mano en `candidatos.csv` con
`fuente_busqueda = manual:<base>`. El script conserva esas filas.

### 2c. Rastreo de citas

Se toman los 655 trabajos que citan a las publicaciones de alto rendimiento de la
base (CLASH, RIL-seq, GRIL, rGRIL, Hi-GRIL, LIGR, MAP-Seq), mediante el elink
`pubmed_pubmed_citedin` de NCBI. De ellos quedan 274, los publicados desde 2022
que tienen algún término de sRNA en el título o el resumen.

### Resultado

Quedaron **913 candidatos**; ya estaban en la base otros 5 trabajos, justamente
los 5 que la base tiene de 2022 y 2023, así que la búsqueda los recuperó todos.
Hay 131 preprints, y **69 filas** son otra versión (preprint o duplicado de
PubMed) de un trabajo que también está en la planilla. Se reconocen por el
título y quedan marcadas en `version_de`, apuntando a la versión preferida.

Cada fila trae una preclasificación hecha con expresiones regulares sobre el
título y el resumen (`metodos_detectados`, `clase_metodo`,
`organismos_detectados`, `organismo_en_base`). Con eso se calcula una
`prioridad_sugerida` que sigue la sección 5 y sirve para ordenar el cribado,
no para reemplazarlo:

| Prioridad | Criterio | Candidatos |
|---:|---|---:|
| 1 | Método de alto rendimiento directo (RIL-seq, CLASH, GRIL, LIGR) | 35 |
| 2 | ESKAPE sin cobertura (*A. baumannii*, *E. faecium*, *Enterobacter*, *S. aureus*) con término de sRNA | 72 |
| 3 | Otro método experimental detectado | 243 |
| 4 | Sin método detectado en el resumen | 372 |
| 7 | Probable ARN eucariota (miRNA, lncRNA) sin sRNA en el título | 117 |
| 8 | Sólo predicción computacional | 11 |
| 9 | Revisión, editorial u otro texto no primario | 63 |

Algunos trabajos de prioridad 1: RIL-seq en *A. baumannii* (PMID 41405210),
GRIL-seq en *A. baumannii* AB5075 (39149883), RIL-seq en *K. pneumoniae*
hipervirulenta (38804271, 39138169), RNase III-CLASH en MRSA (35732654,
35732665), RIL-seq en *C. difficile* (37140366) y RIL-seq de ProQ en
*V. cholerae* (39727155).

Las columnas `decision`, `motivo_exclusion` y `notas` quedan vacías para el paso
3. Las nuevas corridas agregan filas y no las sobrescriben. Si un candidato se
carga después a la base, al volver a correr `exportar_exclusion.py` y
`buscar_candidatos.py` queda con `en_base = si`: conserva su cribado y sale de
la cuenta de pendientes.

## 3. Cribado

Se trabaja en dos pasadas: primero por título y resumen, después por texto
completo. La decisión y el motivo quedan en `candidatos.csv`, en las columnas
`decision` y `motivo_exclusion`.

**Se incluye** un trabajo si cumple todo lo siguiente:

- estudia bacterias o arqueas;
- identifica pares sRNA → blanco concretos, con nombre o locus tag de ambos;
- tiene evidencia experimental, directa (quimeras, EMSA, mutaciones
  compensatorias, *footprinting*) o indirecta (fusiones reporteras, RNA-seq tras
  pulso de sRNA, Northern o Western);
- los datos son accesibles: tabla suplementaria, figura con los pares o
  repositorio.

**Se excluye** un trabajo si es una revisión, si sólo presenta predicciones
computacionales (IntaRNA, CopraRNA) sin validar, si trata de interacciones
sRNA–proteína o ARN antisentido de fagos o plásmidos sin blanco ARNm, o si ya
está en la lista de exclusión por PMID o DOI.

## 4. Cotejo a nivel de interacción

Para cada trabajo incluido se extraen los pares y se clasifican contra
`db/exclusion/pares.csv`:

| Caso | Condición | Acción |
|---|---|---|
| **A. Interacción nueva** | El par no existe en ese genoma | Nueva `interaction` + `interaction_evidence` + `study` |
| **B. Evidencia nueva** | El par existe; el trabajo o el método son nuevos | Sólo `interaction_evidence` + `study` sobre la `interaction` existente |
| **C. Organismo nuevo** | La cepa o el genoma no están en `strain`/`genome` | Alta taxonómica y de genoma primero, y después A |
| **D. Ambiguo** | No se puede mapear el nombre del sRNA o del blanco | Se registra en `qc_issue` y no se carga |

Para que el cruce funcione, los nombres se normalizan igual que en
`build_db.py` (`rna_name_key`) y se buscan también en `rna_synonym`. Si el
trabajo usa otra anotación, los locus tags se convierten a los de la base.
Muchas veces el mismo gen lleva distintos locus tags según la anotación (por
ejemplo PA#### frente a PA14_#####), y ese es el origen más común de falsos
"nuevos".

Entregable: un resumen por trabajo con la cantidad de casos A, B, C y D, que
indica cuánto aporta realmente cada uno.

## 5. Priorización

La carga sigue este orden, pensado para ganar el máximo de interacciones con el
mínimo de curaduría:

1. **Alto rendimiento y directo** (RIL-seq, CLASH, GRIL) en organismos que ya
   están en la base: cientos de casos A por trabajo, con infraestructura que ya
   existe.
2. **Cualquier método en organismos ESKAPE ausentes o poco cubiertos**
   (*A. baumannii*, *E. faecium*, *Enterobacter*, *S. aureus*): son los que más
   valor agregan al proyecto, aunque exigen casos C.
3. **Bajo rendimiento** (validaciones individuales): pocas interacciones por
   trabajo, pero con evidencia de mejor calidad. Muchos aportarán casos B.

## 6. Carga

Cada trabajo, o cada lote de trabajos de bajo rendimiento, se carga siguiendo el
patrón de Gebhardt et al. 2023:

- las fuentes se versionan en `db/fuentes/<autorAño>/`, convertidas a CSV con
  `scripts/xlsx_a_csv.py`;
- el cargador propio (`scripts/load_<autorAño>.py`) es idempotente y reutiliza
  técnicas y métodos existentes;
- cada carga genera su bitácora (`db/cambios_<autorAño>.md` y `.csv`) con las
  filas por tabla antes y después, los rangos de identificadores y el SHA-1 de
  las fuentes;
- los problemas se registran en `qc_issue`;
- la sección de `db/README.md` se actualiza, y la lista de exclusión se regenera
  al terminar.

Para las validaciones de bajo rendimiento conviene una sola planilla curada a
mano (`db/fuentes/curaduria_manual.csv`: pmid, organismo, sRNA, blanco, método,
regulación y figura o tabla de origen), con un único cargador genérico, en
lugar de un script por artículo.

## 7. Mantenimiento

- Se guardan las consultas del paso 2 en un script
  (`scripts/buscar_candidatos.py`) que agrega a `candidatos.csv` sólo los PMID
  nuevos.
- Se configuran alertas por correo en PubMed (My NCBI) y en Europe PMC con las
  mismas consultas.
- La búsqueda se repite cada trimestre, y en cada corrida se registra la fecha y
  la cantidad de resultados para que sea reproducible.

## Cronograma orientativo

| Semana | Tarea |
|---|---|
| 1 | Lista de exclusión (paso 1) y script de búsqueda (paso 2a) |
| 2 | Bases de interacciones y rastreo de citas (2b, 2c); planilla de candidatos consolidada |
| 3 | Cribado por título y resumen, y por texto completo |
| 4 | Cotejo a nivel de interacción y priorización |
| 5 en adelante | Carga en el orden de prioridad, un trabajo o lote por vez |
