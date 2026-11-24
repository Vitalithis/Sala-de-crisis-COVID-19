# Informe técnico (máximo 15 páginas)

> Fuente en Markdown. Exportar a `docs/informe_tecnico.pdf` (por ejemplo, con pandoc o desde Word/Google Docs). Cada sección la redacta su responsable y D la ensambla.

## 1. Introducción y encargo (D)
*(Pendiente de redacción por Rol D.)*

## 2. Arquitectura y capas; CSV frente a Parquet; motor elegido (A)
*(Pendiente de redacción por Rol A.)*

## 3. Calidad de datos: reglas, problemas cuantificados, índice y decisiones (B)

Para garantizar la confiabilidad analítica sin alterar la evidencia histórica, se adoptó el principio del curso: **corregir, marcar o excluir; nunca imputar**. Se implementaron reglas ejecutables sobre las seis dimensiones de calidad (`src/03_calidad_y_olap.py` y `src/calidad/reglas.py`) aplicadas a las `4.287.467` filas de `fact_covid`:

| Dimensión | Regla evaluada | Filas afectadas | Porcentaje | Umbral | Estado |
|---|---|---:|---:|---:|---|
| Completitud | Territorios sin población en UID | 101.775 | 2,3738 % | 5,00 % | OK |
| Unicidad | Duplicados `(fecha × territorio)` en crudo | 6 | 0,0001 % | 0,01 % | OK |
| Validez | Acumulados negativos o coordenadas fuera de rango | 6 | 0,0001 % | 0,10 % | OK |
| Consistencia | Fallecidos mayores que confirmados | 10.777 | 0,2514 % | 0,05 % | RECHAZA |
| Exactitud | Días con acumulado que retrocede | 44.582 | 1,0398 % | 1,00 % | ALERTA |
| Exactitud | Picos bruscos por acumulación de rezagos | 11.354 | 0,2648 % | 0,50 % | OK |
| Oportunidad | Días sin reporte (`0` nuevos en 2022-2023, >100k acum.) | 19.068 | 0,4447 % | 1,00 % | OK |

Las decisiones específicas para los nueve problemas detectados (incluyendo la conciliación exacta con `time_series` al `2023-03-09`, el marcado de `27` entidades especiales y la normalización canónica de países) se detallan en `docs/decisiones_calidad.md`.

## 4. Modelo de datos: estrella, grano, integración con OWID y tasa de cruce, OLAP (A)
*(Pendiente de redacción por Rol A · Nota de integración OWID verificada por B: de `236` códigos ISO3 en JHU y `217` en OWID, cruzan `215` territorios, equivalente a una tasa de cruce de `91,1 %`.)*

## 5. Resultados P1 a P7

### P1 y P2 (D)
*(Pendiente de redacción por Rol D.)*

### P3 · Letalidad aparente mensual frente al porcentaje de vacunación completa (B)
Se analizó la evolución mensual entre abril de 2020 y diciembre de 2022 para Chile, Argentina, Perú y Uruguay cruzando `fact_covid` con `fact_vacunacion` (OWID). Al comparar la mediana de letalidad aparente mensual antes y después de superar el `50 %` de vacunación completa:
- **Chile:** pasa de `2,10 %` (<50 % vac.) a `0,64 %` (>=50 % vac.).
- **Argentina:** pasa de `2,30 %` a `0,41 %`.
- **Perú:** pasa de `7,56 %` a `1,56 %`.
- **Uruguay:** pasa de `1,73 %` a `0,46 %`.

*Advertencia metodológica:* la caída observada coincide con el avance de la vacunación, pero la letalidad aparente (`fallecidos / confirmados`) también depende de la intensidad del testeo y de la menor severidad intrínseca de variantes posteriores como ómicron. (Ver `docs/figuras/p3_letalidad_vacunacion.png`.)

### P4 · Índice de calidad por país: top 10 peores y decisiones (B)
Con la fórmula ponderada documentada en `docs/decisiones_calidad.md` (penalizando inconsistencias `deaths > confirmed` con peso `5,0`, retrocesos con `3,0`, días sin cambio con `0,5` y días faltantes con `0,5`), los 10 peores registros son: `US` (`0,00`), `United Kingdom` (`34,91`), `Iran (Islamic Republic of)` (`50,04`), `Republic of Korea` (`50,04`), `South Korea` (`52,10`), `Tanzania` (`52,60`), `Congo (Brazzaville)` (`56,58`), `Nicaragua` (`56,94`), `Benin` (`57,37`) y `Cameroon` (`57,72`). En EE. UU. y Reino Unido el puntaje cae por inconsistencias en registros subnacionales o `Unknown`; en los países africanos y Nicaragua por cientos de días sin actualización de reportes. Se decidió conservar los datos marcados y utilizar media móvil de 7 días para el análisis temporal.

### P5 y P6 (C)
*(Pendiente de redacción por Rol C.)*

### P7 · Vacunación al cierre de 2021 frente a mortalidad por 100.000 hab. en 2022 (B)
Se evaluó la relación entre el porcentaje de población con vacunación completa al `31-12-2021` (OWID) y la tasa de mortalidad por COVID-19 durante `2022` (fallecidos por `100.000` hab.) en `n = 151` países con población >= `1.000.000`. Se obtuvo una correlación de Pearson `r = 0,488`. Este resultado ilustra que **correlación no implica causalidad**: los países con mayor cobertura vacunal al cierre de 2021 presentan simultáneamente poblaciones más envejecidas, mayor capacidad diagnóstica y sistemas de registro de defunciones más completos, factores de confusión que explican una mayor mortalidad registrada frente a países jóvenes con alto subregistro. (Ver `docs/figuras/p7_vacunacion_vs_mortalidad.png`.)

## 6. Minería y predicción: segmentación, pronóstico, backtesting y alerta (C)
*(Pendiente de redacción por Rol C.)*

## 7. Protección de datos y ética (B)

En el marco de la **Ley N.° 19.628** y la **Ley N.° 21.719** de Chile, los registros de JHU y OWID corresponden a conteos agregados por territorio sin identificadores directos de personas naturales, por lo que no constituyen datos personales ni datos sensibles de salud en términos generales. Sin embargo, en territorios con población reducida y conteos entre `1` y `4`, existe riesgo de reidentificación indirecta al cruzar con fuentes externas.

Como control de divulgación (`src/proteccion/supresion.py` y `dashboard/app.py`):
- En el tablero general se suprimen conteos entre `1` y `4` en territorios con `< 50.000` habitantes (`2.250` territorios; `544.785` celdas de casos y `130.696` de fallecidos en el histórico).
- En la evaluación estricta sobre condados de EE. UU. con `< 5.000` habitantes (`316` condados), la pérdida de información es acotada: `1,79 %` de las celdas de casos (`61.504` de `3.432.447`) y `0,10 %` de las de fallecidos (`3.515`).

Además, el tablero despliega advertencias permanentes sobre sesgo de testeo en la letalidad aparente, heterogeneidad entre países y el cambio de granularidad de Chile en mayo de 2020 (detalle completo en `docs/proteccion_datos.md`).

## 8. Tablero (D)
*(Pendiente de redacción por Rol D.)*

## 9. Limitaciones (todos)
*(Pendiente de consolidación grupal.)*
