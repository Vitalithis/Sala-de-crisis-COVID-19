"""R2 / P4 - Indice de calidad por pais.

Propuesta de partida (el responsable decide y documenta la formula final en
docs/decisiones_calidad.md):

    indice = 100 - (w1 * %dias_retrocede + w2 * %dias_sin_reporte
                    + w3 * %picos_rezago + w4 * %fallecidos_mayor_casos
                    + w5 * |diferencia_series_vs_diarios|)
"""
from __future__ import annotations

import pandas as pd


def problemas_por_pais(df_pais_dia: pd.DataFrame) -> pd.DataFrame:
    """Cuantifica los problemas de R2 por pais.

    Entrada: tabla pais x dia con columnas pais, fecha, confirmados_acum,
    fallecidos_acum, casos_nuevos (vista vw_pais_dia del DW).
    """
    raise NotImplementedError("TODO(R2): dias retrocede, dias sin reporte, picos por rezago, ...")


def indice_calidad(problemas: pd.DataFrame, pesos: dict[str, float] | None = None) -> pd.DataFrame:
    raise NotImplementedError("TODO(R2): combinar problemas en un indice 0-100 y ordenar")
