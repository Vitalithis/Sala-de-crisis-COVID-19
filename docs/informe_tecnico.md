# Informe Técnico · Sala de Crisis COVID-19 (IN1232C)

**Equipo:** Nicolás Urrutia (Rol A), Dan Ocampo (Rol B), Cristian (Rol C), Leo (Rol D)  
**Período analizado:** 22 de enero de 2020 al 9 de marzo de 2023 (1.143 días)

---

## 1. Introducción y encargo

El 10 de marzo de 2023, la Universidad Johns Hopkins (JHU CSSE) archivó su repositorio mundial de seguimiento de COVID-19 tras tres años de registro diario continuo. Ante el Comité Asesor de Preparación Pandémica, el equipo diseñó e implementó una plataforma de datos reproducible de extremo a extremo capaz de:
1. Unificar los 1.143 reportes diarios históricos (cinco cambios de esquema) junto con fuentes externas de vacunación y demografía en un Data Warehouse analítico.
2. Medir la calidad y confiabilidad de los datos bajo seis dimensiones y aplicar control de divulgación conforme a la normativa chilena.
3. Responder con evidencia empírica siete preguntas clave (P1 a P7) y operar un tablero interactivo en Streamlit con pronósticos y alertas tempranas en vivo sin fuga de datos.

## 2. Arquitectura y capas; CSV frente a Parquet; motor elegido

El pipeline se organiza en tres capas reproducibles mediante `src/01_ingesta_y_unificacion.py` y `src/02_construir_dw.py`:
- **Capa cruda (`data/raw/`):** descarga paralela de los `1.143` CSV diarios de JHU, las series globales, la tabla maestra `UID_ISO_FIPS_LookUp_Table.csv`, vacunación de **Our World in Data (OWID)** e indicadores demográficos del **Banco Mundial** (excluida de Git por tamaño y reproducibilidad).
- **Capa limpia (`data/clean/reportes_unificados.parquet`):** unificación de los 5 esquemas en `snake_case`, fechas ISO (`AAAA-MM-DD`), construcción de `combined_key` para etapas tempranas y normalización de nombres de país.
- **Capa analítica (`data/dw_covid.duckdb`):** Data Warehouse en estrella consultado por análisis, modelos y tablero.

**Comparación real CSV vs. Parquet:** los `1.143` archivos CSV originales ocupan **559,87 MB** y demoran aproximadamente **43,80 s** en leerse; el archivo único `reportes_unificados.parquet` (`4.287.473` filas) ocupa **96,07 MB** (**82,8 %** menos almacenamiento) y se lee completo en **7,44 s** (**5,9x** más rápido).

**Justificación del motor elegido frente a NoSQL:** tras la unificación, los datos son estrictamente tabulares con esquema fijo y requieren integridad referencial, funciones ventana (`LAG`) y agregaciones OLAP (`JOIN`, `GROUP BY`). DuckDB (motor SQL columnar embebido, equivalente en diseño relacional a PostgreSQL) ejecuta estas consultas en milisegundos directamente sobre Parquet, mientras bases NoSQL documentales (MongoDB) o columnares anchas para escritura masiva (Cassandra) no optimizan cruces analíticos multidimensionales ni agregaciones ad-hoc. Su equivalente en la nube (S3/GCS + Cloud Run + RDS PostgreSQL/MotherDuck) se estima en **USD 16,50–20,50/mes** (ver `docs/arquitectura.md`).

## 3. Calidad de datos: reglas, problemas cuantificados, índice y decisiones

Bajo el principio **corregir, marcar o excluir; nunca imputar**, se ejecutaron reglas automatizadas sobre las seis dimensiones de calidad (`src/03_calidad_y_olap.py` y `src/calidad/reglas.py`) aplicadas a las `4.287.467` filas de `fact_covid`:

| Dimensión | Regla evaluada | Filas afectadas | Porcentaje | Umbral | Estado |
|---|---|---:|---:|---:|---|
| Completitud | Territorios sin población en UID | 101.775 | 2,3738 % | 5,00 % | OK |
| Unicidad | Duplicados `(fecha × territorio)` en crudo | 6 | 0,0001 % | 0,01 % | OK |
| Validez | Acumulados negativos o coordenadas fuera de rango | 6 | 0,0001 % | 0,10 % | OK |
| Consistencia | Fallecidos mayores que confirmados | 10.777 | 0,2514 % | 0,05 % | RECHAZA |
| Exactitud | Días con acumulado que retrocede | 44.582 | 1,0398 % | 1,00 % | ALERTA |
| Exactitud | Picos bruscos por acumulación de rezagos | 11.354 | 0,2648 % | 0,50 % | OK |
| Oportunidad | Días sin reporte (`0` nuevos en 2022-2023, >100k acum.) | 19.068 | 0,4447 % | 1,00 % | OK |

Adicionalmente, el cruce al `2023-03-09` entre `time_series` y la suma de reportes diarios arrojó **0 países con diferencia** tras normalizar nombres; se marcaron `27` entidades especiales (`24.283` filas), se preservó el cambio de granularidad de Chile (`16` regiones desde `2020-05-20`) y se excluyó `recovered` tras su discontinuación en agosto de 2021. El linaje completo desde `fact_covid` hasta el CSV diario origen y todas las decisiones se detallan en `docs/decisiones_calidad.md`.

## 4. Modelo de datos: estrella, grano, integración con OWID y Banco Mundial, OLAP

- **Esquema en estrella y grano:** `fact_covid` tiene grano **territorio × día** (`4.287.467` filas tras consolidar 6 duplicados del crudo), vinculada a `dim_fecha` (`1.143` días) y `dim_territorio` (`4.413` territorios con jerarquía `pais -> region_estado -> condado`, `nivel_granularidad` y `es_entidad_especial`).
- **Fuentes externas integradas por código ISO3:**
  1. **OWID vacunación (`fact_vacunacion`):** cruza `189` de `248` países/entidades de `dim_territorio` (**76,2 %** sobre el total incluyendo entidades especiales y variantes de nombre históricas; **91,1 %** sobre los `236` códigos `iso3` presentes en `dim_territorio`). Los no cruzados corresponden a cruceros/entidades sin ISO3 (*Diamond Princess*, *Antarctica*), microestados o denominaciones históricas previas a la normalización.
  2. **Banco Mundial (`dim_indicadores_wb`):** incorpora `% población >= 65 años` (`SP.POP.65UP.TO.ZS`) y `PIB per cápita` (`NY.GDP.PCAP.CD`), cruzando `193` entidades (**77,8 %**).
- **Consultas OLAP sobre DuckDB:** ejecutadas directamente sobre la estrella (`roll-up` anual/trimestral global, `slice` de Chile por año y `drill-down + dice` por regiones de Chile en invierno 2021).

## 5. Resultados P1 a P7

- **P1 · Chile frente a Sudamérica (D):** al `2023-03-09`, Chile registró **27.161,7 casos/100k** (2.° en Sudamérica tras Uruguay `29.775,0`) y **336,2 fallecidos/100k** (2.° tras Perú `665,8`). Experimentó 4 olas principales: mayo–julio 2020 (pico `2020-06-17`), febrero–mayo 2021 (pico `2021-04-14`), ómicron en enero–febrero 2022 (pico `2022-02-13`, la mayor en contagios diarios) e invierno 2022 (pico `2022-06-17`). Ver `docs/figuras/p1_sudamerica.png`.
- **P2 · Regiones de Chile y Biobío (D):** desde junio de 2020, Magallanes lidera en incidencia (`40.624,4/100k`) y mortalidad (`464,8/100k`), seguida en mortalidad por la Región Metropolitana (`434,0/100k`). **Biobío** se ubicó en el puesto **#9 en casos/100k** (`32.806,3`) y **#10 en fallecidos/100k** (`309,9`). Ver `docs/figuras/p2_regiones_chile.png`.
- **P3 · Letalidad aparente mensual vs. vacunación completa (B):** comparando medianas mensuales antes vs. después del `50 %` de vacunación completa (OWID): **Chile** bajó de `2,10 %` a `0,64 %`; **Argentina** de `2,30 %` a `0,41 %`; **Perú** de `7,56 %` a `1,56 %`; y **Uruguay** de `1,73 %` a `0,46 %` (interpretación sujeta a intensidad de testeo y menor letalidad intrínseca de ómicron). Ver `docs/figuras/p3_letalidad_vacunacion.png`.
- **P4 · Índice de calidad por país (B):** en escala `0–100`, los 10 peores registros son `US` (`0,00`), `United Kingdom` (`34,91`), `Iran (Islamic Republic of)` (`50,04`), `Republic of Korea` (`50,04`), `South Korea` (`52,10`), `Tanzania` (`52,60`), `Congo (Brazzaville)` (`56,58`), `Nicaragua` (`56,94`), `Benin` (`57,37`) y `Cameroon` (`57,72`). En EE. UU. y Reino Unido pesan inconsistencias `deaths > confirmed` en registros subnacionales/`Unknown`; en países africanos y Nicaragua, cientos de días sin cambio de reporte. Se conservan marcados y se suaviza con MM7.
- **P5 · Segmentación K-Means de países (C):** con 4 clusters estandarizados sobre `167` países (`>= 500k` hab.) por casos/100k, fallecidos/100k, letalidad y vacunación máxima: **Chile** integra el grupo de alta carga epidémica y alta vacunación (`49` países, media `37.347,6` casos/100k, `280,6` fallecidos/100k, `65,0 %` vacunación), junto a EE. UU., España, Bélgica y Países Bajos; otros dos grupos agrupan carga moderada con alta vacunación (`61` países) y baja incidencia/vacunación (`56` países), más un atípico (`Yemen`, `18,1 %` letalidad).
- **P6 · Ómicron en Chile, corte dic-2021 (C):** al `2021-12-28`, los tres modelos univariados obtuvieron errores elevados ante la irrupción abrupta de ómicron (`Base MM7` MAPE `29,2 %`, `Holt` `32,8 %`, `ARIMA` `37,0 %`), confirmando que no es anticipable solo con casos previos. Sin embargo, `alerta()` se activó el `2022-01-03`, **41 días antes** del pico (`2022-02-13`).
- **P7 · Vacunación dic-2021 vs. mortalidad 2022 y factor de confusión demográfico (B):** sobre `n = 151` países (`>= 1M` hab.), se obtuvo correlación positiva `r = 0,488`. Al cruzar con `% población >= 65 años` (Banco Mundial), se verifica un claro factor de confusión: la edad avanzada correlaciona fuertemente con mortalidad 2022 (`r = 0,795`) y con cobertura vacunal (`r = 0,610`). **Correlación no implica causalidad.** Ver `docs/figuras/p7_vacunacion_vs_mortalidad.png`.

## 6. Minería y predicción: segmentación, pronóstico, backtesting y alerta

La función `pronosticar(territorio, fecha_corte, horizonte=14)` filtra estrictamente `fecha <= fecha_corte` (sin fuga de datos) y compara **tres modelos**: `Base (MM7)`, `Holt amortiguado` y `ARIMA(1,1,1)`. Resultados del backtesting en Chile (horizonte 14 días):

| Fecha de corte | Escenario | Base (MM7) MAE / MAPE | Holt MAE / MAPE | ARIMA(1,1,1) MAE / MAPE |
|---|---|---:|---:|---:|
| `2021-03-15` | Ola 2 (otoño 2021) | 1.094,1 / 17,9 % | 650,5 / 10,5 % | **414,7 / 6,7 %** |
| `2021-12-28` | P6 · Inicio Ómicron | **716,3 / 29,2 %** | 783,8 / 32,8 % | 864,9 / 37,0 % |
| `2022-05-15` | Ola invierno 2022 | 2.890,3 / 44,0 % | 1.822,6 / 26,2 % | **1.631,9 / 23,3 %** |

La función `alerta(territorio, fecha)` (`incidencia 7d >= 35,0 c/100k` y `variación semanal >= 25,0 %`) anticipó **44 días** la Ola 1, **41 días** Ómicron y **39 días** la ola de invierno 2022, con `149` días activos y `29` falsas alarmas (`19,5 %`) en toda la serie de Chile.

## 7. Protección de datos y ética

En el marco de la **Ley N.° 19.628** y la **Ley N.° 21.719**, los registros de JHU y OWID son conteos agregados por territorio sin identificadores directos, por lo que no constituyen datos personales ni sensibles de salud. No obstante, conteos entre `1` y `4` en poblaciones pequeñas implican riesgo de reidentificación indirecta. En el tablero (`dashboard/app.py`) se suprimen como `<5 (suprimido R6)` cuando la población es `< 50.000` hab. (`2.250` territorios). En la medición estricta sobre `316` condados de EE. UU. con `< 5.000` hab. (`src/proteccion/supresion.py`), la pérdida de información es solo **1,792 %** en casos (`61.504` de `3.432.447` celdas) y **0,102 %** en fallecidos (`3.515`).

## 8. Tablero

Construido en **Streamlit** (`dashboard/app.py`) conectado a DuckDB en cuatro pestañas: **1) Panorama y Tendencias** (alerta temprana, KPIs con supresión R6, MM7 y avance de vacunación), **2) Mapas Mundial y Chile** (mapas georreferenciados estáticos, rankings y mapa mundial animado mes a mes), **3) Desafío en Vivo** (`pronosticar()` con 3 modelos y `alerta()` sin fuga, comparación real con MAE/MAPE y detalle día a día) y **4) Calidad y Segmentación** (disposición vertical `1x4` con reglas R2, Top 10 P4, perfiles K-Means y backtesting).

## 9. Limitaciones

1. Los casos confirmados y la letalidad aparente dependen de la capacidad de testeo y criterios de registro de cada país.
2. No se integran datos genómicos ni de movilidad, por lo que los modelos univariados no anticipan cambios bruscos de variante como ómicron.
3. JHU discontinuó `recovered` y `active` en agosto de 2021 y varios países pasaron a reporte semanal desde 2022.
4. La granularidad de Chile cambia de nacional a 16 regiones el `2020-05-20`, impidiendo comparaciones regionales previas a esa fecha.
