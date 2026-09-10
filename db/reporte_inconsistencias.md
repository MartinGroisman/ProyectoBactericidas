# Reporte de normalizacion

Origen: `Full_data_set_en uso.csv` (32677 filas x 52 columnas)

## Filas por tabla

| Tabla | Filas |
|---|---:|
| phylum | 7 |
| genus | 34 |
| species | 46 |
| strain | 72 |
| genome | 74 |
| replicon | 99 |
| sequence | 32744 |
| rna | 14027 |
| rna_sequence | 11008 |
| rna_synonym | 9928 |
| rna_locus | 4253 |
| technique | 8 |
| experimental_method | 37 |
| regulation_type | 2 |
| publication | 112 |
| genome_publication | 126 |
| interaction | 29656 |
| interaction_evidence | 32538 |
| binding_site | 35813 |
| study | 39556 |
| qc_issue | 24490 |

## Inconsistencias detectadas (153088 celdas afectadas)

| Tipo | Casos |
|---|---:|
| booleano_es_a_entero | 87476 |
| token_nulo | 39869 |
| span_no_coincide_con_la_secuencia | 18066 |
| cita_bibliografica_en_columna_numerica | 3063 |
| longitud_declarada_vs_secuencia | 1374 |
| molecula_con_varias_secuencias | 690 |
| variante_de_mayusculas | 648 |
| secuencia_normalizada | 635 |
| atributo_booleano_contradictorio | 335 |
| accesiones_multiples_en_una_celda | 329 |
| hebra_invalida | 171 |
| fila_duplicada_exacta | 139 |
| valor_contradictorio_en_la_misma_molecula | 86 |
| residuo_json | 73 |
| conteo_declarado_incorrecto | 50 |
| encoding_artifact | 45 |
| genoma_sin_accesion | 18 |
| rango_en_una_celda | 12 |
| auto_interaccion | 3 |
| cepa_con_varios_ensamblados | 2 |
| secuencia_invalida | 1 |
| molecula_sin_nombre_ni_id_ncbi | 1 |
| genoma_nuevo_sin_publicacion | 1 |
| biotipo_faltante_completado | 1 |

## Conversiones sistematicas (agregadas)

| Columna | Tipo | Valor original | Accion | Casos |
|---|---|---|---|---:|
| None | token_nulo | `NA` | -> NULL | 37037 |
| rna_plasmid_derived | booleano_es_a_entero | `FALSO` | -> 0 | 28963 |
| rna_antisense | booleano_es_a_entero | `FALSO` | -> 0 | 28805 |
| rna_ESTUTR | booleano_es_a_entero | `FALSO` | -> 0 | 28781 |
| rna_biotype_name | token_nulo | `NA` | -> NULL | 946 |
| small_rna_sequence | secuencia_normalizada | `` | trim / mayusculas | 635 |
| small_rna_start_coordinates | token_nulo | `#N/D` | -> NULL | 606 |
| rna_name | variante_de_mayusculas | `cpxP / CpxP` | se conserva 'cpxP'; rna_name_key unifica | 488 |
| rna_ESTUTR | booleano_es_a_entero | `VERDADERO` | -> 1 | 377 |
| rna_antisense | booleano_es_a_entero | `VERDADERO` | -> 1 | 355 |
| rna_sequence | token_nulo | `#N/D` | -> NULL | 336 |
| small_rna_end_coordinates | token_nulo | `#N/D` | -> NULL | 303 |
| small_rna_length | token_nulo | `#N/D` | -> NULL | 303 |
| small_rna_strand | token_nulo | `#N/D` | -> NULL | 303 |
| rna_plasmid_derived | booleano_es_a_entero | `VERDADERO` | -> 1 | 195 |
| rna_name | variante_de_mayusculas | `sucD / SucD` | se conserva 'sucD'; rna_name_key unifica | 84 |
| rna_name | variante_de_mayusculas | `raiA / RaiA` | se conserva 'raiA'; rna_name_key unifica | 39 |
| rna_start_coordinates | token_nulo | `#N/D` | -> NULL | 20 |
| rna_name | variante_de_mayusculas | `gadE / GadE` | se conserva 'gadE'; rna_name_key unifica | 12 |
| rna_end_coordinates | token_nulo | `#N/D` | -> NULL | 10 |
| rna_name | variante_de_mayusculas | `ssrA / SsrA` | se conserva 'ssrA'; rna_name_key unifica | 7 |
| rna_name | variante_de_mayusculas | `ybdK / YbdK` | se conserva 'ybdK'; rna_name_key unifica | 6 |
| DeltaG | token_nulo | `None` | -> NULL | 5 |
| rna_name | variante_de_mayusculas | `RnpB / rnpB` | se conserva 'RnpB'; rna_name_key unifica | 3 |
| rna_name | variante_de_mayusculas | `SsrS / ssrS` | se conserva 'SsrS'; rna_name_key unifica | 3 |
| rna_name | variante_de_mayusculas | `ompX / OmpX` | se conserva 'ompX'; rna_name_key unifica | 2 |
| rna_name | variante_de_mayusculas | `SAspA / SaspA` | se conserva 'SAspA'; rna_name_key unifica | 1 |
| rna_name | variante_de_mayusculas | `RdlA / rdlA` | se conserva 'RdlA'; rna_name_key unifica | 1 |
| rna_name | variante_de_mayusculas | `pspG / PspG` | se conserva 'pspG'; rna_name_key unifica | 1 |
| rna_name | variante_de_mayusculas | `Ffs / ffs` | se conserva 'Ffs'; rna_name_key unifica | 1 |
| rna_biotype_name | biotipo_faltante_completado | `sRNA` | 355 moleculas marcadas como sRNA por su rol | 1 |

Detalle fila por fila en `db/csv/qc_issue.csv` y en la tabla `qc_issue`.
