# Bitácora de cambios: CSV nuevos

Registro de las modificaciones que `scripts/load_csvs_nuevos.py` aplica sobre `db/bactericidas.sqlite` al incorporar los estudios nuevos de `db/fuentes/csvs_nuevos/`. El archivo se regenera en cada carga. El detalle de los registros de catálogo (publicaciones, taxonomía, genomas, técnicas, métodos, ARN, sinónimos, regiones consenso y `qc_issue`) está en `db/cambios_csvs_nuevos.csv`, con 20413 líneas. Las evidencias y sus tablas hijas se resumen por estudio; cada una remite a su fila de origen por `evidence_stats.source_ref` y por `study.comments`.

## Archivos de origen

El SHA-1 permite verificar que la fuente no cambió entre una carga y otra.

| Archivo | Filas leídas | Contenido | SHA-1 |
|---|---:|---|---|
| estudios.csv | 485 | un estudio = publicación, método, condición y ensamblado | `da82dee19141` |
| entidades_rna.csv | 29907 | moléculas por especie, con secuencia y coordenadas | `a58c8ec2fe93` |
| interacciones.csv | 128599 | una evidencia de un par en un estudio | `621c988c252b` |
| duplex.csv | 72847 | dúplex predicho para cada interacción con ventanas de binding | `10d47711fc6a` |
| regiones_consenso.csv | 84 | región del sRNA que concentra el apareamiento | `fdc3ea3a6cb9` |

Complementos, generados por `scripts/completar_csvs_nuevos.py` y corregibles a mano: `complementos/publicaciones.csv` (19) y `complementos/genomas.csv` (15).

## Qué se cargó

De los 485 estudios de la fuente, 427 son la base migrada (`migracion_v1`) y no se leen. De los 58 restantes se cargan 44; los demás se detallan más abajo.

| Estudio | Trabajo | publication_id | Método | Genoma | Condición | Filas | Cargadas | Descartadas | Pares nuevos | Pares previos | Con publicación previa | evidence_id |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| EST0427 | Rabea Ghandour 2025 | PUB-0114 | RIL-Seq / ProQ | GEN-0005 | alta densidad celular (OD600 2,0), medio LB | 1879 | 1879 | 0 | 1394 | 321 | 321 | EVI-034023 … EVI-035901 |
| EST0428 | Rabea Ghandour 2025 | PUB-0114 | RIL-Seq / ProQ | GEN-0005 | baja densidad celular (OD600 0,2), medio LB | 1442 | 1442 | 0 | 863 | 145 | 145 | EVI-035902 … EVI-037343 |
| EST0429 | Dilip Kumar 2025 | PUB-0115 | RIL-Seq / Hfq | GEN-0075 | fase exponencial, medio Stainer-Scholte con ciclodextrina 0,1% y casam | 89 | 89 | 0 | 85 | 0 | 0 | EVI-037344 … EVI-037432 |
| EST0441 | Manuela Fuchs 2023 | PUB-0116 | RIL-Seq / Hfq | GEN-0076 | cultivo anaerobio, cepa hfq::3xFLAG, datasets unificados | 1898 | 1898 | 0 | 1645 | 0 | 0 | EVI-037433 … EVI-039330 |
| EST0444 | Valerie Intorcia 2026 | PUB-0117 | RIL-Seq / Hfq | GEN-0077 | fase exponencial, cepa AB5075-UW con Hfq marcado | 500 | 500 | 0 | 481 | 0 | 0 | EVI-039331 … EVI-039830 |
| EST0445 | Valerie Intorcia 2026 | PUB-0117 | RIL-Seq / Hfq | GEN-0077 | fase estacionaria, cepa AB5075-UW con Hfq marcado | 468 | 468 | 0 | 352 | 0 | 0 | EVI-039831 … EVI-040298 |
| EST0446 | Eric Ruhland 2024 | PUB-0118 | RIL-Seq / Hfq | GEN-0078 | cepa MGH 78578 con Hfq-3xFLAG | 1216 | 1216 | 0 | 1119 | 0 | 0 | EVI-040299 … EVI-041514 |
| EST0447 | Kwok Jian Goh 2024 | PUB-0119 | RIL-Seq / Hfq | GEN-0074 | cepa hipervirulenta SGH10, medio LB | 5543 | 5543 | 0 | 1552 | 3892 | 0 | EVI-041515 … EVI-047057 |
| EST0448 | Kwok Jian Goh 2024 | PUB-0119 | RIL-Seq / Hfq | GEN-0074 | cepa hipervirulenta SGH10, medio DMEM (condiciones de infeccion) | 1061 | 1061 | 0 | 76 | 747 | 0 | EVI-047058 … EVI-048118 |
| EST0449 | Fang Liu 2023 | PUB-0120 | iRIL-Seq / Hfq | GEN-0009 | fase exponencial temprana, OD600 0,5, cepa SL1344 con Hfq-3xFLAG | 414 | 414 | 0 | 361 | 47 | 47 | EVI-048119 … EVI-048532 |
| EST0450 | Fang Liu 2023 | PUB-0120 | iRIL-Seq / Hfq | GEN-0009 | fase exponencial tardia, OD600 2,0, cepa SL1344 con Hfq-3xFLAG | 831 | 831 | 0 | 450 | 122 | 122 | EVI-048533 … EVI-049363 |
| EST0451 | Fang Liu 2023 | PUB-0120 | iRIL-Seq / Hfq | GEN-0009 | fase estacionaria, 3 h despues de OD600 2,0, cepa SL1344 con Hfq-3xFLA | 1689 | 1689 | 0 | 1065 | 99 | 99 | EVI-049364 … EVI-051052 |
| EST0452 | Hoda Kooshapour 2025 | PUB-0121 | RIL-Seq / Hfq | GEN-0009 | dentro de macrofagos infectados, cepa SL1344 con Hfq marcado (RIL-seq  | 7299 | 7299 | 0 | 6426 | 189 | 189 | EVI-051053 … EVI-058351 |
| EST0453 | Hoda Kooshapour 2025 | PUB-0121 | RIL-Seq / Hfq | GEN-0009 | medio inductor de SPI-2 in vitro, cepa SL1344 con Hfq marcado | 4529 | 4529 | 0 | 3283 | 123 | 123 | EVI-058352 … EVI-062880 |
| EST0459 | Aviezer Silverman 2025 | PUB-0122 | RIL-Seq / Hfq | GEN-0002 | sin infectar, 30 min, Hfq marcado con FLAG | 1695 | 1694 | 1 | 617 | 1021 | 1021 | EVI-062881 … EVI-064574 |
| EST0460 | Aviezer Silverman 2025 | PUB-0122 | RIL-Seq / Hfq | GEN-0002 | sin infectar, 60 min, Hfq marcado con FLAG | 1356 | 1354 | 2 | 139 | 851 | 851 | EVI-064575 … EVI-065928 |
| EST0461 | Aviezer Silverman 2025 | PUB-0122 | RIL-Seq / Hfq | GEN-0002 | infectada con fago lambda, 30 min post infeccion, Hfq marcado con FLAG | 1865 | 1747 | 118 | 160 | 1047 | 1047 | EVI-065929 … EVI-067675 |
| EST0462 | Aviezer Silverman 2025 | PUB-0122 | RIL-Seq / Hfq | GEN-0002 | infectada con fago lambda, 60 min post infeccion, Hfq marcado con FLAG | 1464 | 1362 | 102 | 92 | 867 | 867 | EVI-067676 … EVI-069037 |
| EST0463 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | Hfq silvestre con FLAG, RIL-seq anti-FLAG | 3591 | 3591 | 0 | 1283 | 1737 | 1737 | EVI-069038 … EVI-072628 |
| EST0464 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq D9A, cara proximal, RIL-seq anti-FLAG | 2321 | 2321 | 0 | 480 | 1303 | 1303 | EVI-072629 … EVI-074949 |
| EST0465 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq K31A, cara distal, RIL-seq anti-FLAG | 1445 | 1445 | 0 | 219 | 697 | 697 | EVI-074950 … EVI-076394 |
| EST0466 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq Y25D, cara distal, RIL-seq anti-FLAG | 4094 | 4094 | 0 | 1289 | 1433 | 1433 | EVI-076395 … EVI-080488 |
| EST0467 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq R16A, rim, RIL-seq anti-FLAG | 52 | 52 | 0 | 5 | 35 | 35 | EVI-080489 … EVI-080540 |
| EST0468 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | Hfq silvestre con FLAG, RIL-seq con anticuerpo anti-Hfq | 3921 | 3921 | 0 | 838 | 1992 | 1992 | EVI-080541 … EVI-084461 |
| EST0469 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | Hfq silvestre sin marcar, RIL-seq con anticuerpo anti-Hfq | 5495 | 5495 | 0 | 972 | 2420 | 2420 | EVI-084462 … EVI-089956 |
| EST0470 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq R16A con FLAG, rim, RIL-seq con anticuerpo anti-Hfq | 142 | 142 | 0 | 15 | 103 | 103 | EVI-089957 … EVI-090098 |
| EST0471 | Xing Luo 2025 | PUB-0123 | RIL-Seq / Hfq | GEN-0002 | mutante Hfq R16A sin marcar, rim, RIL-seq con anticuerpo anti-Hfq | 127 | 127 | 0 | 10 | 85 | 85 | EVI-090099 … EVI-090225 |
| EST0472 | Xing Luo 2025 | PUB-0123 | Hi-GRIL / Hfq | GEN-0002 | Hfq silvestre, Hi-GRIL-seq con ligasa T4 in vivo | 210 | 210 | 0 | 42 | 118 | 118 | EVI-090226 … EVI-090435 |
| EST0473 | Xing Luo 2025 | PUB-0123 | Hi-GRIL / Hfq | GEN-0002 | mutante Hfq R16A, rim, Hi-GRIL-seq con ligasa T4 in vivo | 28 | 28 | 0 | 9 | 12 | 12 | EVI-090436 … EVI-090463 |
| EST0474 | Xing Luo 2025 | PUB-0123 | Hi-GRIL / Hfq | GEN-0002 | delecion de hfq, Hi-GRIL-seq con ligasa T4 in vivo | 31 | 31 | 0 | 7 | 11 | 11 | EVI-090464 … EVI-090494 |
| EST0475 | Xing Luo 2025 | PUB-0123 | iRIL-Seq / Hfq | GEN-0002 | Hfq silvestre, iRIL-seq con ligasa T4 in vivo y co-IP de Hfq | 1793 | 1793 | 0 | 714 | 566 | 566 | EVI-090495 … EVI-092287 |
| EST0476 | Xing Luo 2025 | PUB-0123 | iRIL-Seq / Hfq | GEN-0002 | mutante Hfq R16A, rim, iRIL-seq con ligasa T4 in vivo y co-IP de Hfq | 102 | 102 | 0 | 30 | 31 | 31 | EVI-092288 … EVI-092389 |
| EST0478 | Natalia I García-Tomsig 2022 | PUB-0124 | MAP-Seq | GEN-0022 | MAPS de AbcR1 con etiqueta MS2, cepa 2011 | 225 | 225 | 0 | 225 | 0 | 0 | EVI-092390 … EVI-092614 |
| EST0479 | Natalia I García-Tomsig 2022 | PUB-0124 | MAP-Seq | GEN-0022 | MAPS de AbcR2 con etiqueta MS2, cepa 2011 | 356 | 356 | 0 | 356 | 0 | 0 | EVI-092615 … EVI-092970 |
| EST0480 | Natalia I García-Tomsig 2026 | PUB-0125 | MAP-Seq | GEN-0022 | MAPS de NfeR1 con etiqueta MS2, cepa 2011, medio minimo con y sin amon | 487 | 487 | 0 | 486 | 0 | 0 | EVI-092971 … EVI-093457 |
| EST0481 | Stuart W McKellar 2022 | PUB-0126 | CLASH / RNase III | GEN-0079 | medio rico TSB, cepa USA300 con RNasa III marcada | 43 | 43 | 0 | 43 | 0 | 0 | EVI-093458 … EVI-093500 |
| EST0482 | Stuart W McKellar 2022 | PUB-0126 | CLASH / RNase III | GEN-0079 | medio RPMI, que imita el ambiente del hospedador | 840 | 840 | 0 | 766 | 0 | 0 | EVI-093501 … EVI-094340 |
| EST0483 | Stuart W McKellar 2022 | PUB-0126 | CLASH / RNase III | GEN-0079 | medio LPM a pH 5,5, que imita el fagosoma | 1251 | 1251 | 0 | 1179 | 0 | 0 | EVI-094341 … EVI-095591 |
| EST0484 | Winton Wu 2024 | PUB-0127 | CLASH / RNase III | GEN-0080 | cepa con tolerancia intermedia a vancomicina, CLASH de RNasa III | 1356 | 1356 | 0 | 768 | 0 | 0 | EVI-095592 … EVI-096947 |
| EST0485 | Gustavo Rios-Delgado 2025 | PUB-0128 | MAP-Seq | GEN-0079 | medio rico BHI | 13 | 13 | 0 | 13 | 0 | 0 | EVI-096948 … EVI-096960 |
| EST0486 | Gustavo Rios-Delgado 2025 | PUB-0128 | MAP-Seq | GEN-0079 | RPMI sin hierro, condicion que induce a IsrR | 84 | 84 | 0 | 76 | 0 | 0 | EVI-096961 … EVI-097044 |
| EST0487 | Stuart W McKellar 2022 | PUB-0126 | CLASH / RNase III | GEN-0079 | consolidado curado de las cuatro condiciones, cepa USA300 | 414 | 414 | 0 | 394 | 0 | 0 | EVI-097045 … EVI-097458 |
| EST0488 | Stuart W McKellar 2022 | PUB-0126 | CLASH / RNase III | GEN-0080 | consolidado curado de dos condiciones, cepa JKD6008 | 581 | 581 | 0 | 578 | 0 | 0 | EVI-097459 … EVI-098039 |
| EST0489 | Kejing Wu 2024 | PUB-0129 | iRIL-Seq / Hfq | GEN-0081 | cepa VK055 hipervirulenta, interactoma de Hfq | 2800 | 2800 | 0 | 2208 | 0 | 0 | EVI-098040 … EVI-100839 |

*Pares previos* son evidencias que se suman a un par sRNA → blanco que ya existía (de este mismo lote o de antes); *con publicación previa*, las que caen sobre un par que ya tenía respaldo bibliográfico antes de esta carga.

Qué guarda `evidence_stats` en cada estudio, según su descripción en la fuente:

| Estudio | p_value_kind | score_kind |
|---|---|---|
| EST0427 | fdr | — |
| EST0428 | fdr | — |
| EST0429 | bonferroni | — |
| EST0441 | fisher | — |
| EST0444 | fisher | — |
| EST0445 | fisher | — |
| EST0446 | fdr | — |
| EST0447 | fisher | odds_ratio |
| EST0448 | fisher | odds_ratio |
| EST0449 | fisher | — |
| EST0450 | fisher | — |
| EST0451 | fisher | — |
| EST0452 | fisher | — |
| EST0453 | fisher | — |
| EST0459 | fisher | — |
| EST0460 | fisher | — |
| EST0461 | fisher | — |
| EST0462 | fisher | — |
| EST0463 | fisher | — |
| EST0464 | fisher | — |
| EST0465 | fisher | — |
| EST0466 | fisher | — |
| EST0467 | fisher | — |
| EST0468 | fisher | — |
| EST0469 | fisher | — |
| EST0470 | fisher | — |
| EST0471 | fisher | — |
| EST0472 | fisher | — |
| EST0473 | fisher | — |
| EST0474 | fisher | — |
| EST0475 | fisher | — |
| EST0476 | fisher | — |
| EST0478 | sin_especificar | log2_fold_change |
| EST0479 | sin_especificar | log2_fold_change |
| EST0480 | sin_especificar | log2_fold_change |
| EST0481 | fdr_bh | connection_score |
| EST0482 | fdr_bh | connection_score |
| EST0483 | fdr_bh | connection_score |
| EST0484 | sin_especificar | odds_ratio |
| EST0485 | sin_especificar | log2_fold_change |
| EST0486 | sin_especificar | log2_fold_change |
| EST0487 | sin_especificar | — |
| EST0488 | sin_especificar | — |
| EST0489 | bonferroni | — |

### Estudios no cargados

| Estudio | Trabajo | Método | Filas | Motivo |
|---|---|---|---:|---|
| EST0430 | Sahar Melamed 2020 | RIL-Seq | 535 | publicacion ya en la base |
| EST0431 | Sahar Melamed 2020 | RIL-Seq | 133 | publicacion ya en la base |
| EST0432 | Sahar Melamed 2020 | RIL-Seq | 2838 | publicacion ya en la base |
| EST0433 | Sahar Melamed 2020 | RIL-Seq | 2565 | publicacion ya en la base |
| EST0434 | Sahar Melamed 2020 | RIL-Seq | 535 | publicacion ya en la base |
| EST0435 | Sahar Melamed 2020 | RIL-Seq | 212 | publicacion ya en la base |
| EST0436 | Sahar Melamed 2020 | RIL-Seq | 2662 | publicacion ya en la base |
| EST0437 | Sahar Melamed 2020 | RIL-Seq | 4270 | publicacion ya en la base |
| EST0438 | Sahar Melamed 2016 | RIL-Seq | 685 | publicacion ya en la base |
| EST0439 | Sahar Melamed 2016 | RIL-Seq | 1198 | publicacion ya en la base |
| EST0440 | Sahar Melamed 2016 | RIL-Seq | 1407 | publicacion ya en la base |
| EST0442 | Michael J Gebhardt 2023 | RIL-Seq | 937 | publicacion ya en la base |
| EST0443 | Michael J Gebhardt 2023 | RIL-Seq | 509 | publicacion ya en la base |
| EST0477 | Jonas Bergman | CLIP-Seq | 0 | sin filas en interacciones.csv |

Las reingestas de Melamed 2016 y 2020 y de Gebhardt 2023 traen además lecturas y p-valores por quimera que la base no tiene para esas evidencias; quedan sin cargar porque no hay una correspondencia fila a fila con las evidencias existentes.

## Publicaciones

Los datos salen de PubMed; la fuente traía errores que se corrigieron en el complemento y constan en `qc_issue`:

| publication_id | PMID | DOI | Primer autor | Año | Revista | Nota |
|---|---|---|---|---|---|---|
| PUB-0114 | 39727155 | 10.1093/nar/gkae1283 | Rabea Ghandour | 2025 | Nucleic acids research |  |
| PUB-0115 | 40626561 | 10.1093/nar/gkaf614 | Dilip Kumar | 2025 | Nucleic acids research |  |
| PUB-0116 | 37140366 | 10.15252/embj.2022112858 | Manuela Fuchs | 2023 | The EMBO journal |  |
| PUB-0117 | 41405210 | 10.1128/mbio.03231-25 | Valerie Intorcia | 2026 | mBio |  |
| PUB-0118 | 38377209 | 10.1073/pnas.2317322121 | Eric Ruhland | 2024 | Proceedings of the National Academy of Sciences of the United States of America |  |
| PUB-0119 | 38804271 | 10.1093/nar/gkae440 | Kwok Jian Goh | 2024 | Nucleic acids research |  |
| PUB-0120 | 38062076 | 10.1038/s41467-023-43632-1 | Fang Liu | 2023 | Nature communications |  |
| PUB-0121 | 41428736 | 10.1093/nar/gkaf1364 | Hoda Kooshapour | 2025 | Nucleic acids research |  |
| PUB-0122 | 41418758 | 10.1016/j.molcel.2025.11.019 | Aviezer Silverman | 2025 | Molecular cell | primer autor en estudios.csv: Daniel Silverman |
| PUB-0123 | 41385330 | 10.1093/nar/gkaf1313 | Xing Luo | 2025 | Nucleic acids research | primer autor en estudios.csv: Xiangqian Luo |
| PUB-0124 | 35164560 | 10.1128/mbio.03576-21 | Natalia I García-Tomsig | 2022 | mBio | anio de la publicacion electronica (PubMed registra 2021); primer autor en estudios.csv: Natalia I. Garcia-Tomsig |
| PUB-0125 | 41747566 | 10.1016/j.micres.2026.128480 | Natalia I García-Tomsig | 2026 | Microbiological research | primer autor en estudios.csv: Natalia I. Garcia-Tomsig |
| PUB-0126 | 35732654 | 10.1038/s41467-022-31173-y | Stuart W McKellar | 2022 | Nature communications | el DOI de la fuente es de otro trabajo; PMID segun GEO GSE166151 |
| PUB-0127 | 38534138 | 10.1128/msystems.00971-23 | Winton Wu | 2024 | mSystems | el DOI de la fuente no existe; PMID segun GEO GSE254532 |
| PUB-0128 | 41042061 | 10.1128/mbio.01415-25 | Gustavo Rios-Delgado | 2025 | mBio | el DOI de la fuente es de otro trabajo; PMID segun GEO GSE296222 |
| PUB-0129 | 39138169 | 10.1038/s41467-024-51213-z | Kejing Wu | 2024 | Nature communications | primer autor en estudios.csv: Winton Wu |

## Taxonomía, cepas y genomas

| Tabla | ID | Valor |
|---|---|---|
| genus | 517 | Bordetella |
| species | 520 | Bordetella pertussis |
| strain | STR-0073 | Bordetella pertussis Tohama I / taxid 257313 / Gram-negative |
| genome | GEN-0075 | Bordetella pertussis Tohama I / NC_002929.2 |
| genus | 1870884 | Clostridioides |
| species | 1496 | Clostridioides difficile |
| strain | STR-0074 | Clostridioides difficile 630 / taxid 272563 / Gram-positive |
| genome | GEN-0076 | Clostridioides difficile 630 / NC_009089.1 |
| genus | 469 | Acinetobacter |
| species | 470 | Acinetobacter baumannii |
| strain | STR-0075 | Acinetobacter baumannii AB5075-UW / taxid - / Gram-negative |
| genome | GEN-0077 | Acinetobacter baumannii AB5075-UW / NZ_CP008706.1;NZ_CP008707.1;NZ_CP008708.1;NZ_CP008709.1 |
| strain | STR-0076 | Klebsiella pneumoniae subsp. pneumoniae MGH 78578 / taxid 272620 / Gram-negative |
| genome | GEN-0078 | Klebsiella pneumoniae subsp. pneumoniae MGH 78578 / NC_009648.1;NC_009649.1;NC_009650.1;NC_009651.1;NC_009652.1;NC_009653.1 |
| strain | STR-0077 | Staphylococcus aureus subsp. aureus USA300_FPR3757 / taxid 451515 / Gram-positive |
| genome | GEN-0079 | Staphylococcus aureus subsp. aureus USA300_FPR3757 / CP000255.1 |
| strain | STR-0078 | Staphylococcus aureus subsp. aureus str. JKD6008 / taxid 546342 / Gram-positive |
| genome | GEN-0080 | Staphylococcus aureus subsp. aureus str. JKD6008 / CP002120.1 |
| strain | STR-0079 | Klebsiella pneumoniae VK055 / taxid - / Gram-negative |
| genome | GEN-0081 | Klebsiella pneumoniae VK055 / NZ_CP009208.1 |

Los estudios cuyo ensamblado ya estaba en la base usan ese genoma. Cuando una accesión aparece en varios genomas (NC_000913.3: MG1655, MC4100, GS162) se usa el primero cargado, y los replicones que el estudio nombra pero el genoma no tiene (plásmidos, el fago lambda) quedan anotados en `qc_issue`.

## Resumen por tabla

| Tabla | Antes | Insertadas | Modificadas | Después |
|---|---:|---:|---:|---:|
| genus | 34 | 3 |  | 37 |
| species | 46 | 3 |  | 49 |
| strain | 72 | 7 |  | 79 |
| genome | 74 | 7 |  | 81 |
| replicon | 99 | 15 |  | 114 |
| sequence | 32744 | 69941 |  | 102685 |
| rna | 14854 | 14780 | 249 | 29634 |
| rna_sequence | 11008 | 5674 |  | 16682 |
| rna_synonym | 9979 | 4869 |  | 14848 |
| rna_locus | 4253 | 6645 |  | 10898 |
| technique | 8 | 4 |  | 12 |
| experimental_method | 37 | 1 |  | 38 |
| publication | 113 | 16 |  | 129 |
| genome_publication | 127 | 17 |  | 144 |
| interaction | 30814 | 33165 |  | 63979 |
| interaction_evidence | 34022 | 66817 |  | 100839 |
| binding_site | 38705 | 122230 |  | 160935 |
| study | 41046 | 66817 |  | 107863 |
| evidence_stats | 1446 | 66817 |  | 68263 |
| duplex_prediction | 0 | 46450 |  | 46450 |
| srna_seed_region | 0 | 84 |  | 84 |
| qc_issue | 24509 | 358 |  | 24867 |

Rangos de identificadores asignados:

- `rna`: RNA-014855 … RNA-029634 (14780)
- `interaction`: INT-030815 … INT-063979 (33165)
- `interaction_evidence`: EVI-034023 … EVI-100839 (66817)
- `binding_site`: BND-038706 … BND-160935 (122230)
- `study`: STU-041047 … STU-107863 (66817)
- `rna_locus`: LOC-004254 … LOC-010898 (6645)
- `srna_seed_region`: SSR-0001 … SSR-0084 (84)
- `qc_issue`: 24510 … 24867 (358)

## Moléculas

Cada entidad de la fuente es una molécula por especie; la base guarda una por cepa. Se busca en la cepa del estudio por locus (`ncbi_id`), BioCyc, sinónimos con forma de locus, nombre y sinónimos, con la misma comparación de nombres que `load_gebhardt2023.py`. Se reutilizaron 6916 moléculas existentes y se crearon 14780. Una molécula nueva toma secuencia y locus de la entidad solo si la entidad está anotada sobre el mismo ensamblado del estudio; 743 secuencias de otro ensamblado no se usaron.

| biotype | n |
|---|---:|
| mRNA | 8652 |
| intergenic | 3225 |
| antisense | 1806 |
| sRNA | 839 |
| ncRNA | 133 |
| tRNA | 97 |
| riboswitch | 20 |
| rRNA | 5 |
| CRISPR | 3 |

Se agregaron 4869 sinónimos, 6645 locus y 69941 secuencias nuevas.

## Registros existentes modificados

La carga modifica 249 registros que ya estaban en la base. En ningún caso se sobrescribe un valor que no fuera nulo o cero.

| Campo | n |
|---|---:|
| rna.is_srna | 141 |
| rna.hfq_class | 56 |
| rna.is_target | 52 |

El detalle de cada uno está en el CSV de cambios (operación `UPDATE`).

## Klebsiella pneumoniae SGH10

El genoma `GEN-0074` figuraba en `genome_publication` como `pendiente_de_curacion`: 3378 de sus pares no tenían ninguna publicación. Goh et al. 2024 (RIL-seq en SGH10) aporta evidencia a 3364 de esos pares (100 %). La fila pendiente se conserva; si se confirma que el lote sin cita es este trabajo, se puede reemplazar por la publicación.

## Dúplex predichos

`duplex_prediction` guarda la predicción de la fuente, que no es un dato experimental. Se cargaron 46450: 40667 de evidencias de esta carga y 5783 de evidencias que ya estaban, reconocidas por sus dos ventanas de binding y su `pairing_id`.

| Filas de duplex.csv fuera de esta carga | n |
|---|---:|
| asociada | 5783 |
| repetida_igual | 5732 |
| sin_evidencia | 20351 |
| sin_ventanas | 134 |

## Regiones consenso y clase Hfq

Se cargaron 84 regiones en `srna_seed_region` (21 con q < 0,05). 35 quedaron con `rna_id` porque la entidad corresponde a una sola molécula; las demás se consultan por especie y nombre del sRNA.

`rna.hfq_class` se completó en 64 moléculas (8 nuevas y 56 existentes), a partir de 39 entidades clasificadas.

## Registros en qc_issue

| Tipo | n_casos |
|---|---:|
| separador_de_miles_corrompido | 52699 |
| coma_decimal | 35854 |
| region_no_es_de_mrna | 14874 |
| valor_no_numerico | 2999 |
| valor_no_finito | 2194 |
| ambiguo_separador_de_miles | 938 |
| molecula_de_otro_organismo | 236 |
| region_de_varias_moleculas | 49 |
| publicacion_ya_en_la_base | 13 |
| columna_corrompida_en_el_estudio | 12 |
| metadato_corregido | 8 |
| replicon_no_registrado_en_el_genoma | 4 |
| accesion_en_varios_genomas | 2 |
| duplex_sin_evidencia_asociada | 2 |
| estudio_sin_interacciones | 1 |
| cepa_distinta_del_ensamblado | 1 |

| issue_id | Origen | Columna | Tipo | Valor | Acción | n_casos |
|---:|---|---|---|---|---|---:|
| 24510 | CsvsNuevos EST0430 | * | publicacion_ya_en_la_base | PMID 31761494, 535 filas | no se carga: reingesta del mismo experimento | 1 |
| 24511 | CsvsNuevos EST0431 | * | publicacion_ya_en_la_base | PMID 31761494, 133 filas | no se carga: reingesta del mismo experimento | 1 |
| 24512 | CsvsNuevos EST0432 | * | publicacion_ya_en_la_base | PMID 31761494, 2838 filas | no se carga: reingesta del mismo experimento | 1 |
| 24513 | CsvsNuevos EST0433 | * | publicacion_ya_en_la_base | PMID 31761494, 2565 filas | no se carga: reingesta del mismo experimento | 1 |
| 24514 | CsvsNuevos EST0434 | * | publicacion_ya_en_la_base | PMID 31761494, 535 filas | no se carga: reingesta del mismo experimento | 1 |
| 24515 | CsvsNuevos EST0435 | * | publicacion_ya_en_la_base | PMID 31761494, 212 filas | no se carga: reingesta del mismo experimento | 1 |
| 24516 | CsvsNuevos EST0436 | * | publicacion_ya_en_la_base | PMID 31761494, 2662 filas | no se carga: reingesta del mismo experimento | 1 |
| 24517 | CsvsNuevos EST0437 | * | publicacion_ya_en_la_base | PMID 31761494, 4270 filas | no se carga: reingesta del mismo experimento | 1 |
| 24518 | CsvsNuevos EST0438 | * | publicacion_ya_en_la_base | PMID 27588604, 685 filas | no se carga: reingesta del mismo experimento | 1 |
| 24519 | CsvsNuevos EST0439 | * | publicacion_ya_en_la_base | PMID 27588604, 1198 filas | no se carga: reingesta del mismo experimento | 1 |
| 24520 | CsvsNuevos EST0440 | * | publicacion_ya_en_la_base | PMID 27588604, 1407 filas | no se carga: reingesta del mismo experimento | 1 |
| 24521 | CsvsNuevos EST0442 | * | publicacion_ya_en_la_base | PMID 37285605, 937 filas | no se carga: reingesta del mismo experimento | 1 |
| 24522 | CsvsNuevos EST0443 | * | publicacion_ya_en_la_base | PMID 37285605, 509 filas | no se carga: reingesta del mismo experimento | 1 |
| 24523 | CsvsNuevos EST0477 | * | estudio_sin_interacciones | CLIP-Seq | no se carga | 1 |
| 24524 | CsvsNuevos 10.1016/j.molcel.2025.11.019 | publication_doi | metadato_corregido | 10.1016/j.molcel.2025.11.019 | primer autor en estudios.csv: Daniel Silverman | 1 |
| 24525 | CsvsNuevos 10.1093/nar/gkaf1313 | publication_doi | metadato_corregido | 10.1093/nar/gkaf1313 | primer autor en estudios.csv: Xiangqian Luo | 1 |
| 24526 | CsvsNuevos 10.1128/mbio.03576-21 | publication_doi | metadato_corregido | 10.1128/mbio.03576-21 | anio de la publicacion electronica (PubMed registra 2021); primer autor en estudios.csv: Natalia I. Garcia-Tomsig | 1 |
| 24527 | CsvsNuevos 10.1016/j.micres.2026.128480 | publication_doi | metadato_corregido | 10.1016/j.micres.2026.128480 | primer autor en estudios.csv: Natalia I. Garcia-Tomsig | 1 |
| 24528 | CsvsNuevos 10.1038/s41467-022-34073-3 | publication_doi | metadato_corregido | 10.1038/s41467-022-34073-3 | el DOI de la fuente es de otro trabajo; PMID segun GEO GSE166151 | 1 |
| 24529 | CsvsNuevos 10.1128/spectrum.00552-24 | publication_doi | metadato_corregido | 10.1128/spectrum.00552-24 | el DOI de la fuente no existe; PMID segun GEO GSE254532 | 1 |
| 24530 | CsvsNuevos 10.1128/jb.00145-25 | publication_doi | metadato_corregido | 10.1128/jb.00145-25 | el DOI de la fuente es de otro trabajo; PMID segun GEO GSE296222 | 1 |
| 24531 | CsvsNuevos 10.1038/s41467-024-51213-z | publication_doi | metadato_corregido | 10.1038/s41467-024-51213-z | primer autor en estudios.csv: Winton Wu | 1 |
| 24532 | CsvsNuevos EST0427 | ensamblado_accession | replicon_no_registrado_en_el_genoma | GEN-0005: NC_002506 | se usa el genoma existente; el replicon no se agrega | 1 |
| 24533 | CsvsNuevos EST0447 | ensamblado_accession | replicon_no_registrado_en_el_genoma | GEN-0074: NZ_CP025081.1 | se usa el genoma existente; el replicon no se agrega | 1 |
| 24534 | CsvsNuevos EST0452 | ensamblado_accession | replicon_no_registrado_en_el_genoma | GEN-0009: NC_017718.1, NC_017719.1, NC_017720.1 | se usa el genoma existente; el replicon no se agrega | 1 |
| 24535 | CsvsNuevos EST0459 | ensamblado_accession | accesion_en_varios_genomas | NC_000913.3: GEN-0002, GEN-0029, GEN-0036 | se usa GEN-0002 (STR-0002), el primero cargado | 1 |
| 24536 | CsvsNuevos EST0459 | ensamblado_accession | replicon_no_registrado_en_el_genoma | GEN-0002: J02459.1 | se usa el genoma existente; el replicon no se agrega | 1 |
| 24537 | CsvsNuevos EST0463 | ensamblado_accession | accesion_en_varios_genomas | NC_000913.3: GEN-0002, GEN-0029, GEN-0036 | se usa GEN-0002 (STR-0002), el primero cargado | 1 |
| 24538 | CsvsNuevos EST0489 | strain_name | cepa_distinta_del_ensamblado | Klebsiella pneumoniae VK055 | cepa del experimento; el ensamblado es de Klebsiella pneumoniae subsp. pneumoniae ATCC 43816 KPPR1 | 1 |
| 24539 | CsvsNuevos duplex.csv | interaccion_id | duplex_sin_evidencia_asociada | sin_ventanas: 134 filas | no se carga | 1 |
| 24540 | CsvsNuevos duplex.csv | interaccion_id | duplex_sin_evidencia_asociada | sin_evidencia: 20351 filas | no se carga | 1 |
| 24541 | CsvsNuevos regiones_consenso RNA27191 | entidad_id | region_de_varias_moleculas | srn_4100_sprG3: RNA-025631, RNA-027722 | rna_id = NULL; se usa especie y nombre | 1 |
| 24542 | CsvsNuevos regiones_consenso RNA00539 | entidad_id | region_de_varias_moleculas | ChiX: RNA-000056, RNA-000686, RNA-008756 | rna_id = NULL; se usa especie y nombre | 1 |
| 24543 | CsvsNuevos regiones_consenso RNA26709 | entidad_id | region_de_varias_moleculas | srn_3840_sprG1: RNA-025191, RNA-027703 | rna_id = NULL; se usa especie y nombre | 1 |
| 24544 | CsvsNuevos regiones_consenso RNA00638 | entidad_id | region_de_varias_moleculas | CyaR: RNA-000141, RNA-000694, RNA-008633 | rna_id = NULL; se usa especie y nombre | 1 |
| 24545 | CsvsNuevos regiones_consenso RNA02767 | entidad_id | region_de_varias_moleculas | RprA: RNA-000233, RNA-000755, RNA-008686 | rna_id = NULL; se usa especie y nombre | 1 |
| 24546 | CsvsNuevos regiones_consenso RNA02865 | entidad_id | region_de_varias_moleculas | RyhB: RNA-000001, RNA-000781, RNA-008679 | rna_id = NULL; se usa especie y nombre | 1 |
| 24547 | CsvsNuevos regiones_consenso RNA05541 | entidad_id | region_de_varias_moleculas | rprA: RNA-012217, RNA-017965 | rna_id = NULL; se usa especie y nombre | 1 |
| 24548 | CsvsNuevos regiones_consenso RNA05242 | entidad_id | region_de_varias_moleculas | mgrR: RNA-012249, RNA-017944 | rna_id = NULL; se usa especie y nombre | 1 |
| 24549 | CsvsNuevos regiones_consenso RNA02948 | entidad_id | region_de_varias_moleculas | SgrS: RNA-000382, RNA-000929, RNA-008642 | rna_id = NULL; se usa especie y nombre | 1 |
| 24550 | CsvsNuevos regiones_consenso RNA00287 | entidad_id | region_de_varias_moleculas | ArcZ: RNA-000278, RNA-000673, RNA-008635 | rna_id = NULL; se usa especie y nombre | 1 |
| 24551 | CsvsNuevos regiones_consenso RNA04883 | entidad_id | region_de_varias_moleculas | cpxQ: RNA-012222, RNA-017926 | rna_id = NULL; se usa especie y nombre | 1 |
| 24552 | CsvsNuevos regiones_consenso RNA01231 | entidad_id | region_de_varias_moleculas | GcvB: RNA-000301, RNA-000679, RNA-008637 | rna_id = NULL; se usa especie y nombre | 1 |
| 24553 | CsvsNuevos regiones_consenso RNA06431 | entidad_id | region_de_varias_moleculas | spf: RNA-012257, RNA-018015 | rna_id = NULL; se usa especie y nombre | 1 |
| 24554 | CsvsNuevos regiones_consenso RNA02227 | entidad_id | region_de_varias_moleculas | OmrA: RNA-000303, RNA-000850, RNA-009209, RNA-010024 | rna_id = NULL; se usa especie y nombre | 1 |
| 24555 | CsvsNuevos regiones_consenso RNA01956 | entidad_id | region_de_varias_moleculas | MicF: RNA-000288, RNA-001156, RNA-008761 | rna_id = NULL; se usa especie y nombre | 1 |
| 24556 | CsvsNuevos regiones_consenso RNA00807 | entidad_id | region_de_varias_moleculas | DsrA: RNA-000241, RNA-000770, RNA-008862 | rna_id = NULL; se usa especie y nombre | 1 |
| 24557 | CsvsNuevos regiones_consenso RNA02861 | entidad_id | region_de_varias_moleculas | RyeA: RNA-000406, RNA-000684 | rna_id = NULL; se usa especie y nombre | 1 |
| 24558 | CsvsNuevos regiones_consenso RNA01288 | entidad_id | region_de_varias_moleculas | GlnZ: RNA-008014, RNA-008688 | rna_id = NULL; se usa especie y nombre | 1 |
| 24559 | CsvsNuevos regiones_consenso RNA03005 | entidad_id | region_de_varias_moleculas | SroH: RNA-000313, RNA-000709 | rna_id = NULL; se usa especie y nombre | 1 |
| 24560 | CsvsNuevos regiones_consenso RNA01943 | entidad_id | region_de_varias_moleculas | MgrR: RNA-000102, RNA-000712, RNA-008640 | rna_id = NULL; se usa especie y nombre | 1 |
| 24561 | CsvsNuevos regiones_consenso RNA05016 | entidad_id | region_de_varias_moleculas | fnrS: RNA-012252, RNA-017942 | rna_id = NULL; se usa especie y nombre | 1 |
| 24562 | CsvsNuevos regiones_consenso RNA01272 | entidad_id | region_de_varias_moleculas | GlmZ: RNA-000130, RNA-000837, RNA-009408 | rna_id = NULL; se usa especie y nombre | 1 |
| 24563 | CsvsNuevos regiones_consenso RNA01203 | entidad_id | region_de_varias_moleculas | GadY: RNA-000060, RNA-000749, RNA-008819 | rna_id = NULL; se usa especie y nombre | 1 |
| 24564 | CsvsNuevos regiones_consenso RNA01111 | entidad_id | region_de_varias_moleculas | FnrS: RNA-000438, RNA-002981, RNA-008651 | rna_id = NULL; se usa especie y nombre | 1 |
| 24565 | CsvsNuevos regiones_consenso RNA26684 | entidad_id | region_de_varias_moleculas | srn_2740_Teg108: RNA-025168, RNA-028113 | rna_id = NULL; se usa especie y nombre | 1 |
| 24566 | CsvsNuevos regiones_consenso RNA02858 | entidad_id | region_de_varias_moleculas | RybB: RNA-000369, RNA-000723, RNA-009211 | rna_id = NULL; se usa especie y nombre | 1 |
| 24567 | CsvsNuevos regiones_consenso RNA04900 | entidad_id | region_de_varias_moleculas | cyaR: RNA-012214, RNA-017924 | rna_id = NULL; se usa especie y nombre | 1 |
| 24568 | CsvsNuevos regiones_consenso RNA04794 | entidad_id | region_de_varias_moleculas | arcZ: RNA-012218, RNA-017922 | rna_id = NULL; se usa especie y nombre | 1 |
| 24569 | CsvsNuevos regiones_consenso RNA02252 | entidad_id | region_de_varias_moleculas | OxyS: RNA-000359, RNA-000758, RNA-008653 | rna_id = NULL; se usa especie y nombre | 1 |
| 24570 | CsvsNuevos regiones_consenso RNA05051 | entidad_id | region_de_varias_moleculas | gcvB: RNA-012224, RNA-017920 | rna_id = NULL; se usa especie y nombre | 1 |
| 24571 | CsvsNuevos regiones_consenso RNA27290 | entidad_id | region_de_varias_moleculas | srn_4830_Sau6072: RNA-025722, RNA-027751 | rna_id = NULL; se usa especie y nombre | 1 |
| 24572 | CsvsNuevos regiones_consenso RNA04952 | entidad_id | region_de_varias_moleculas | dsrA: RNA-012233, RNA-017976 | rna_id = NULL; se usa especie y nombre | 1 |
| 24573 | CsvsNuevos regiones_consenso RNA27377 | entidad_id | region_de_varias_moleculas | srn_1510_rsaA: RNA-025801, RNA-027629 | rna_id = NULL; se usa especie y nombre | 1 |
| 24574 | CsvsNuevos regiones_consenso RNA05247 | entidad_id | region_de_varias_moleculas | micF: RNA-012264, RNA-017923 | rna_id = NULL; se usa especie y nombre | 1 |
| 24575 | CsvsNuevos regiones_consenso RNA02989 | entidad_id | region_de_varias_moleculas | Spf: RNA-000137, RNA-000670, RNA-008647 | rna_id = NULL; se usa especie y nombre | 1 |
| 24576 | CsvsNuevos regiones_consenso RNA05245 | entidad_id | region_de_varias_moleculas | micA: RNA-012225, RNA-017993 | rna_id = NULL; se usa especie y nombre | 1 |
| 24577 | CsvsNuevos regiones_consenso RNA00751 | entidad_id | region_de_varias_moleculas | DicF: RNA-000431, RNA-001173 | rna_id = NULL; se usa especie y nombre | 1 |
| 24578 | CsvsNuevos regiones_consenso RNA05593 | entidad_id | region_de_varias_moleculas | sdsR: RNA-012279, RNA-017930 | rna_id = NULL; se usa especie y nombre | 1 |
| 24579 | CsvsNuevos regiones_consenso RNA26695 | entidad_id | region_de_varias_moleculas | srn_3580_SprA1: RNA-025179, RNA-027990 | rna_id = NULL; se usa especie y nombre | 1 |
| 24580 | CsvsNuevos regiones_consenso RNA01873 | entidad_id | region_de_varias_moleculas | McaS: RNA-000244, RNA-008019, RNA-008708 | rna_id = NULL; se usa especie y nombre | 1 |
| 24581 | CsvsNuevos regiones_consenso RNA02228 | entidad_id | region_de_varias_moleculas | OmrB: RNA-000261, RNA-000718, RNA-008975, RNA-010026 | rna_id = NULL; se usa especie y nombre | 1 |
| 24582 | CsvsNuevos regiones_consenso RNA02860 | entidad_id | region_de_varias_moleculas | RydC: RNA-000811, RNA-008921 | rna_id = NULL; se usa especie y nombre | 1 |
| 24583 | CsvsNuevos regiones_consenso RNA26711 | entidad_id | region_de_varias_moleculas | srn_3910_RNAIII: RNA-025193, RNA-027708 | rna_id = NULL; se usa especie y nombre | 1 |
| 24584 | CsvsNuevos regiones_consenso RNA01957 | entidad_id | region_de_varias_moleculas | MicL: RNA-008406, RNA-008764 | rna_id = NULL; se usa especie y nombre | 1 |
| 24585 | CsvsNuevos regiones_consenso RNA01954 | entidad_id | region_de_varias_moleculas | MicA: RNA-000298, RNA-000675 | rna_id = NULL; se usa especie y nombre | 1 |
| 24586 | CsvsNuevos regiones_consenso RNA05069 | entidad_id | region_de_varias_moleculas | glnZ: RNA-012240, RNA-018022 | rna_id = NULL; se usa especie y nombre | 1 |
| 24587 | CsvsNuevos regiones_consenso RNA00334 | entidad_id | region_de_varias_moleculas | ArrS: RNA-000677, RNA-008643 | rna_id = NULL; se usa especie y nombre | 1 |
| 24588 | CsvsNuevos regiones_consenso RNA05581 | entidad_id | region_de_varias_moleculas | ryhB-2: RNA-012213, RNA-018273 | rna_id = NULL; se usa especie y nombre | 1 |
| 24589 | CsvsNuevos regiones_consenso RNA02593 | entidad_id | region_de_varias_moleculas | RdlA: RNA-000337, RNA-001384 | rna_id = NULL; se usa especie y nombre | 1 |
| 24590 | CsvsNuevos EST0427 | fdr | coma_decimal |  | convertida a punto | 774 |
| 24591 | CsvsNuevos EST0427 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1879 |
| 24592 | CsvsNuevos EST0427 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 174 |
| 24593 | CsvsNuevos EST0427 | region_blanco | region_no_es_de_mrna | mRNA | region_involved_mrna = NULL | 1595 |
| 24594 | CsvsNuevos EST0427 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 110 |
| 24595 | CsvsNuevos EST0428 | fdr | coma_decimal |  | convertida a punto | 650 |
| 24596 | CsvsNuevos EST0428 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1442 |
| 24597 | CsvsNuevos EST0428 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 187 |
| 24598 | CsvsNuevos EST0428 | region_blanco | region_no_es_de_mrna | mRNA | region_involved_mrna = NULL | 1152 |
| 24599 | CsvsNuevos EST0428 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 103 |
| 24600 | CsvsNuevos EST0429 | fdr | coma_decimal |  | convertida a punto | 67 |
| 24601 | CsvsNuevos EST0429 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 89 |
| 24602 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 6 |
| 24603 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 21 |
| 24604 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | IGT | region_involved_mrna = NULL | 1 |
| 24605 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | IGT_AS | region_involved_mrna = NULL | 1 |
| 24606 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 3 |
| 24607 | CsvsNuevos EST0429 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 5 |
| 24608 | CsvsNuevos EST0441 | fdr | coma_decimal |  | convertida a punto | 1382 |
| 24609 | CsvsNuevos EST0441 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1887 |
| 24610 | CsvsNuevos EST0441 | odds_ratio | valor_no_finito | Inf | -> NULL | 11 |
| 24611 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 55 |
| 24612 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | CRISPR | region_involved_mrna = NULL | 17 |
| 24613 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 78 |
| 24614 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | Riboswitch | region_involved_mrna = NULL | 33 |
| 24615 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 48 |
| 24616 | CsvsNuevos EST0441 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24617 | CsvsNuevos EST0444 | fdr | coma_decimal |  | convertida a punto | 415 |
| 24618 | CsvsNuevos EST0444 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 492 |
| 24619 | CsvsNuevos EST0444 | odds_ratio | valor_no_finito | inf | -> NULL | 8 |
| 24620 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 25 |
| 24621 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | CRISPR | region_involved_mrna = NULL | 2 |
| 24622 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 34 |
| 24623 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 2 |
| 24624 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 45 |
| 24625 | CsvsNuevos EST0444 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 15 |
| 24626 | CsvsNuevos EST0445 | fdr | coma_decimal |  | convertida a punto | 387 |
| 24627 | CsvsNuevos EST0445 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 426 |
| 24628 | CsvsNuevos EST0445 | odds_ratio | valor_no_finito | inf | -> NULL | 42 |
| 24629 | CsvsNuevos EST0445 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 35 |
| 24630 | CsvsNuevos EST0445 | region_blanco | region_no_es_de_mrna | CRISPR | region_involved_mrna = NULL | 1 |
| 24631 | CsvsNuevos EST0445 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 28 |
| 24632 | CsvsNuevos EST0445 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 54 |
| 24633 | CsvsNuevos EST0445 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 5 |
| 24634 | CsvsNuevos EST0446 | fdr | coma_decimal |  | convertida a punto | 223 |
| 24635 | CsvsNuevos EST0446 | fdr | valor_no_finito | NaN | -> NULL | 311 |
| 24636 | CsvsNuevos EST0446 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 101 |
| 24637 | CsvsNuevos EST0446 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 62 |
| 24638 | CsvsNuevos EST0447 | fdr | coma_decimal |  | convertida a punto | 2 |
| 24639 | CsvsNuevos EST0447 | n_librerias | valor_no_numerico | u | -> NULL | 1423 |
| 24640 | CsvsNuevos EST0447 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1 |
| 24641 | CsvsNuevos EST0447 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 299 |
| 24642 | CsvsNuevos EST0447 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 1079 |
| 24643 | CsvsNuevos EST0447 | region_blanco | region_no_es_de_mrna | otro_ncRNA | region_involved_mrna = NULL | 9 |
| 24644 | CsvsNuevos EST0447 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 30 |
| 24645 | CsvsNuevos EST0447 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 18 |
| 24646 | CsvsNuevos EST0448 | n_librerias | valor_no_numerico | u | -> NULL | 317 |
| 24647 | CsvsNuevos EST0448 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 2 |
| 24648 | CsvsNuevos EST0448 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 30 |
| 24649 | CsvsNuevos EST0448 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 183 |
| 24650 | CsvsNuevos EST0448 | region_blanco | region_no_es_de_mrna | otro_ncRNA | region_involved_mrna = NULL | 2 |
| 24651 | CsvsNuevos EST0448 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 17 |
| 24652 | CsvsNuevos EST0448 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 3 |
| 24653 | CsvsNuevos EST0449 | fdr | coma_decimal |  | convertida a punto | 1 |
| 24654 | CsvsNuevos EST0449 | odds_ratio | columna_corrompida_en_el_estudio |  | -> NULL (la mayoria de los valores del estudio tienen el separador de miles corrompido) | 1 |
| 24655 | CsvsNuevos EST0449 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 413 |
| 24656 | CsvsNuevos EST0449 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 29 |
| 24657 | CsvsNuevos EST0449 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 50 |
| 24658 | CsvsNuevos EST0449 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 24 |
| 24659 | CsvsNuevos EST0450 | fdr | coma_decimal |  | convertida a punto | 1 |
| 24660 | CsvsNuevos EST0450 | odds_ratio | columna_corrompida_en_el_estudio |  | -> NULL (la mayoria de los valores del estudio tienen el separador de miles corrompido) | 1 |
| 24661 | CsvsNuevos EST0450 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 830 |
| 24662 | CsvsNuevos EST0450 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 59 |
| 24663 | CsvsNuevos EST0450 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 65 |
| 24664 | CsvsNuevos EST0450 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 45 |
| 24665 | CsvsNuevos EST0451 | fdr | coma_decimal |  | convertida a punto | 5 |
| 24666 | CsvsNuevos EST0451 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1689 |
| 24667 | CsvsNuevos EST0451 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 170 |
| 24668 | CsvsNuevos EST0451 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 132 |
| 24669 | CsvsNuevos EST0451 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 61 |
| 24670 | CsvsNuevos EST0452 | fdr | coma_decimal |  | convertida a punto | 6260 |
| 24671 | CsvsNuevos EST0452 | odds_ratio | columna_corrompida_en_el_estudio |  | -> NULL (la mayoria de los valores del estudio tienen el separador de miles corrompido) | 5 |
| 24672 | CsvsNuevos EST0452 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 7088 |
| 24673 | CsvsNuevos EST0452 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 1228 |
| 24674 | CsvsNuevos EST0452 | region_blanco | region_no_es_de_mrna | exon | region_involved_mrna = NULL | 193 |
| 24675 | CsvsNuevos EST0452 | region_blanco | region_no_es_de_mrna | sORF | region_involved_mrna = NULL | 34 |
| 24676 | CsvsNuevos EST0452 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 124 |
| 24677 | CsvsNuevos EST0452 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 51 |
| 24678 | CsvsNuevos EST0453 | fdr | coma_decimal |  | convertida a punto | 3235 |
| 24679 | CsvsNuevos EST0453 | odds_ratio | columna_corrompida_en_el_estudio |  | -> NULL (la mayoria de los valores del estudio tienen el separador de miles corrompido) | 3 |
| 24680 | CsvsNuevos EST0453 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 4150 |
| 24681 | CsvsNuevos EST0453 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 586 |
| 24682 | CsvsNuevos EST0453 | region_blanco | region_no_es_de_mrna | exon | region_involved_mrna = NULL | 82 |
| 24683 | CsvsNuevos EST0453 | region_blanco | region_no_es_de_mrna | sORF | region_involved_mrna = NULL | 39 |
| 24684 | CsvsNuevos EST0453 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 128 |
| 24685 | CsvsNuevos EST0453 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 77 |
| 24686 | CsvsNuevos EST0459 | fdr | coma_decimal |  | convertida a punto | 1224 |
| 24687 | CsvsNuevos EST0459 | n_librerias | valor_no_numerico | U | -> NULL | 370 |
| 24688 | CsvsNuevos EST0459 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1693 |
| 24689 | CsvsNuevos EST0459 | odds_ratio | valor_no_finito | inf | -> NULL | 1 |
| 24690 | CsvsNuevos EST0459 | organismo_especie | molecula_de_otro_organismo | Escherichia virus Lambda | fila descartada | 1 |
| 24691 | CsvsNuevos EST0459 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 58 |
| 24692 | CsvsNuevos EST0459 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 132 |
| 24693 | CsvsNuevos EST0459 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 20 |
| 24694 | CsvsNuevos EST0459 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 6 |
| 24695 | CsvsNuevos EST0460 | fdr | coma_decimal |  | convertida a punto | 1000 |
| 24696 | CsvsNuevos EST0460 | n_librerias | valor_no_numerico | U | -> NULL | 276 |
| 24697 | CsvsNuevos EST0460 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1354 |
| 24698 | CsvsNuevos EST0460 | organismo_especie | molecula_de_otro_organismo | Escherichia virus Lambda | fila descartada | 2 |
| 24699 | CsvsNuevos EST0460 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 44 |
| 24700 | CsvsNuevos EST0460 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 99 |
| 24701 | CsvsNuevos EST0460 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 16 |
| 24702 | CsvsNuevos EST0460 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 7 |
| 24703 | CsvsNuevos EST0461 | fdr | coma_decimal |  | convertida a punto | 1270 |
| 24704 | CsvsNuevos EST0461 | n_librerias | valor_no_numerico | U | -> NULL | 397 |
| 24705 | CsvsNuevos EST0461 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1746 |
| 24706 | CsvsNuevos EST0461 | odds_ratio | valor_no_finito | inf | -> NULL | 1 |
| 24707 | CsvsNuevos EST0461 | organismo_especie | molecula_de_otro_organismo | Escherichia virus Lambda | fila descartada | 126 |
| 24708 | CsvsNuevos EST0461 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 65 |
| 24709 | CsvsNuevos EST0461 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 139 |
| 24710 | CsvsNuevos EST0461 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 18 |
| 24711 | CsvsNuevos EST0461 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 4 |
| 24712 | CsvsNuevos EST0462 | fdr | coma_decimal |  | convertida a punto | 1013 |
| 24713 | CsvsNuevos EST0462 | n_librerias | valor_no_numerico | U | -> NULL | 215 |
| 24714 | CsvsNuevos EST0462 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1362 |
| 24715 | CsvsNuevos EST0462 | organismo_especie | molecula_de_otro_organismo | Escherichia virus Lambda | fila descartada | 107 |
| 24716 | CsvsNuevos EST0462 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 40 |
| 24717 | CsvsNuevos EST0462 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 106 |
| 24718 | CsvsNuevos EST0462 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 17 |
| 24719 | CsvsNuevos EST0462 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 7 |
| 24720 | CsvsNuevos EST0463 | fdr | coma_decimal |  | convertida a punto | 2605 |
| 24721 | CsvsNuevos EST0463 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 3579 |
| 24722 | CsvsNuevos EST0463 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 12 |
| 24723 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 162 |
| 24724 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 247 |
| 24725 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 30 |
| 24726 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 6 |
| 24727 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 20 |
| 24728 | CsvsNuevos EST0463 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 3 |
| 24729 | CsvsNuevos EST0464 | fdr | coma_decimal |  | convertida a punto | 1697 |
| 24730 | CsvsNuevos EST0464 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 2317 |
| 24731 | CsvsNuevos EST0464 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 4 |
| 24732 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 100 |
| 24733 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 207 |
| 24734 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 24 |
| 24735 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 3 |
| 24736 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 19 |
| 24737 | CsvsNuevos EST0464 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24738 | CsvsNuevos EST0465 | fdr | coma_decimal |  | convertida a punto | 1107 |
| 24739 | CsvsNuevos EST0465 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1433 |
| 24740 | CsvsNuevos EST0465 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 12 |
| 24741 | CsvsNuevos EST0465 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 58 |
| 24742 | CsvsNuevos EST0465 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 128 |
| 24743 | CsvsNuevos EST0465 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 7 |
| 24744 | CsvsNuevos EST0465 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 1 |
| 24745 | CsvsNuevos EST0465 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 11 |
| 24746 | CsvsNuevos EST0466 | fdr | coma_decimal |  | convertida a punto | 2969 |
| 24747 | CsvsNuevos EST0466 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 4065 |
| 24748 | CsvsNuevos EST0466 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 29 |
| 24749 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 159 |
| 24750 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 284 |
| 24751 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 26 |
| 24752 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 3 |
| 24753 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 23 |
| 24754 | CsvsNuevos EST0466 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 3 |
| 24755 | CsvsNuevos EST0467 | fdr | coma_decimal |  | convertida a punto | 48 |
| 24756 | CsvsNuevos EST0467 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 50 |
| 24757 | CsvsNuevos EST0467 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 2 |
| 24758 | CsvsNuevos EST0467 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 1 |
| 24759 | CsvsNuevos EST0467 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 4 |
| 24760 | CsvsNuevos EST0467 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 2 |
| 24761 | CsvsNuevos EST0467 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 1 |
| 24762 | CsvsNuevos EST0467 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24763 | CsvsNuevos EST0468 | fdr | coma_decimal |  | convertida a punto | 2866 |
| 24764 | CsvsNuevos EST0468 | odds_ratio | columna_corrompida_en_el_estudio |  | -> NULL (la mayoria de los valores del estudio tienen el separador de miles corrompido) | 2 |
| 24765 | CsvsNuevos EST0468 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 3889 |
| 24766 | CsvsNuevos EST0468 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 30 |
| 24767 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 181 |
| 24768 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 297 |
| 24769 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 22 |
| 24770 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 6 |
| 24771 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 23 |
| 24772 | CsvsNuevos EST0468 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 3 |
| 24773 | CsvsNuevos EST0469 | fdr | coma_decimal |  | convertida a punto | 4004 |
| 24774 | CsvsNuevos EST0469 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 5464 |
| 24775 | CsvsNuevos EST0469 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 31 |
| 24776 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 287 |
| 24777 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 389 |
| 24778 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 31 |
| 24779 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 13 |
| 24780 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 19 |
| 24781 | CsvsNuevos EST0469 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 14 |
| 24782 | CsvsNuevos EST0470 | fdr | coma_decimal |  | convertida a punto | 125 |
| 24783 | CsvsNuevos EST0470 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 139 |
| 24784 | CsvsNuevos EST0470 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 3 |
| 24785 | CsvsNuevos EST0470 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 2 |
| 24786 | CsvsNuevos EST0470 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 7 |
| 24787 | CsvsNuevos EST0470 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 4 |
| 24788 | CsvsNuevos EST0470 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 10 |
| 24789 | CsvsNuevos EST0470 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24790 | CsvsNuevos EST0471 | fdr | coma_decimal |  | convertida a punto | 108 |
| 24791 | CsvsNuevos EST0471 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 126 |
| 24792 | CsvsNuevos EST0471 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 1 |
| 24793 | CsvsNuevos EST0471 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 2 |
| 24794 | CsvsNuevos EST0471 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 10 |
| 24795 | CsvsNuevos EST0471 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 2 |
| 24796 | CsvsNuevos EST0471 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 2 |
| 24797 | CsvsNuevos EST0471 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24798 | CsvsNuevos EST0472 | fdr | coma_decimal |  | convertida a punto | 177 |
| 24799 | CsvsNuevos EST0472 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 210 |
| 24800 | CsvsNuevos EST0472 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 4 |
| 24801 | CsvsNuevos EST0472 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 23 |
| 24802 | CsvsNuevos EST0472 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 5 |
| 24803 | CsvsNuevos EST0472 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 3 |
| 24804 | CsvsNuevos EST0472 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 2 |
| 24805 | CsvsNuevos EST0473 | fdr | coma_decimal |  | convertida a punto | 22 |
| 24806 | CsvsNuevos EST0473 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 28 |
| 24807 | CsvsNuevos EST0473 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 1 |
| 24808 | CsvsNuevos EST0473 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 5 |
| 24809 | CsvsNuevos EST0473 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 1 |
| 24810 | CsvsNuevos EST0474 | fdr | coma_decimal |  | convertida a punto | 27 |
| 24811 | CsvsNuevos EST0474 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 31 |
| 24812 | CsvsNuevos EST0474 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 5 |
| 24813 | CsvsNuevos EST0474 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 1 |
| 24814 | CsvsNuevos EST0474 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 1 |
| 24815 | CsvsNuevos EST0475 | fdr | coma_decimal |  | convertida a punto | 1299 |
| 24816 | CsvsNuevos EST0475 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1776 |
| 24817 | CsvsNuevos EST0475 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 17 |
| 24818 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 197 |
| 24819 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 228 |
| 24820 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 16 |
| 24821 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 8 |
| 24822 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 10 |
| 24823 | CsvsNuevos EST0475 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 66 |
| 24824 | CsvsNuevos EST0476 | fdr | coma_decimal |  | convertida a punto | 68 |
| 24825 | CsvsNuevos EST0476 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 100 |
| 24826 | CsvsNuevos EST0476 | odds_ratio | valor_no_finito | #NUM! | -> NULL | 2 |
| 24827 | CsvsNuevos EST0476 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 5 |
| 24828 | CsvsNuevos EST0476 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 19 |
| 24829 | CsvsNuevos EST0476 | region_blanco | region_no_es_de_mrna | other-ncRNA | region_involved_mrna = NULL | 3 |
| 24830 | CsvsNuevos EST0476 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 3 |
| 24831 | CsvsNuevos EST0478 | enriquecimiento_log2 | ambiguo_separador_de_miles |  | -> NULL (tres decimales: puede ser un separador de miles) | 200 |
| 24832 | CsvsNuevos EST0479 | enriquecimiento_log2 | ambiguo_separador_de_miles |  | -> NULL (tres decimales: puede ser un separador de miles) | 273 |
| 24833 | CsvsNuevos EST0480 | enriquecimiento_log2 | ambiguo_separador_de_miles |  | -> NULL (tres decimales: puede ser un separador de miles) | 424 |
| 24834 | CsvsNuevos EST0481 | fdr | coma_decimal |  | convertida a punto | 2 |
| 24835 | CsvsNuevos EST0481 | odds_ratio | valor_no_finito | inf | -> NULL | 36 |
| 24836 | CsvsNuevos EST0481 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 6 |
| 24837 | CsvsNuevos EST0481 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 2 |
| 24838 | CsvsNuevos EST0481 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 3 |
| 24839 | CsvsNuevos EST0482 | fdr | coma_decimal |  | convertida a punto | 32 |
| 24840 | CsvsNuevos EST0482 | odds_ratio | coma_decimal |  | convertida a punto | 8 |
| 24841 | CsvsNuevos EST0482 | odds_ratio | valor_no_finito | inf | -> NULL | 770 |
| 24842 | CsvsNuevos EST0482 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 95 |
| 24843 | CsvsNuevos EST0482 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 32 |
| 24844 | CsvsNuevos EST0482 | region_blanco | region_no_es_de_mrna | rRNA | region_involved_mrna = NULL | 48 |
| 24845 | CsvsNuevos EST0482 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 282 |
| 24846 | CsvsNuevos EST0483 | fdr | coma_decimal |  | convertida a punto | 118 |
| 24847 | CsvsNuevos EST0483 | odds_ratio | coma_decimal |  | convertida a punto | 5 |
| 24848 | CsvsNuevos EST0483 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 1 |
| 24849 | CsvsNuevos EST0483 | odds_ratio | valor_no_finito | inf | -> NULL | 871 |
| 24850 | CsvsNuevos EST0483 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 183 |
| 24851 | CsvsNuevos EST0483 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 115 |
| 24852 | CsvsNuevos EST0483 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 99 |
| 24853 | CsvsNuevos EST0484 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 148 |
| 24854 | CsvsNuevos EST0484 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 219 |
| 24855 | CsvsNuevos EST0484 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 48 |
| 24856 | CsvsNuevos EST0484 | region_blanco | region_no_es_de_mrna | tRNA | region_involved_mrna = NULL | 75 |
| 24857 | CsvsNuevos EST0485 | enriquecimiento_log2 | ambiguo_separador_de_miles |  | -> NULL (tres decimales: puede ser un separador de miles) | 7 |
| 24858 | CsvsNuevos EST0486 | enriquecimiento_log2 | ambiguo_separador_de_miles |  | -> NULL (tres decimales: puede ser un separador de miles) | 34 |
| 24859 | CsvsNuevos EST0487 | fdr | coma_decimal |  | convertida a punto | 123 |
| 24860 | CsvsNuevos EST0487 | region_blanco | region_no_es_de_mrna | AS | region_involved_mrna = NULL | 61 |
| 24861 | CsvsNuevos EST0487 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 31 |
| 24862 | CsvsNuevos EST0487 | region_blanco | region_no_es_de_mrna | sRNA | region_involved_mrna = NULL | 17 |
| 24863 | CsvsNuevos EST0488 | fdr | coma_decimal |  | convertida a punto | 239 |
| 24864 | CsvsNuevos EST0489 | fdr | coma_decimal |  | convertida a punto | 296 |
| 24865 | CsvsNuevos EST0489 | n_librerias | valor_no_numerico | U | -> NULL | 1 |
| 24866 | CsvsNuevos EST0489 | odds_ratio | separador_de_miles_corrompido |  | -> NULL (la coma decimal se perdio; el valor no es recuperable) | 2800 |
| 24867 | CsvsNuevos EST0489 | region_blanco | region_no_es_de_mrna | IGR | region_involved_mrna = NULL | 468 |
