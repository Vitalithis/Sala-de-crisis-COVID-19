# Decisiones de calidad (R2)

Regla del curso: corregir, marcar o excluir. **Imputar es inventar.**

| # | Problema | Cuántos casos (cuantificado) | Decisión | Justificación | Dónde se aplica |
|---|---|---|---|---|---|
| 1 | Acumulado que retrocede (84 países) | | Marcar (`retrocede`) | | `src/dw/cargar.py` |
| 2 | Días sin reporte (reportes semanales en 2022) | | | | |
| 3 | Picos por acumulación de rezagos | | | | |
| 4 | Fallecidos mayores que casos | | | | |
| 5 | Diferencia entre las series y la suma de los diarios | | | | |
| 6 | Entidades especiales (Diamond Princess, MS Zaandam, Olimpiadas, Antarctica) | | | | |
| 7 | Nombres de país inconsistentes (Mainland China, Korea, South, Taiwan*) | 242 nombres distintos antes de normalizar frente a 202 países de la tabla UID; 41 variantes, casi todas entre ene y mar de 2020 | Corregir | Se llevan al nombre canónico de la tabla UID para poder cruzar con población e ISO3. Los territorios que primero aparecen como país y después como provincia (Hong Kong, Macau, Aruba, Guadalupe, Guam…) se reasignan a su país y provincia | `NORMALIZAR_PAIS` y `PAIS_A_PROVINCIA` en `src/ingesta/unificar.py` |
| 10 | Filas duplicadas por (fecha_reporte, territorio) en un mismo archivo | 79 filas de 4.287.473 (0,002 %), todas entre ene y mar de 2020. 7 venían duplicadas en el origen (China/Gansu y China/Hebei el 11 y 12-mar, China/Hubei el 23-ene, Nueva Zelanda el 26-feb, District of Columbia el 22-mar); 72 aparecen al normalizar (problema 7), porque en mar-2020 JHU publicó a la vez el nombre antiguo («Guam», «Reunion», «The Bahamas»…) y el canónico («US / Guam»…) | Excluir | En 61 de las 79 la fila del nombre antiguo trae 0 o un valor menor (quedó sin actualizar) y en 18 los valores son idénticos. Se conserva la fila con mayor `confirmed` (y luego `deaths`); no se suman (sería contar doble) ni se imputan. Las filas excluidas quedan en `reports/duplicados_excluidos.csv` con su archivo y fila de origen | `separar_duplicados` en `src/ingesta/unificar.py` |
| 8 | Chile nacional hasta may-2020 y regional después | | | | |
| 9 | Recuperados sin actualizar desde ago-2021 | | | | |

## Índice de calidad por país

Fórmula, pesos y top 10 de peores países (P4): TODO (B).
