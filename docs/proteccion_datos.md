# Protección de datos y ética (R6)

## 1. ¿Son datos personales? (Ley 19.628 y Ley 21.719)

TODO (B): definición de dato personal y de dato sensible (salud); por qué los conteos agregados por territorio no identifican a nadie en general; cuándo podrían llegar a hacerlo (territorios pequeños con conteos de 1 a 4, combinados con otras fuentes).

## 2. Control de divulgación

- Regla: si la población es menor a ____ y el conteo está entre 1 y 4, se muestra «<5».
- Implementación: `src/proteccion/supresion.py`, aplicada en el tablero.
- Territorios afectados: ____ (cuantificar).
- Excelente: condados de EE.UU. (317 con menos de 5.000 habitantes); información perdida: ____ %.

## 3. Advertencias de interpretación

- La letalidad aparente (fallecidos / casos) depende del testeo: con poco testeo se subestiman los casos y la letalidad sube.
- Comparar países exige cautela: definiciones, testeo, rezagos y frecuencia de reporte distintos.
- (Agregar las advertencias que se muestran en el tablero.)
