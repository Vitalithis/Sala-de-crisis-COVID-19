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
| 7 | Nombres de país inconsistentes (Mainland China, Korea, South, Taiwan*) | | Corregir | Mapa NORMALIZAR_PAIS | `src/ingesta/unificar.py` |
| 8 | Chile nacional hasta may-2020 y regional después | | | | |
| 9 | Recuperados sin actualizar desde ago-2021 | | | | |

## Índice de calidad por país

Fórmula, pesos y top 10 de peores países (P4): TODO (B).
