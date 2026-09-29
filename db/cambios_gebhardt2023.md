# Bitácora de cambios: Gebhardt et al. 2023

Registro de todas las modificaciones que `scripts/load_gebhardt2023.py` aplica sobre `db/bactericidas.sqlite` al incorporar el artículo. El archivo se regenera en cada carga, y el detalle fila por fila está en `db/cambios_gebhardt2023.csv`, con 7931 líneas.

## Publicación

| Campo | Valor |
|---|---|
| publication_id | PUB-0113 |
| PMID | 37285605 |
| DOI | 10.1073/pnas.2218407120 |
| Título | Hfq-licensed RNA-RNA interactome in Pseudomonas aeruginosa reveals a keystone sRNA |
| Revista | Proceedings of the National Academy of Sciences of the United States of America |
| Año | 2023 |
| Primer autor | Michael J Gebhardt |
| Correspondencia | simon.dove@childrens.harvard.edu; michael-gebhardt@uiowa.edu |
| Cepa / genoma | Pseudomonas aeruginosa PAO1 (STR-0003) / GEN-0003 |

## Archivos de origen

Todos provienen de `db/fuentes/gebhardt2023/` y se obtuvieron de los Datasets suplementarios S1 y S2 con `scripts/xlsx_a_csv.py`. El SHA-1 permite verificar que la fuente no cambió entre una carga y otra.

| Archivo | Filas leídas | Uso | SHA-1 |
|---|---:|---|---|
| sd01_S_chimeras_in_Exp_Phase.csv | 997 | interacciones RIL-seq, fase exponencial | `5a4edd8555b8` |
| sd01_S_chimeras_in_Stat_Phase.csv | 702 | interacciones RIL-seq, fase estacionaria | `8b543226b461` |
| sd02_pEV_vs_pPhrS_Full_DESeq2.csv | 6213 | producto génico de ARN nuevos; padj del pulso de PhrS | `b5ae360f1013` |
| sd02_pEV_vs_pPhrS_Significant.csv | 677 | blancos de PhrS con cambio de expresión tras el pulso | `8e05123ec3c0` |
| sd02_pEV_vs_pPhrS_deltaseed_Full_DESeq2.csv | 6213 | log2FC con PhrS-Δseed para los blancos del pulso | `22f7e0c49815` |
| sd02_pEV_vs_pPhrS_deltaseed_Signficiant.csv | 569 | significancia con PhrS-Δseed (según los autores) | `6ebea8bced43` |

También se conservan `sd01_Legend.csv` y `sd02_Description.csv`, que describen las columnas de cada dataset; el cargador no las lee.

## Resumen por tabla

| Tabla | Antes | Insertadas | Modificadas | Después |
|---|---:|---:|---:|---:|
| rna | 14027 | 827 | 8 | 14854 |
| rna_synonym | 9928 | 51 |  | 9979 |
| publication | 112 | 1 |  | 113 |
| genome_publication | 126 | 1 |  | 127 |
| interaction | 29656 | 1158 |  | 30814 |
| interaction_evidence | 32538 | 1484 |  | 34022 |
| binding_site | 35813 | 2892 |  | 38705 |
| study | 39556 | 1490 |  | 41046 |
| qc_issue | 24490 | 19 |  | 24509 |

El resto de las tablas (taxonomía, genomas, replicones, secuencias, locus, técnicas, métodos y tipos de regulación) no cambia. Se reutilizaron las técnicas y los métodos que ya existían: `TEC-007` (RIL-seq with Hfq) y los métodos `MET-002` (Translational fusion reporter), `MET-004` (RNA-Sequencing), `MET-008` (RIL-Seq), `MET-009` (Real-Time qRT-PCR), `MET-011` (Western blot), `MET-022` (Site-directed mutagenesis), `MET-023` (Paired compensatory mutations).

Rangos de identificadores asignados:

- `rna`: RNA-014028 … RNA-014854 (827)
- `interaction`: INT-029657 … INT-030814 (1158)
- `interaction_evidence`: EVI-032539 … EVI-034022 (1484)
- `binding_site`: BND-035814 … BND-038705 (2892)
- `study`: STU-039557 … STU-041046 (1490)
- `qc_issue`: 24491 … 24509 (19)

## Registros existentes modificados

La carga modifica 8 registros que ya estaban en la base; todos se listan a continuación. En ningún caso se sobrescribe un valor que no fuera nulo o cero.

| Tabla | ID | Molécula | Campo | Antes | Después | Motivo / origen |
|---|---|---|---|---:|---:|---|
| rna | RNA-002540 | RhlS | ncbi_id | NULL | PA3476.1 | S1_exp #2 |
| rna | RNA-002447 | ErsA | ncbi_id | NULL | PA5492.1 | S1_exp #46 |
| rna | RNA-002532 | ReaL | ncbi_id | NULL | PA3535.1 | S1_exp #233 |
| rna | RNA-010028 | PhrS | is_target | 0 | 1 | rol observado en Dataset S1 |
| rna | RNA-002540 | RhlS | is_target | 0 | 1 | rol observado en Dataset S1 |
| rna | RNA-002447 | ErsA | is_target | 0 | 1 | rol observado en Dataset S1 |
| rna | RNA-002443 | Sr0161 | is_target | 0 | 1 | rol observado en Dataset S1 |
| rna | RNA-010293 | RgsA | is_target | 0 | 1 | rol observado en Dataset S1 |

Sinónimos agregados a moléculas que ya existían:

| rna_id | Molécula | Sinónimo | Origen |
|---|---|---|---|
| RNA-002540 | RhlS | SPA104 | S1_exp #2 |

## Dataset S1: interacciones RIL-seq

| Hoja | Filas leídas | Cargadas | Excluidas (sin sRNA) |
|---|---:|---:|---:|
| sd01_S_chimeras_in_Exp_Phase.csv | 997 | 937 | 60 |
| sd01_S_chimeras_in_Stat_Phase.csv | 702 | 509 | 193 |

Cada fila cargada genera una `interaction_evidence` con técnica `TEC-007`, un `study` con método RIL-Seq, `rbp = Hfq` y la fase en `microbe_condition`, y dos `binding_site`. El campo `comments` del `study` guarda el número de fila de la hoja, los fragmentos quiméricos, el *odds ratio* y el p de Fisher. En 123 filas ambos ARN son sRNA; en ese caso se tomó RNA2 como regulador.

Filas excluidas, por combinación de clases (RNA1 / RNA2):

| RNA1 | RNA2 | n |
|---|---|---:|
| mRNA | mRNA | 159 |
| mRNA | antisense | 19 |
| mRNA | 3-utr | 18 |
| antisense | mRNA | 16 |
| 5-utr | mRNA | 5 |
| 3-utr | mRNA | 5 |
| intergenic | mRNA | 5 |
| mRNA | tRNA | 4 |
| mRNA | 5-utr | 3 |
| tRNA | 3-utr | 3 |
| tRNA | mRNA | 3 |
| antisense | antisense | 3 |
| mRNA | intergenic | 3 |
| rRNA | mRNA | 2 |
| 5-utr | 3-utr | 1 |
| antisense | 3-utr | 1 |
| intergenic | 3-utr | 1 |
| 5-utr | antisense | 1 |
| intergenic | antisense | 1 |

Además quedaron sin cargar las hojas *Self S-Chimeras* (fragmentos de un mismo transcripto) y las filas de encabezado repetidas de cada hoja.

### Interacciones

Se crearon 1158 interacciones (pares sRNA → blanco) y 9 pares que ya existían recibieron evidencia nueva. Estos últimos son coincidencias con estudios previos:

| interaction_id | sRNA | Blanco | Publicaciones previas |
|---|---|---|---|
| INT-003667 | Sr0161 | exsA | Yi-Fan Zhang 2017 |
| INT-003772 | RhlS | vfr | Julian Trouillon 2022 |
| INT-022859 | PhrS | cyoA | Elisabeth Sonnleitner 2011 |
| INT-022862 | PhrS | PA3967 | Elisabeth Sonnleitner 2011 |
| INT-022871 | PhrS | PA0588 | Elisabeth Sonnleitner 2011 |
| INT-022876 | PhrS | pqsE | Elisabeth Sonnleitner 2011 |
| INT-022879 | PhrS | PA1123 | Elisabeth Sonnleitner 2011 |
| INT-022883 | PhrS | PA2166 | Elisabeth Sonnleitner 2011 |
| INT-022889 | PhrS | PA3691 | Elisabeth Sonnleitner 2011 |

### sRNA

Se incorporaron 83 sRNA nuevos (`biotype = sRNA`). De ellos, 47 actúan como reguladores y 36 aparecen sólo como blanco de otro sRNA. La tabla indica el rol de cada uno, que determina `is_srna` / `is_target`, y la cantidad de blancos distintos que tiene como regulador en este trabajo:

| rna_id | Nombre | ncbi_id | Sinónimos | Rol | n blancos | Origen |
|---|---|---|---|---|---:|---|
| RNA-014030 | Spa121 |  |  | regulador y blanco | 1 | S1_exp #5 |
| RNA-014031 | Pant445 |  | Spa93 | regulador | 9 | S1_exp #7 |
| RNA-014032 | OprB-3' | PA3185.1 |  | regulador | 13 | S1_exp #10 |
| RNA-014034 | BetZ | PA5375.1 |  | regulador | 1 | S1_exp #14 |
| RNA-014035 | PA0160.1 | PA0160.1 |  | regulador | 1 | S1_exp #15 |
| RNA-014036 | P30 | PA4726.2 |  | regulador y blanco | 2 | S1_exp #16 |
| RNA-014037 | AS2779 | PA2768.1 |  | regulador y blanco | 27 | S1_exp #17 |
| RNA-014040 | P14 | PA2852.2 |  | blanco | 0 | S1_exp #21 |
| RNA-014051 | AspA-3' | PA5429.1 |  | regulador | 23 | S1_exp #40 |
| RNA-014054 | PA5185as | PA5185.1 |  | regulador y blanco | 1 | S1_exp #42 |
| RNA-014062 | Sr063 |  | Spa38, Sr63 | regulador | 36 | S1_exp #51 |
| RNA-014066 | PrrH | PA4704.3 |  | regulador y blanco | 26 | S1_exp #55 |
| RNA-014067 | 5_utr_betTI | PA5374.1 | BetT1-5' | blanco | 0 | S1_exp #56 |
| RNA-014072 | PA3449.1 | PA3449.1 |  | regulador | 5 | S1_exp #65 |
| RNA-014076 | PA0217-5' | PA0217.1 |  | regulador | 1 | S1_exp #69 |
| RNA-014080 | Pant70 |  | Spa70 | blanco | 0 | S1_exp #76 |
| RNA-014086 | Sr065 |  | Spa181 | blanco | 0 | S1_exp #82 |
| RNA-014087 | Spa170 |  |  | regulador y blanco | 1 | S1_exp #83 |
| RNA-014092 | P8 | PA1030.1 |  | blanco | 0 | S1_exp #89 |
| RNA-014112 | Sr066 |  |  | blanco | 0 | S1_exp #113 |
| RNA-014119 | QuiP-3' | PA1031.1 |  | regulador | 1 | S1_exp #123 |
| RNA-014121 | Sr012 |  |  | blanco | 0 | S1_exp #125 |
| RNA-014127 | Spa103 |  |  | blanco | 0 | S1_exp #133 |
| RNA-014137 | Pant340 |  |  | blanco | 0 | S1_exp #145 |
| RNA-014138 | AceF-3' | PA5016.1 |  | regulador | 17 | S1_exp #146 |
| RNA-014140 | Sr151 |  |  | regulador y blanco | 1 | S1_exp #147 |
| RNA-014144 | Pant133 |  | Spa101 | blanco | 0 | S1_exp #152 |
| RNA-014146 | Pant148 |  |  | blanco | 0 | S1_exp #157 |
| RNA-014156 | Pant130 |  |  | blanco | 0 | S1_exp #170 |
| RNA-014191 | Spa164 |  |  | blanco | 0 | S1_exp #221 |
| RNA-014211 | Spa047 |  |  | blanco | 0 | S1_exp #251 |
| RNA-014212 | BkdZ | PA2250.1 |  | regulador | 27 | S1_exp #252 |
| RNA-014213 | Spa077 |  |  | regulador y blanco | 1 | S1_exp #252 |
| RNA-014228 | Pant72 |  |  | regulador y blanco | 2 | S1_exp #273 |
| RNA-014289 | Spa115 |  |  | regulador y blanco | 1 | S1_exp #358 |
| RNA-014292 | Sr139 |  |  | blanco | 0 | S1_exp #365 |
| RNA-014296 | NtrC-3' | PA5125.01 |  | regulador y blanco | 1 | S1_exp #370 |
| RNA-014299 | Spa059 |  |  | regulador y blanco | 1 | S1_exp #374 |
| RNA-014316 | PA3181-3' | PA3180.1 |  | regulador | 4 | S1_exp #405 |
| RNA-014318 | Spa058 |  |  | blanco | 0 | S1_exp #407 |
| RNA-014323 | PA3133.01 | PA3133.01 |  | regulador | 5 | S1_exp #414 |
| RNA-014328 | Pant297 |  |  | blanco | 0 | S1_exp #422 |
| RNA-014335 | Pant3 |  |  | blanco | 0 | S1_exp #436 |
| RNA-014343 | OprN-3' | PA2495.1 |  | regulador y blanco | 11 | S1_exp #445 |
| RNA-014371 | GabT-3' | PA0266.1 |  | regulador | 1 | S1_exp #489 |
| RNA-014395 | Pant452 |  |  | blanco | 0 | S1_exp #530 |
| RNA-014415 | FlgDas | PA1079.1 |  | regulador y blanco | 1 | S1_exp #559 |
| RNA-014424 | SahHas | PA0432.1 |  | blanco | 0 | S1_exp #578 |
| RNA-014476 | Pant358 |  |  | blanco | 0 | S1_exp #652 |
| RNA-014487 | Spa086 |  |  | regulador | 1 | S1_exp #673 |
| RNA-014488 | Spa107 |  |  | blanco | 0 | S1_exp #673 |
| RNA-014514 | Sr118 |  |  | regulador | 1 | S1_exp #715 |
| RNA-014525 | Pant363 |  |  | blanco | 0 | S1_exp #735 |
| RNA-014530 | RsmZ | PA3621.1 |  | regulador y blanco | 1 | S1_exp #745 |
| RNA-014531 | PaiI | PA3865.2 |  | regulador | 1 | S1_exp #747 |
| RNA-014543 | RsmY | PA0527.1 |  | regulador y blanco | 1 | S1_exp #770 |
| RNA-014544 | Pant257 |  |  | blanco | 0 | S1_exp #771 |
| RNA-014585 | Sr90 |  |  | regulador | 4 | S1_exp #839 |
| RNA-014620 | PA0806.1 | PA0806.1 |  | regulador | 4 | S1_exp #894 |
| RNA-014634 | Pant269 |  |  | blanco | 0 | S1_exp #923 |
| RNA-014643 | Pant54 |  |  | regulador | 1 | S1_exp #945 |
| RNA-014670 | Spa029 |  |  | blanco | 0 | S1_stat #31 |
| RNA-014678 | Pant66 |  |  | blanco | 0 | S1_stat #92 |
| RNA-014680 | Spa095 |  | sRNA1059 | blanco | 0 | S1_stat #94 |
| RNA-014682 | Spa097 |  |  | regulador | 7 | S1_stat #107 |
| RNA-014685 | Spa079 |  |  | regulador | 2 | S1_stat #111 |
| RNA-014690 | AmiL | PA3366.1 |  | regulador | 2 | S1_stat #143 |
| RNA-014695 | Pant150 |  |  | blanco | 0 | S1_stat #158 |
| RNA-014702 | AzoR3-3' | PA3222.1 |  | regulador | 1 | S1_stat #185 |
| RNA-014704 | Pant109 |  |  | regulador y blanco | 1 | S1_stat #187 |
| RNA-014705 | Sr032 |  |  | regulador | 1 | S1_stat #189 |
| RNA-014707 | Spa005 |  |  | blanco | 0 | S1_stat #197 |
| RNA-014725 | Pant102 |  |  | regulador | 1 | S1_stat #261 |
| RNA-014748 | PA1507-3' | PA1506.1 |  | regulador | 1 | S1_stat #327 |
| RNA-014751 | 5_utr_PA2770 |  | PA2770_5' | regulador | 1 | S1_stat #330 |
| RNA-014752 | Spa113 |  |  | blanco | 0 | S1_stat #343 |
| RNA-014756 | Spa108 |  |  | blanco | 0 | S1_stat #362 |
| RNA-014757 | Spa002 |  |  | blanco | 0 | S1_stat #367 |
| RNA-014775 | RnpB | PA4421.1 |  | blanco | 0 | S1_stat #424 |
| RNA-014795 | Pant87 |  | PA0788a | blanco | 0 | S1_stat #518 |
| RNA-014798 | Pant314 |  |  | blanco | 0 | S1_stat #524 |
| RNA-014803 | Spa064 |  |  | regulador | 1 | S1_stat #539 |
| RNA-014820 | Pant215 |  |  | regulador | 2 | S1_stat #586 |

sRNA que ya estaban en la base y reciben interacciones de este trabajo:

| rna_id | Nombre | ncbi_id | n blancos |
|---|---|---|---:|
| RNA-010028 | PhrS | PA3305.1 | 772 |
| RNA-001834 | CrcZ | PA4726.11 | 71 |
| RNA-002540 | RhlS | PA3476.1 | 40 |
| RNA-002447 | ErsA | PA5492.1 | 14 |
| RNA-010293 | RgsA | PA2958.1 | 7 |
| RNA-002532 | ReaL | PA3535.1 | 5 |
| RNA-002443 | Sr0161 |  | 3 |

### Blancos nuevos

Se agregaron 744 moléculas que actúan sólo como blanco. Los mRNA se identifican por locus y toman nombre y producto de la tabla DESeq2. Los transcriptos antisentido e intergénicos se identifican por el nombre que figura en el dataset. El detalle de cada uno está en el CSV de cambios.

| biotype | n |
|---|---:|
| mRNA | 634 |
| antisense | 75 |
| intergenic | 29 |
| tRNA | 5 |
| tmRNA | 1 |

## Dataset S2: pulso de PhrS (RNA-seq)

De los 677 genes con |log2FC| > 1 y padj ≤ 0,05 tras 20 min de expresión de PhrS en fase estacionaria, se cargan sólo los 35 que el dataset marca como blanco directo de PhrS por RIL-seq. Cada uno genera una `interaction_evidence` sin técnica y un `study` con método RNA-Sequencing. La regulación se asigna según el signo del log2FC.

**Error en la fuente.** En la tabla DESeq2 completa de PhrS-Δseed, el p-valor y el padj son idénticos a los de PhrS en 6194 de 6196 genes, aunque los log2FC difieren. Es un error de copia del archivo suplementario, así que esos p-valores no se usan. La columna *Δseed signif.* indica si el gen figura en la hoja de significativos de PhrS-Δseed publicada por los autores. Un blanco que responde a PhrS pero no a PhrS-Δseed depende de la región semilla (170–181).

| Locus | Gen | rna_id | log2FC | padj | Regulación | Δseed log2FC | Δseed signif. | Quimera en S1 | evidence_id |
|---|---|---|---:|---:|---|---:|---|---|---|
| PA0462 | PA0462 | RNA-014152 | 1.49 | 1.9e-18 | Activation | 1.57 | sí | sí | EVI-033985 |
| PA0588 | PA0588 | RNA-010039 | 1.54 | 3.8e-08 | Activation | 1.46 | sí | sí | EVI-033986 |
| PA0765 | mucC | RNA-014085 | 2.39 | 8.3e-24 | Activation | 1.94 | sí | sí | EVI-033987 |
| PA0857 | bolA | RNA-014774 | 1.14 | 4.8e-05 | Activation | 0.93 | no | sí | EVI-033988 |
| PA0973 | oprL | RNA-014101 | 1.13 | 4.3e-10 | Activation | 0.45 | no | sí | EVI-033989 |
| PA1000 | pqsE | RNA-010044 | 1.21 | 4.5e-06 | Activation | -0.19 | no | sí | EVI-033990 |
| PA1123 | PA1123 | RNA-010047 | 1.12 | 6.6e-10 | Activation | -0.46 | no | sí | EVI-033991 |
| PA1209 | PA1209 | RNA-014058 | -1.29 | 7.4e-07 | Repression | 0.31 | no | sí | EVI-033992 |
| PA1287 | PA1287 | RNA-014768 | -1.07 | 5.9e-07 | Repression | -0.42 | no | sí | EVI-033993 |
| PA1317 | cyoA | RNA-010031 | -1.60 | 0.01 | Repression | -0.84 | no | sí | EVI-033994 |
| PA1429 | PA1429 | RNA-002346 | 1.67 | 3.2e-28 | Activation | 1.84 | sí | sí | EVI-033995 |
| PA1562 | acnA | RNA-002131 | 2.08 | 1.3e-16 | Activation | 1.77 | sí | sí | EVI-033996 |
| PA1592 | PA1592 | RNA-014042 | 1.79 | 1.5e-09 | Activation | 1.62 | sí | sí | EVI-033997 |
| PA2006 | PA2006 | RNA-002365 | -1.55 | 1.2e-06 | Repression | -0.14 | no | sí | EVI-033998 |
| PA2046 | PA2046 | RNA-014714 | 2.85 | 2.8e-67 | Activation | 3.22 | sí | sí | EVI-033999 |
| PA2177 | PA2177 | RNA-014189 | 2.39 | 1.8e-42 | Activation | 2.37 | sí | sí | EVI-034000 |
| PA2365 | HsiB3 | RNA-014734 | -1.33 | 0.0027 | Repression | -0.43 | no | sí | EVI-034001 |
| PA2371 | clpV3 | RNA-014731 | -1.09 | 4.9e-09 | Repression | -0.83 | no | sí | EVI-034002 |
| PA2519 | xylS | RNA-014453 | -1.08 | 0.00052 | Repression | -0.15 | no | sí | EVI-034003 |
| PA2798 | PA2798 | RNA-014850 | 2.43 | 1.6e-36 | Activation | 2.06 | sí | sí | EVI-034004 |
| PA2931 | cifR | RNA-014105 | 1.16 | 6.2e-06 | Activation | 0.79 | no | sí | EVI-034005 |
| PA3080 | PA3080 | RNA-014134 | -1.20 | 3e-10 | Repression | -0.63 | no | sí | EVI-034006 |
| PA3887 | nhaP | RNA-002080 | 1.03 | 4e-06 | Activation | 0.98 | no | sí | EVI-034007 |
| PA3929 | cioB | RNA-014842 | 1.42 | 1.5e-13 | Activation | 1.32 | sí | sí | EVI-034008 |
| PA3930 | cioA | RNA-002277 | 1.32 | 4.5e-20 | Activation | 1.10 | sí | sí | EVI-034009 |
| PA3966 | PA3966 | RNA-014669 | -1.42 | 2e-11 | Repression | 0.40 | no | sí | EVI-034010 |
| PA4016 | PA4016 | RNA-014154 | 1.79 | 3.8e-08 | Activation | 1.31 | sí | sí | EVI-034011 |
| PA4751 | ftsH | RNA-014771 | 1.01 | 6.1e-11 | Activation | 1.05 | sí | sí | EVI-034012 |
| PA4812 | fdnG | RNA-001870 | -1.09 | 8.3e-14 | Repression | 0.15 | no | sí | EVI-034013 |
| PA5256 | dsbH | RNA-014069 | 1.45 | 2.5e-08 | Activation | 1.01 | sí | sí | EVI-034014 |
| PA5290 | PA5290 | RNA-014709 | 1.24 | 3e-07 | Activation | 1.25 | sí | sí | EVI-034015 |
| PA5301 | pauR | RNA-002311 | -1.93 | 2.4e-27 | Repression | -0.69 | no | sí | EVI-034016 |
| Spa103 | Spa103 | RNA-014127 | -1.90 | 1.1e-19 | Repression | 0.05 | no | sí | EVI-034017 |
| Spa121 | Spa121 | RNA-014030 | 1.76 | 3.2e-23 | Activation | 0.49 | no | sí | EVI-034018 |
| Spa170 | Spa170 | RNA-014087 | 1.13 | 1.5e-07 | Activation | 0.05 | no | sí | EVI-034019 |

Resumen: 15 de los 35 blancos siguen alterados con PhrS-Δseed y 20 dejan de estarlo (efecto dependiente de la semilla).

## Validaciones de bajo rendimiento (texto del artículo)

Las tres validaciones son de represión en el 5'UTR del blanco, en fase estacionaria. Cada blanco tiene una `interaction_evidence` propia, sin técnica, con un `study` por método.

| Locus | Gen | evidence_id | Método | Resultado |
|---|---|---|---|---|
| PA2009 | hmgA | EVI-034020 | Translational fusion reporter | hmgA::lacZ translational fusion: ~3-fold repression by ectopic PhrS in deltaphrS; lost with PhrS-deltaseed and PhrS-delta1/2seed (Fig. 2C) |
| PA2009 | hmgA | EVI-034020 | Site-directed mutagenesis | PhrS SM171-SM176 dinucleotide substitutions in the predicted pairing region (171-177) impair repression of hmgA::lacZ (Fig. 2I) |
| PA2009 | hmgA | EVI-034020 | Paired compensatory mutations | PhrS-SM175 represses the compensatory hmgA-SM175C::lacZ reporter (Fig. 2J) |
| PA3340 | — | EVI-034021 | Translational fusion reporter | PA3340::lacZ translational fusion: ~1.5-fold higher in deltaphrS; ~4-fold repression by ectopic PhrS; seed-dependent (Fig. 2D) |
| PA2511 | antR | EVI-034022 | Real-Time qRT-PCR | antR ~5-fold, antA ~40-fold, antB ~15-fold higher in deltaphrS; complemented by PhrS (Fig. 4C) |
| PA2511 | antR | EVI-034022 | Translational fusion reporter | antR::lacZ translational fusion: ~3-fold higher in deltaphrS; ~16-fold repression by ectopic PhrS; seed-dependent (Fig. 4D) |
| PA2511 | antR | EVI-034022 | Site-directed mutagenesis | PhrS SM173-SM182 dinucleotide substitutions; SM178-SM181 reduce repression of antR::lacZ, SM179 strongest (Fig. 4E) |
| PA2511 | antR | EVI-034022 | Paired compensatory mutations | chromosomal phrS-SM179 represses antR-M2C::lacZ (Fig. 4H) |
| PA2511 | antR | EVI-034022 | Western blot | AntR-V reduced by PhrS-SM179 in the antR-M2C background (Fig. 4G) |

## Registros en qc_issue

| issue_id | Origen | Columna | Tipo | Valor | Acción |
|---:|---|---|---|---|---|
| 24491 | Gebhardt2023 S1_exp #2 | rna.ncbi_id | ncbi_id_completado | RNA-002540 (RhlS/SPA104) | NULL -> PA3476.1 (locus informado en Dataset S1) |
| 24492 | Gebhardt2023 S1_exp #46 | rna.ncbi_id | ncbi_id_completado | RNA-002447 (ErsA) | NULL -> PA5492.1 (locus informado en Dataset S1) |
| 24493 | Gebhardt2023 S1_exp #55 | RNA Gene | srna_con_locus_de_cds | Sr0161 -> PA0161 | el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre |
| 24494 | Gebhardt2023 S1_exp #72 | RNA Gene | srna_con_locus_de_cds | Sr0161 -> PA0161 | el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre |
| 24495 | Gebhardt2023 S1_exp #233 | rna.ncbi_id | ncbi_id_completado | RNA-002532 (ReaL) | NULL -> PA3535.1 (locus informado en Dataset S1) |
| 24496 | Gebhardt2023 S1_exp #413 | RNA Gene | srna_con_locus_de_cds | Sr0161 -> PA0161 | el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre |
| 24497 | Gebhardt2023 S1_exp #827 | RNA Gene | srna_con_locus_de_cds | Sr0161 -> PA0161 | el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre |
| 24498 | Gebhardt2023 S1_stat #110 | annotation class RNA1 | clase_srna_en_gen_codificante | ahpB (PA0848) | tratado como mRNA |
| 24499 | Gebhardt2023 S1_stat #179 | annotation class RNA1 | clase_srna_en_gen_codificante | PA5446 (PA5446) | tratado como mRNA |
| 24500 | Gebhardt2023 S1_stat #286 | annotation class RNA1 | clase_srna_en_gen_codificante | hsiB3 (PA2365) | tratado como mRNA |
| 24501 | Gebhardt2023 S1_stat #651 | RNA Gene | srna_con_locus_de_cds | Sr0161 -> PA0161 | el locus corresponde a un gen codificante vecino; el sRNA se identifica por nombre |
| 24502 | Gebhardt2023 S1 | * | quimeras_sin_srna_excluidas | 253 | S-chimeras sin sRNA (mRNA-mRNA, tRNA-mRNA, ...) no se cargan |
| 24503 | Gebhardt2023 S1 | RNA1/RNA2 | par_srna_srna | 123 | ambos ARN son sRNA: se toma RNA2 como regulador (convencion RIL-seq) y RNA1 como blanco |
| 24504 | Gebhardt2023 S2 | adjusted p-value | pvalores_repetidos_entre_comparaciones | 6194 de 6196 genes con padj identico en pPhrS y pPhrS-deltaseed | no se usan los p-valores de deltaseed; la significancia se toma de su hoja Significant |
| 24505 | Gebhardt2023 | rna.is_target | rol_nuevo_en_molecula_existente | RNA-010028 (PhrS) | 0 -> 1 |
| 24506 | Gebhardt2023 | rna.is_target | rol_nuevo_en_molecula_existente | RNA-002540 (RhlS) | 0 -> 1 |
| 24507 | Gebhardt2023 | rna.is_target | rol_nuevo_en_molecula_existente | RNA-002447 (ErsA) | 0 -> 1 |
| 24508 | Gebhardt2023 | rna.is_target | rol_nuevo_en_molecula_existente | RNA-002443 (Sr0161) | 0 -> 1 |
| 24509 | Gebhardt2023 | rna.is_target | rol_nuevo_en_molecula_existente | RNA-010293 (RgsA) | 0 -> 1 |
