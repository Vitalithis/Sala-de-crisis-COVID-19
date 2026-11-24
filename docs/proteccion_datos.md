# Protección de datos y ética (R6)

## 1. ¿Son datos personales? (Ley 19.628 y Ley 21.719)

En la legislación chilena vigente sobre protección de la vida privada (**Ley N.° 19.628**) y su modernización (**Ley N.° 21.719**, que regula el tratamiento de datos personales y crea la Agencia de Protección de Datos Personales):

- **Dato personal:** toda información vinculada o referida a una persona natural identificada o identificable.
- **Dato sensible (categoría especial):** aquellos datos que revelan el estado de salud físico o psíquico, diagnósticos clínicos o información biométrica de una persona natural.
- **Evaluación sobre los datos de JHU y OWID:** las series de casos confirmados, fallecidos y vacunación utilizadas en este proyecto son **conteos agregados por territorio** (país, región, provincia o condado) sin identificadores directos (RUT, nombre, dirección o fecha de nacimiento). En términos generales, los datos agregados no permiten identificar a un individuo específico, por lo que no constituyen datos personales ni sensibles de salud.
- **Riesgo de reidentificación en poblaciones pequeñas:** cuando se reportan territorios con población reducida y conteos muy bajos (entre `1` y `4` casos o fallecidos en un día), la combinación con información contextual externa (noticias locales, registros civiles o redes sociales en localidades pequeñas) podría permitir inferir la identidad de la persona afectada (reidentificación indirecta).

## 2. Control de divulgación (supresión de celdas pequeñas)

Para mitigar el riesgo de reidentificación indirecta, se aplica una regla de **supresión de celdas pequeñas**:

- **Regla en el tablero general (`dashboard/app.py`):** si un territorio tiene población conocida menor a `50.000` habitantes y el conteo está entre `1` y `4`, el valor mostrado se reemplaza por `<5 (suprimido R6)`.
  - **Territorios afectados en el DW:** `2.250` territorios distintos con población `< 50.000` habitantes (sobre `4.185.692` filas con población conocida > 0).
  - **Celdas suprimidas en la serie histórica:** `544.785` celdas de `casos_nuevos` (`13,02 %`) y `130.696` celdas de `fallecidos_nuevos` (`3,12 %`).
- **Regla estricta / nivel excelente en condados de EE. UU. (`src/proteccion/supresion.py`):** usando el umbral de `5.000` habitantes sobre los condados de EE. UU. (`nivel_granularidad = 'condado'`):
  - **Condados afectados:** `316` condados de EE. UU. con menos de `5.000` habitantes.
  - **Información perdida sobre `3.432.447` filas de condados de EE. UU.:** `61.504` celdas suprimidas en `casos_nuevos` (**`1,79 %`**) y `3.515` celdas suprimidas en `fallecidos_nuevos` (**`0,10 %`**).

## 3. Advertencias de interpretación

El tablero (`dashboard/app.py`, barra lateral y tarjetas de métricas) muestra explícitamente las siguientes advertencias para evitar malas interpretaciones de los indicadores:

1. **Sesgo de testeo en la letalidad aparente:** la razón `fallecidos / confirmados` depende directamente de la capacidad y estrategia de testeo de cada país. Con bajo nivel de testeo se subestiman los casos leves o asintomáticos y la letalidad aparente se eleva artificialmente.
2. **Cautela al comparar países:** distintos países aplican criterios heterogéneos para definir caso confirmado, defunción por COVID-19, rezagos administrativos y frecuencia de reporte (diaria vs. semanal desde 2022).
3. **Cambio de granularidad en Chile:** Chile se reportó de forma nacional hasta fines de mayo de 2020 y desagregado en 16 regiones desde el 20 de mayo de 2020 en adelante; las comparaciones regionales no deben extenderse hacia atrás antes de esa fecha.
4. **Supresión de celdas pequeñas:** los conteos entre `1` y `4` en territorios con menos de `50.000` habitantes se ocultan como `<5 (suprimido R6)` para resguardar el control de divulgación.
