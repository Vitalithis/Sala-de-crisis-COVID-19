# Decisiones de calidad (R2)

Regla del curso: corregir, marcar o excluir. **Imputar es inventar.**

Sobre la tabla de hechos del Data Warehouse (`fact_covid`, 4.287.467 filas y 4.413 territorios) y la capa unificada (`reportes_unificados.parquet`), se cuantificaron y documentaron los nueve problemas estructurales de los datos de Johns Hopkins CSSE:

| # | Problema | Cuántos casos (cuantificado) | Decisión | Justificación | Dónde se aplica |
|---|---|---|---|---|---|
| 1 | Acumulado que retrocede | 44.582 filas (1,0398 %) en 170 países/entidades | Marcar (`retrocede_casos`, `retrocede_muertes`) | Los retrocesos corresponden a correcciones oficiales retrospectivas de los ministerios de salud. No se imputan ni se suavizan; en cálculos de variación diaria se acota con `GREATEST(casos_nuevos, 0)` | `src/02_construir_dw.py` (`fact_covid`) |
| 2 | Días sin reporte (reportes semanales en 2022-2023) | 19.068 días-país (0,4447 %) en 122 países con >100.000 acumulados | Marcar y usar media móvil 7 días | A partir de 2022 varios países pasaron a reportar semanalmente, generando ceros artificiales entre semana. No se imputan días sin reporte; se usa MM7 para análisis y pronóstico | `src/03_calidad_y_olap.py` y `src/04_modelos_y_alerta.py` |
| 3 | Picos por acumulación de rezagos | 11.354 filas (0,2648 %) con `casos_nuevos > 5x` media móvil 14d y `> 500` casos | Marcar y amortiguar visualmente con MM7 | Reflejan cargas masivas de casos rezagados en un solo día. Se conservan los datos reales en el DW y se usa media móvil de 7 días para evitar distorsión de tendencias | `src/03_calidad_y_olap.py` y `dashboard/app.py` |
| 4 | Fallecidos mayores que confirmados | 10.777 filas (0,2514 %) en 10 países (principalmente EE. UU. y Reino Unido) | Marcar y alertar (`RECHAZA` en regla de consistencia) | Ocurre en registros subnacionales o asignaciones `Unknown` donde se registran defunciones sin el correspondiente caso asignado al mismo territorio | `src/03_calidad_y_olap.py` (`reglas_calidad.csv`) |
| 5 | Diferencia entre `time_series` y suma de `daily_reports` | 0 países con diferencia > 0 al cierre (`2023-03-09`) tras normalizar nombres | Validar por conciliación | Al unificar los nombres de país y sumar los reportes diarios al último corte, los totales coinciden con `confirmed_global.csv` | `src/03_calidad_y_olap.py` |
| 6 | Entidades especiales (Diamond Princess, MS Zaandam, Olimpiadas, Antarctica) | 24.283 filas en 27 territorios | Marcar (`es_entidad_especial = TRUE`) y excluir en rankings nacionales | No son países ni divisiones administrativas con población estable; incluirlos distorsiona tasas por 100.000 hab. y rankings | `src/02_construir_dw.py` (`dim_territorio`) |
| 7 | Nombres de país inconsistentes (`Mainland China`, `Korea, South`, `Taiwan*`, etc.) | 5 esquemas históricos con denominaciones heterogéneas | Corregir mediante diccionario canónico (`NORMALIZAR_PAIS`) | Permite consolidar la serie continua por país sin fragmentar China, Corea del Sur, Taiwán, Irán o Rusia entre etapas | `src/01_ingesta_y_unificacion.py` y `src/ingesta/unificar.py` |
| 8 | Chile nacional hasta mayo 2020 y regional después | 16 regiones desde `2020-05-20` hasta `2023-03-09` | Mantener ambas granularidades en `dim_territorio` (`nivel_granularidad`) y advertir | JHU reportó a Chile agregado a nivel país al inicio y desagregado en 16 regiones desde fines de mayo de 2020. No se interpola retroactivamente | `src/02_construir_dw.py` y `dashboard/app.py` |
| 9 | Recuperados sin actualizar desde agosto 2021 | 2.332.426 filas posteriores al `2021-08-05` (4.287.467 nulos/descontinuados en DW) | Excluir de indicadores activos y documentar | JHU dejó de actualizar `recovered` y `active` en agosto de 2021. Se conserva la columna solo por trazabilidad histórica y no se usa en KPIs | `docs/diccionario_datos.md` |

## Índice de calidad por país (P4)

Para responder a **P4**, se construyó un índice compuesto en escala `0` a `100` (donde `100` representa ausencia total de anomalías) sobre países con al menos `1.000` casos confirmados acumulados:

$$\text{Índice} = \text{clip}_{[0, 100]}\Big(100 - 3{,}0 \cdot \%_{\text{retrocede}} - 0{,}5 \cdot \%_{\text{sin cambio}} - 5{,}0 \cdot \%_{\text{inconsistente}} - 0{,}5 \cdot \%_{\text{días faltantes}}\Big)$$

Donde:
- **Peso `5,0` (`dias_inconsistentes`)**: penaliza con mayor severidad los días donde `deaths > confirmed`, por ser una violación lógica directa de consistencia.
- **Peso `3,0` (`dias_retrocede`)**: penaliza retrocesos en el acumulado diario (`casos_nuevos < 0`), que rompen la monotonicidad esperada de una serie acumulada.
- **Peso `0,5` (`dias_sin_cambio`)**: penaliza días con `casos_nuevos = 0` teniendo `confirmed > 100` (reportes intermitentes o semanales).
- **Peso `0,5` (`dias_faltantes`)**: penaliza la falta de cobertura respecto a los `1.143` días totales de la serie (`2020-01-22` a `2023-03-09`).

### Top 10 países con peor índice de calidad (según `data/clean/indice_calidad_paises.csv`)

| Puesto | País / Registro | Días reportados | Días retrocede | Días sin cambio | Días inconsistentes (`deaths > confirmed`) | Índice |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `US` | 1.143 | 3 | 0 | 1.083 | 0,00 |
| 2 | `United Kingdom` | 1.143 | 5 | 128 | 133 | 34,91 |
| 3 | `Iran (Islamic Republic of)` | 1 | 0 | 0 | 0 | 50,04 |
| 4 | `Republic of Korea` | 1 | 0 | 0 | 0 | 50,04 |
| 5 | `South Korea` | 48 | 0 | 0 | 0 | 52,10 |
| 6 | `Tanzania` | 1.089 | 0 | 981 | 0 | 52,60 |
| 7 | `Congo (Brazzaville)` | 1.090 | 1 | 890 | 0 | 56,58 |
| 8 | `Nicaragua` | 1.086 | 0 | 881 | 0 | 56,94 |
| 9 | `Benin` | 1.089 | 1 | 871 | 0 | 57,37 |
| 10 | `Cameroon` | 1.099 | 1 | 881 | 0 | 57,72 |

**Interpretación y decisión:**
- **`US` (0,00) y `United Kingdom` (34,91)** caen al fondo del ranking principalmente por inconsistencias `deaths > confirmed` en registros subnacionales o categorías `Unknown` (1.083 días en EE. UU. y 133 en Reino Unido).
- **`Iran (Islamic Republic of)`, `Republic of Korea` y `South Korea`** aparecen con pocos días reportados porque corresponden a denominaciones previas al mapeo canónico en los primeros esquemas de 2020.
- **`Tanzania`, `Congo (Brazzaville)`, `Nicaragua`, `Benin` y `Cameroon`** presentan entre 871 y 981 días sin cambio reportado (reportes muy espaciados o interrumpidos).
- **Decisión operativa:** No se eliminan ni imputan estos países; se marcan en el DW, se muestra esta tabla en la pestaña de Calidad del tablero y se exige usar media móvil de 7 días para comparaciones temporales.

## Linaje de datos (R2 · Nivel excelente)

Cualquier cifra mostrada en el tablero o en las respuestas P1–P7 es completamente trazable hasta su archivo y fila de origen siguiendo la cadena de tres saltos:

1. **Tablero / Consultas OLAP -> `fact_covid` (`data/dw_covid.duckdb`):** cada registro se identifica de forma única por `(fecha_key, territorio_key)`. La columna `esquema` indica la etapa original (`1` a `5`).
2. **`fact_covid` -> `reportes_unificados.parquet` (`data/clean/`):** `fecha_key` (`YYYYMMDD`) mapea 1:1 a `fecha_reporte` (`YYYY-MM-DD`) y `territorio_key` mapea 1:1 a `dim_territorio.combined_key`.
3. **`reportes_unificados.parquet` -> CSV crudo de origen (`data/raw/daily_reports/`):** el archivo exacto es `MM-DD-AAAA.csv` (derivado de `fecha_reporte`) y la fila corresponde a la tupla `(combined_key)` (o `(Province/State, Country/Region)` en esquemas 1 y 2).

Ejemplo verificable en SQL sobre DuckDB para rastrear el registro de Biobío al `2021-12-28`:
```sql
SELECT f.fecha_key, t.combined_key, f.esquema, f.confirmed, f.deaths
FROM fact_covid f
JOIN dim_territorio t ON f.territorio_key = t.territorio_key
WHERE t.country_region = 'Chile' AND t.province_state = 'Biobio' AND f.fecha_key = 20211228;
-- Origen exacto: data/raw/daily_reports/12-28-2021.csv, fila Combined_Key = 'Biobio, Chile'.
```

