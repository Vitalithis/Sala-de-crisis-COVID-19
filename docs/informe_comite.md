# Informe al Comité Asesor de Preparación Pandémica

**Proyecto:** Sala de Crisis COVID-19 · Gestión de Datos (IN1232C)  
**Cobertura:** 22 de enero de 2020 al 9 de marzo de 2023 (1.143 días · 4.287.467 registros territoriales)

---

## 1. Qué pasó

Durante los tres años analizados a partir del registro consolidado de Johns Hopkins CSSE, integrado con datos de vacunación de Our World in Data (OWID) y demografía del Banco Mundial, se observaron los siguientes hechos principales:

- **Chile frente a Sudamérica:** al cierre del registro (`2023-03-09`), Chile acumuló **27.161,7 casos por 100.000 habitantes** (2.° en Sudamérica, tras Uruguay con 29.775,0) y **336,2 fallecidos por 100.000 habitantes** (2.° en la región, tras Perú con 665,8). El país atravesó cuatro grandes olas epidémicas, siendo la ola de ómicron (pico el `2022-02-13`) la de mayor volumen de contagios diarios.
- **Impacto desigual dentro de Chile:** entre las 16 regiones reportadas desde fines de mayo de 2020, **Magallanes** concentró la mayor incidencia acumulada (**40.624,4 c/100k**) y mortalidad (**464,8 c/100k**), mientras la Región Metropolitana ocupó el 2.° lugar en mortalidad (**434,0 c/100k**). La **Región del Biobío** se ubicó en posición intermedia: **#9 en incidencia** (**32.806,3 c/100k**) y **#10 en mortalidad** (**309,9 c/100k**).
- **Efecto de la vacunación y sesgo de interpretación:** tras superar el `50 %` de vacunación completa, la mediana de letalidad aparente mensual cayó drásticamente en el Cono Sur (en Chile de **2,10 % a 0,64 %**; en Perú de **7,56 % a 1,56 %**). Sin embargo, al comparar `151` países en 2022, la vacunación al cierre de 2021 muestra correlación positiva con la mortalidad 2022 (`r = 0,488`) debido al envejecimiento poblacional: la proporción de adultos mayores de 65 años (Banco Mundial) explica fuertemente la mortalidad (`r = 0,795`) y la prioridad vacunal (`r = 0,610`).
- **Calidad heterogénea de los reportes:** se detectaron `44.582` retrocesos en acumulados (`1,04 %`), `10.777` registros con fallecidos mayores que casos (`0,25 %`, concentrados en EE. UU. y Reino Unido) y `19.068` días sin reporte desde 2022.

## 2. Qué habría permitido anticiparlo

- **Alertas tempranas sobre variaciones semanales:** la regla implementada (`incidencia 7d >= 35 c/100k` y `variación semanal >= 25 %`) habría activado alertas con **44 días de anticipación** antes del pico de la primera ola (`2020-05-04` vs. `2020-06-17`), **41 días** antes del pico de ómicron (`2022-01-03` vs. `2022-02-13`) y **39 días** antes del pico de invierno 2022 (`2022-05-09` vs. `2022-06-17`), con una tasa acotada de falsas alarmas del **19,5 %**.
- **Límites del pronóstico puramente histórico:** el backtesting a 14 días demuestra que modelos univariados como `ARIMA(1,1,1)` y `Holt` logran errores bajos en olas con inercia establecida (**MAPE 6,7 % y 10,5 %** en marzo 2021; **23,3 % y 26,2 %** en mayo 2022), pero subestiman quiebres abruptos por nuevas variantes (ómicron en dic-2021, **MAPE 29,2 %–37,0 %**). Anticipar un cambio de variante exige integrar datos genómicos, positividad de testeo y movilidad, no solo conteos diarios rezagados.

## 3. Tres recomendaciones para la próxima pandemia

| # | Recomendación concreta | Evidencia del proyecto | Indicador medible (KPI) | Responsable |
|---:|---|---|---|---|
| **1** | **Estandarizar un esquema único de reporte diario desde el día 1**, con validación automática de consistencia (`deaths <= confirmed`), marcas explícitas de ajuste retroactivo y granularidad regional homogénea. | JHU cambió de esquema **5 veces**; hubo **44.582** retrocesos y **10.777** inconsistencias (`US` índice `0,00`, `UK` `34,91`); Chile cambió de nacional a 16 regiones recién en mayo de 2020. | `%` de reportes diarios aprobando las 6 reglas de calidad sin estado `RECHAZA` (`>= 99,9 %`) y cobertura regional desde la semana 1. | Jefatura de Estadísticas Sanitarias / DEIS |
| **2** | **Operar un sistema de alerta temprana por velocidad de crecimiento (MM7)** complementado con vigilancia genómica y de testeo antes de cambios de variante. | La regla `alerta()` anticipó **41 días** el pico de ómicron y **44 días** la ola 1; los modelos sin señal genómica elevaron el MAPE a **29,2 %–37,0 %** en el quiebre de dic-2021. | Días de anticipación promedio previo al pico (`>= 21 días`), tasa de falsas alarmas a 14 días (`<= 20 %`) y `MAPE <= 15 %` a 14 días. | Unidad de Vigilancia Epidemiológica y Analítica |
| **3** | **Publicar indicadores ajustados por edad, testeo y control de divulgación** para evitar decisiones basadas en tasas crudas o datos reidentificables. | La correlación cruda vacunación vs. mortalidad 2022 (`r = 0,488`) se explica por población >=65 años (`r = 0,795`); la supresión `<5` protegió `316` condados `<5.000` hab. perdiendo solo **1,79 %** de celdas. | `100 %` de tableros públicos con tasas estandarizadas por edad, positividad visible y `0` celdas `1–4` expuestas en territorios `<50.000` hab. | Dirección de Datos Abiertos y Privacidad |
