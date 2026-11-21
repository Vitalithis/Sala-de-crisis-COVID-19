# Diccionario de datos (R2)

Tabla unificada: `data/clean/reportes_diarios_unificados.parquet` (generada por `src/ingesta/unificar.py`).
Grano: una fila por territorio reportado y por archivo diario.

| Columna | Significado | Tipo | Dominio / formato | Origen | Existe desde (esquema) |
|---|---|---|---|---|---|
| fecha_reporte | Fecha del dato (nombre del archivo) | date | 2020-01-22 a 2023-03-09 | Nombre del archivo | 1 |
| esquema | Etapa del formato de origen | int8 | 1 a 5 | Derivada de la fecha | 1 |
| fips | Código FIPS (EE.UU.) | str | 5 dígitos | FIPS | 3 (22-mar-2020) |
| admin2 | Condado (EE.UU.) | str | | Admin2 | 3 |
| province_state | Provincia, estado o región | str | | Province/State, Province_State | 1 |
| country_region | País o entidad, normalizado | str | Ver NORMALIZAR_PAIS | Country/Region, Country_Region | 1 |
| last_update | Cuándo JHU modificó la fila (no es la fecha del dato) | str ISO | AAAA-MM-DD | Last Update, Last_Update | 1 |
| lat | Latitud | float | -90 a 90 | Latitude, Lat | 2 (1-mar-2020) |
| long | Longitud | float | -180 a 180 | Longitude, Long_ | 2 |
| confirmed | Casos confirmados acumulados | Int64 | >= 0 | Confirmed | 1 |
| deaths | Fallecidos acumulados | Int64 | >= 0 | Deaths | 1 |
| recovered | Recuperados acumulados (se deja de actualizar en ago-2021) | Int64 | >= 0 | Recovered | 1 |
| active | Casos activos | Int64 | | Active | 3 |
| combined_key | Clave textual del territorio | str | | Combined_Key | 3 |
| incident_rate | Casos por 100.000 según JHU | float | >= 0 | Incidence_Rate, Incident_Rate | 4 (29-may-2020) |
| case_fatality_ratio | Letalidad según JHU (%) | float | 0 a 100 | Case-Fatality_Ratio, Case_Fatality_Ratio | 4 |
| clave_territorio | país\|provincia\|condado | str | | Derivada | 1 |
| archivo_origen | Archivo CSV de origen (linaje) | str | MM-DD-AAAA.csv | Derivada | 1 |
| fila_origen | Línea del CSV de origen (linaje) | int | >= 2 | Derivada | 1 |

TODO (B): revisar los dominios con los datos reales, agregar % de nulos por columna y documentar las tablas del DW.
