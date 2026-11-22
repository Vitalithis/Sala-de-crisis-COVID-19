# Diccionario de Datos · Tabla Unificada (`reportes_unificados.parquet`)

Tabla consolidada a partir de los 1.143 reportes diarios de Johns Hopkins CSSE (4.287.473 filas), unificando los 5 esquemas históricos en formato `snake_case` y fechas ISO (`AAAA-MM-DD`).

| Columna | Significado | Tipo | Dominio / Valores permitidos | Origen | Existe desde |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fecha_reporte` | Fecha del reporte diario extraída del nombre del archivo | string (ISO) | `2020-01-22` a `2023-03-09` | Generada en ETL | 2020-01-22 (Etapa 1) |
| `esquema` | Versión del esquema original del CSV fuente | int | Entero `1` a `5` | Generada en ETL | 2020-01-22 (Etapa 1) |
| `fips` | Código federal de condado de EE. UU. | string | 5 dígitos o nulo | JHU Daily Reports | 2020-03-22 (Etapa 3) |
| `admin2` | Nombre del condado o división administrativa nivel 2 | string | Texto libre o nulo | JHU Daily Reports | 2020-03-22 (Etapa 3) |
| `province_state` | Región, provincia o estado (incluye 16 regiones de Chile desde fines de mayo 2020) | string | Texto libre o nulo | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `country_region` | País o entidad especial (ej. `Chile`, `Diamond Princess`) | string | Texto (`Mainland China` normalizado a `China`) | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `combined_key` | Llave compuesta `admin2, province_state, country_region` | string | No nulo (construida en etapas 1–2) | JHU / ETL | 2020-03-22 (Etapa 3) |
| `last_update` | Marca de tiempo en que JHU actualizó el registro | string | Timestamps heterogéneos | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `lat` | Latitud geográfica del territorio | float | `[-90.0, 90.0]` o nulo | JHU Daily Reports | 2020-03-01 (Etapa 2) |
| `long` | Longitud geográfica del territorio | float | `[-180.0, 180.0]` o nulo | JHU Daily Reports | 2020-03-01 (Etapa 2) |
| `confirmed` | Casos confirmados acumulados a la fecha | float | `>= 0` (algunos retrocesos marcados en DW) | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `deaths` | Fallecidos acumulados a la fecha | float | `>= 0` (inconsistencias `deaths > confirmed` marcadas) | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `recovered` | Recuperados acumulados (dejó de actualizarse en ago-2021) | float | `>= 0` o nulo | JHU Daily Reports | 2020-01-22 (Etapa 1) |
| `active` | Casos activos estimados por JHU | float | Numérico o nulo | JHU Daily Reports | 2020-03-22 (Etapa 3) |
| `incident_rate` | Casos acumulados por 100.000 habitantes | float | `>= 0` o nulo | JHU Daily Reports | 2020-05-29 (Etapa 4) |
| `case_fatality_ratio` | Razón de letalidad aparente (`deaths / confirmed * 100`) | float | `[0, 100]` o nulo | JHU Daily Reports | 2020-05-29 (Etapa 4) |